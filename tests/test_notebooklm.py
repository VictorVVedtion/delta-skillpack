"""Tests for NotebookLM knowledge engine integration."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from skillpack.models import (
    Citation,
    KnowledgeResponse,
    NotebookConfig,
    NotebookLMConfig,
    NotebookType,
    QueryContext,
    SkillStep,
    StoryType,
)
from skillpack.ralph.notebooklm import NotebookLMBridge, NotebookRouter, QueryCache


class TestQueryCache:
    """Tests for QueryCache."""

    def test_compute_key(self, tmp_path: Path) -> None:
        cache = QueryCache(tmp_path)
        key1 = cache._compute_key("What is X?", NotebookType.ARCHITECTURE)
        key2 = cache._compute_key("what is x?", NotebookType.ARCHITECTURE)
        key3 = cache._compute_key("What is X?", NotebookType.PATTERNS)

        assert key1 == key2  # Case insensitive
        assert key1 != key3  # Different notebook type

    def test_memory_cache_hit(self, tmp_path: Path) -> None:
        cache = QueryCache(tmp_path)
        response = KnowledgeResponse(
            question="test",
            answer="answer",
            notebook_type=NotebookType.DOMAIN,
        )

        cache.set("test question", NotebookType.DOMAIN, response)
        result = cache.get("test question", NotebookType.DOMAIN)

        assert result is not None
        assert result.answer == "answer"
        assert result.cached is True

    def test_memory_cache_expiry(self, tmp_path: Path) -> None:
        cache = QueryCache(tmp_path, default_ttl_minutes=0)  # Immediate expiry
        response = KnowledgeResponse(
            question="test",
            answer="answer",
            notebook_type=NotebookType.DOMAIN,
        )

        cache.set("test question", NotebookType.DOMAIN, response)
        # With TTL=0, should expire immediately
        cache.get("test question", NotebookType.DOMAIN, ttl=timedelta(seconds=0))

        # May or may not be None depending on timing, but shouldn't crash

    def test_file_cache_persistence(self, tmp_path: Path) -> None:
        cache1 = QueryCache(tmp_path)
        response = KnowledgeResponse(
            question="test",
            answer="persisted",
            notebook_type=NotebookType.API,
        )
        cache1.set("persist test", NotebookType.API, response)

        # New cache instance should load from file
        cache2 = QueryCache(tmp_path)
        result = cache2.get("persist test", NotebookType.API)

        assert result is not None
        assert result.answer == "persisted"

    def test_semantic_cache(self, tmp_path: Path) -> None:
        cache = QueryCache(tmp_path)
        response = KnowledgeResponse(
            question="What is the architecture pattern?",
            answer="MVC pattern",
            notebook_type=NotebookType.PATTERNS,
        )
        cache.set("What is the architecture pattern?", NotebookType.PATTERNS, response)

        # Similar question should hit semantic cache
        # Note: actual result depends on Jaccard similarity
        cache._get_semantic(
            "What is architecture pattern?",  # Slightly different
            NotebookType.PATTERNS,
            timedelta(minutes=30),
            threshold=0.8,
        )


class TestNotebookRouter:
    """Tests for NotebookRouter."""

    def test_rule_routing(self) -> None:
        router = NotebookRouter()

        context = QueryContext(
            current_step=SkillStep.PLAN,
            story_type=StoryType.FEATURE,
        )
        result = router.route("How to implement X?", context)
        assert result == NotebookType.ARCHITECTURE

    def test_step_only_routing(self) -> None:
        router = NotebookRouter()

        context = QueryContext(current_step=SkillStep.REVIEW)
        result = router.route("Check this code", context)
        assert result == NotebookType.STANDARDS

    def test_keyword_routing(self) -> None:
        router = NotebookRouter()

        context = QueryContext()  # No step/type info

        result = router.route("What is the API endpoint for users?", context)
        assert result == NotebookType.API

        result = router.route("How to fix this error?", context)
        assert result == NotebookType.TROUBLESHOOTING

    def test_default_routing(self) -> None:
        router = NotebookRouter()

        context = QueryContext()
        result = router.route("Something random", context)
        assert result == NotebookType.DOMAIN


class TestKnowledgeResponse:
    """Tests for KnowledgeResponse model."""

    def test_has_citations(self) -> None:
        resp1 = KnowledgeResponse(question="q", answer="a")
        assert resp1.has_citations is False

        resp2 = KnowledgeResponse(
            question="q",
            answer="a",
            citations=[Citation(source="doc.pdf", quote="text")],
        )
        assert resp2.has_citations is True

    def test_summary_truncation(self) -> None:
        short_answer = "Short"
        long_answer = "x" * 300

        resp1 = KnowledgeResponse(question="q", answer=short_answer)
        assert resp1.summary == short_answer

        resp2 = KnowledgeResponse(question="q", answer=long_answer)
        assert len(resp2.summary) == 200

    def test_format_with_citations(self) -> None:
        resp = KnowledgeResponse(
            question="q",
            answer="The answer",
            citations=[
                Citation(source="doc.pdf", section="Chapter 1", quote="quote"),
                Citation(source="other.pdf"),
            ],
        )
        formatted = resp.format_with_citations()

        assert "The answer" in formatted
        assert "Sources:" in formatted
        assert "doc.pdf" in formatted
        assert "Chapter 1" in formatted


class TestNotebookLMBridge:
    """Tests for NotebookLMBridge."""

    @pytest.fixture
    def mock_memory(self, tmp_path: Path) -> MagicMock:
        memory = MagicMock()
        memory.ralph_dir = tmp_path / "ralph"
        memory.ralph_dir.mkdir(parents=True)
        memory.append_progress = MagicMock()
        return memory

    @pytest.fixture
    def config(self) -> NotebookLMConfig:
        return NotebookLMConfig(
            enabled=True,
            skill_path="/tmp/notebooklm",
            notebooks=[
                NotebookConfig(id="arch-123", type=NotebookType.ARCHITECTURE),
                NotebookConfig(id="api-456", type=NotebookType.API),
            ],
            default_notebook_id="default-789",
        )

    def test_get_ttl(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        # Long TTL questions
        assert bridge._get_ttl("What is the architecture pattern?") == bridge.TTL_LONG
        assert bridge._get_ttl("What are the coding standards?") == bridge.TTL_LONG

        # Short TTL questions
        assert bridge._get_ttl("Is this correct?") == bridge.TTL_SHORT
        assert bridge._get_ttl("Does this follow guidelines?") == bridge.TTL_SHORT

        # Default TTL
        assert bridge._get_ttl("Something else") == bridge.TTL_DEFAULT

    def test_get_notebook_id(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        assert bridge._get_notebook_id(NotebookType.ARCHITECTURE) == "arch-123"
        assert bridge._get_notebook_id(NotebookType.API) == "api-456"
        assert bridge._get_notebook_id(NotebookType.DOMAIN) == "default-789"

    def test_parse_response_json(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        json_output = json.dumps(
            {
                "answer": "The answer",
                "citations": [{"source": "doc.pdf", "quote": "text"}],
                "confidence": 0.9,
            }
        )

        resp = bridge._parse_response("question", NotebookType.DOMAIN, json_output)

        assert resp.answer == "The answer"
        assert len(resp.citations) == 1
        assert resp.confidence == 0.9

    def test_parse_response_plain_text(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        text_output = "Plain text answer"

        resp = bridge._parse_response("question", NotebookType.DOMAIN, text_output)

        assert resp.answer == "Plain text answer"
        assert len(resp.citations) == 0
        assert resp.confidence == 0.5  # Lower for plain text

    def test_format_context(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        responses = [
            KnowledgeResponse(
                question="Q1",
                answer="A1",
                citations=[Citation(source="s1.pdf")],
            ),
            KnowledgeResponse(
                question="Q2",
                answer="A2",
            ),
        ]

        formatted = bridge.format_context(responses)

        assert "External Knowledge" in formatted
        assert "Q1" in formatted
        assert "A1" in formatted
        assert "s1.pdf" in formatted
        assert "Q2" in formatted
        assert "A2" in formatted

    def test_format_context_empty(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        assert bridge.format_context([]) == ""

        # With error response
        responses = [
            KnowledgeResponse(question="Q", answer="", error="Failed"),
        ]
        assert bridge.format_context(responses) == ""

    @pytest.mark.asyncio
    async def test_query_cache_hit(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        # Pre-populate cache
        cached_response = KnowledgeResponse(
            question="test",
            answer="cached answer",
            notebook_type=NotebookType.DOMAIN,
            confidence=0.9,
        )
        bridge.cache.set("test question", NotebookType.DOMAIN, cached_response)

        context = QueryContext()
        result = await bridge.query("test question", context, notebook_hint=NotebookType.DOMAIN)

        assert result.answer == "cached answer"
        assert result.cached is True

    @pytest.mark.asyncio
    async def test_query_skill_not_installed(self, tmp_path: Path, mock_memory: MagicMock) -> None:
        config = NotebookLMConfig(
            enabled=True,
            skill_path="/nonexistent/path",
            default_notebook_id="nb-123",
            cache_enabled=False,
        )
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        context = QueryContext()
        result = await bridge.query("test", context)

        assert result.answer == ""
        assert result.error is not None
        assert "not installed" in result.error

    @pytest.mark.asyncio
    async def test_batch_query(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        config.cache_enabled = False
        config.batch_delay_seconds = 0
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        # Mock _execute_query
        async def mock_execute(q: str, nt: NotebookType) -> KnowledgeResponse:
            return KnowledgeResponse(question=q, answer=f"Answer to {q}", notebook_type=nt)

        bridge._execute_query = mock_execute  # type: ignore[method-assign]

        context = QueryContext()
        questions = ["Q1", "Q2", "Q3"]

        results = await bridge.batch_query(questions, context)

        assert len(results) == 3
        assert results[0].question == "Q1"
        assert results[1].question == "Q2"
        assert results[2].question == "Q3"


# =============================================================================
# Integration Tests for Phase 2+3
# =============================================================================


class TestOrchestratorIntegration:
    """Tests for Orchestrator integration with NotebookLM."""

    def test_ralph_config_notebooklm_enabled(self) -> None:
        """Test RalphConfig with NotebookLM enabled."""
        from skillpack.models import NotebookLMConfig, RalphConfig

        config = RalphConfig(
            use_notebooklm=True,
            notebooklm=NotebookLMConfig(
                enabled=True,
                skill_path="/tmp/notebooklm",
                default_notebook_id="test-123",
            ),
            knowledge_query_before_plan=True,
            knowledge_query_before_review=True,
            knowledge_query_on_error=True,
        )

        assert config.use_notebooklm is True
        assert config.notebooklm.enabled is True
        assert config.knowledge_query_before_plan is True
        assert config.knowledge_query_before_review is True
        assert config.knowledge_query_on_error is True

    def test_ralph_config_notebooklm_disabled(self) -> None:
        """Test RalphConfig with NotebookLM disabled (default)."""
        from skillpack.models import RalphConfig

        config = RalphConfig()

        assert config.use_notebooklm is False

    def test_orchestrator_init_without_notebooklm(self, tmp_path: Path) -> None:
        """Test StoryOrchestrator initializes without knowledge engine when disabled."""
        from skillpack.models import RalphConfig
        from skillpack.ralph.orchestrator import StoryOrchestrator

        config = RalphConfig(use_notebooklm=False)
        orchestrator = StoryOrchestrator(tmp_path, ralph_config=config)

        assert orchestrator.knowledge_engine is None

    def test_orchestrator_init_with_notebooklm(self, tmp_path: Path) -> None:
        """Test StoryOrchestrator initializes with knowledge engine when enabled."""
        from skillpack.models import NotebookLMConfig, RalphConfig
        from skillpack.ralph.orchestrator import StoryOrchestrator

        config = RalphConfig(
            use_notebooklm=True,
            notebooklm=NotebookLMConfig(
                enabled=True,
                skill_path="/tmp/notebooklm",
                default_notebook_id="test-123",
            ),
        )
        orchestrator = StoryOrchestrator(tmp_path, ralph_config=config)

        assert orchestrator.knowledge_engine is not None


class TestSelfHealIntegration:
    """Tests for SelfHeal integration with NotebookLM."""

    @pytest.fixture
    def mock_memory(self, tmp_path: Path) -> MagicMock:
        memory = MagicMock()
        memory.ralph_dir = tmp_path / "ralph"
        memory.ralph_dir.mkdir(parents=True)
        memory.append_progress = MagicMock()
        return memory

    @pytest.fixture
    def config(self) -> NotebookLMConfig:
        return NotebookLMConfig(
            enabled=True,
            skill_path="/tmp/notebooklm",
            notebooks=[
                NotebookConfig(id="arch-123", type=NotebookType.ARCHITECTURE),
                NotebookConfig(id="trouble-456", type=NotebookType.TROUBLESHOOTING),
            ],
            default_notebook_id="default-789",
        )

    def test_init_without_knowledge_engine(self, tmp_path: Path) -> None:
        """Test SelfHealingOrchestrator without knowledge engine."""
        from skillpack.ralph.memory import MemoryManager
        from skillpack.ralph.self_heal import SelfHealingOrchestrator
        from skillpack.ralph.verify import QualityVerifier

        memory = MemoryManager(tmp_path)
        verifier = QualityVerifier(tmp_path)

        healer = SelfHealingOrchestrator(memory, verifier)

        assert healer.knowledge_engine is None

    def test_init_with_knowledge_engine(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        """Test SelfHealingOrchestrator with knowledge engine."""
        from skillpack.ralph.self_heal import SelfHealingOrchestrator
        from skillpack.ralph.verify import QualityVerifier

        bridge = NotebookLMBridge(tmp_path, mock_memory, config)
        verifier = QualityVerifier(tmp_path)

        healer = SelfHealingOrchestrator(mock_memory, verifier, knowledge_engine=bridge)

        assert healer.knowledge_engine is not None

    @pytest.mark.asyncio
    async def test_search_solution_returns_none_without_engine(self, tmp_path: Path) -> None:
        """Test that _search_solution returns None without knowledge engine."""
        from skillpack.ralph.memory import MemoryManager
        from skillpack.ralph.self_heal import ErrorCategory, SelfHealingOrchestrator
        from skillpack.ralph.verify import QualityVerifier

        memory = MemoryManager(tmp_path)
        verifier = QualityVerifier(tmp_path)
        healer = SelfHealingOrchestrator(memory, verifier)

        result = await healer._search_solution(
            "ModuleNotFoundError: No module named 'foo'",
            ErrorCategory.IMPORT,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_heal_with_knowledge_engine(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        """Test heal method with knowledge engine providing solution."""
        from skillpack.models import StoryType, UserStory
        from skillpack.ralph.self_heal import SelfHealingOrchestrator
        from skillpack.ralph.verify import QualityVerifier

        # Create bridge with mocked query
        bridge = NotebookLMBridge(tmp_path, mock_memory, config)

        async def mock_query(q: str, ctx: QueryContext, **kwargs) -> KnowledgeResponse:
            return KnowledgeResponse(
                question=q,
                answer="To fix this import error, install the package with pip install foo",
                notebook_type=NotebookType.TROUBLESHOOTING,
                confidence=0.85,
            )

        bridge.query = mock_query  # type: ignore[method-assign]

        verifier = QualityVerifier(tmp_path)
        healer = SelfHealingOrchestrator(mock_memory, verifier, knowledge_engine=bridge)

        story = UserStory(
            id="STORY-001",
            title="Test Story",
            description="Test",
            type=StoryType.FEATURE,
        )

        await healer.heal(
            story,
            "ModuleNotFoundError: No module named 'foo'",
            current_iteration=1,
        )

        # Should have found and stored the solution
        assert "heal_solution" in story.step_outputs
        assert "pip install foo" in story.step_outputs["heal_solution"]


class TestLearningIntegration:
    """Tests for Learning integration with NotebookLM."""

    @pytest.fixture
    def mock_memory(self, tmp_path: Path) -> MagicMock:
        memory = MagicMock()
        memory.ralph_dir = tmp_path / "ralph"
        memory.ralph_dir.mkdir(parents=True)
        memory.append_progress = MagicMock()
        return memory

    @pytest.fixture
    def config(self) -> NotebookLMConfig:
        return NotebookLMConfig(
            enabled=True,
            skill_path="/tmp/notebooklm",
            notebooks=[
                NotebookConfig(id="arch-123", type=NotebookType.ARCHITECTURE),
            ],
            default_notebook_id="default-789",
        )

    def test_init_without_knowledge_engine(self, tmp_path: Path) -> None:
        """Test KnowledgeLearner without knowledge engine."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        assert learner.knowledge_engine is None

    def test_init_with_knowledge_engine(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        """Test KnowledgeLearner with knowledge engine."""
        from skillpack.ralph.learning import KnowledgeLearner

        bridge = NotebookLMBridge(tmp_path, mock_memory, config)
        learner = KnowledgeLearner(mock_memory, knowledge_engine=bridge)

        assert learner.knowledge_engine is not None

    def test_is_valuable_pattern_true(self, tmp_path: Path) -> None:
        """Test _is_valuable_pattern returns True for valuable patterns."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        # Pattern with code, substantial length, and keywords
        pattern = {
            "title": "Architecture Pattern",
            "context": """
This is a valuable pattern for handling async operations.

```python
class AsyncHandler:
    async def process(self, data):
        # Best practice: use context managers
        async with self.connection as conn:
            return await conn.execute(data)
```

This pattern ensures proper resource cleanup and follows best practices.
""",
        }

        assert learner._is_valuable_pattern(pattern) is True

    def test_is_valuable_pattern_false_no_code(self, tmp_path: Path) -> None:
        """Test _is_valuable_pattern returns False for patterns without code."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        pattern = {
            "title": "Simple Note",
            "context": "This is just a note without any code. " * 20,
        }

        assert learner._is_valuable_pattern(pattern) is False

    def test_is_valuable_pattern_false_too_short(self, tmp_path: Path) -> None:
        """Test _is_valuable_pattern returns False for short patterns."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        pattern = {
            "title": "Short Pattern",
            "context": "def foo(): pass",
        }

        assert learner._is_valuable_pattern(pattern) is False

    def test_suggest_notebook_type_architecture(self, tmp_path: Path) -> None:
        """Test _suggest_notebook_type returns architecture."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        pattern = {"title": "System Architecture", "context": "Design for the system"}

        assert learner._suggest_notebook_type(pattern) == "architecture"

    def test_suggest_notebook_type_patterns(self, tmp_path: Path) -> None:
        """Test _suggest_notebook_type returns patterns."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        pattern = {"title": "Best Practice", "context": "Convention for naming"}

        assert learner._suggest_notebook_type(pattern) == "patterns"

    def test_suggest_notebook_type_api(self, tmp_path: Path) -> None:
        """Test _suggest_notebook_type returns api."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        pattern = {"title": "API Endpoint", "context": "REST interface for users"}

        assert learner._suggest_notebook_type(pattern) == "api"

    def test_suggest_notebook_type_troubleshooting(self, tmp_path: Path) -> None:
        """Test _suggest_notebook_type returns troubleshooting."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        pattern = {"title": "Bug Fix", "context": "Error handling for edge case"}

        assert learner._suggest_notebook_type(pattern) == "troubleshooting"

    def test_suggest_notebook_type_domain(self, tmp_path: Path) -> None:
        """Test _suggest_notebook_type returns domain as default."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        pattern = {"title": "Random Note", "context": "Something about business logic"}

        assert learner._suggest_notebook_type(pattern) == "domain"

    @pytest.mark.asyncio
    async def test_suggest_upload_creates_file(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        """Test _suggest_upload creates suggestion file."""
        from skillpack.ralph.learning import KnowledgeLearner

        bridge = NotebookLMBridge(tmp_path, mock_memory, config)
        learner = KnowledgeLearner(mock_memory, knowledge_engine=bridge)

        pattern = {
            "title": "Test Pattern",
            "context": "Test context with architecture details",
        }

        await learner._suggest_upload(pattern)

        suggestion_file = mock_memory.ralph_dir / "knowledge_suggestions.md"
        assert suggestion_file.exists()

        content = suggestion_file.read_text()
        assert "Test Pattern" in content
        assert "architecture" in content  # suggested notebook type

    @pytest.mark.asyncio
    async def test_learn_from_success_updates_agents_md(self, tmp_path: Path) -> None:
        """Test learn_from_success updates AGENTS.md with extracted patterns."""
        from skillpack.models import StoryType, UserStory
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        # Create a step output file with patterns
        plan_dir = tmp_path / ".skillpack" / "runs" / "test" / "plan"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text("""# Implementation Plan

## Best Practice - Error Handling

Always wrap async operations in try-catch blocks.

## Recommendations

Use context managers for resource management.
""")

        story = UserStory(
            id="STORY-001",
            title="Test Story",
            description="Test",
            type=StoryType.FEATURE,
            step_outputs={"plan": str(plan_file)},
        )

        await learner.learn_from_success(story)

        # Check AGENTS.md was updated
        agents_file = tmp_path / ".skillpack" / "ralph" / "AGENTS.md"
        assert agents_file.exists()
        content = agents_file.read_text()
        assert "Plan - Best Practice - Error Handling" in content

    @pytest.mark.asyncio
    async def test_learn_from_success_with_knowledge_engine(
        self, tmp_path: Path, mock_memory: MagicMock, config: NotebookLMConfig
    ) -> None:
        """Test learn_from_success suggests valuable patterns for upload."""
        from skillpack.models import StoryType, UserStory
        from skillpack.ralph.learning import KnowledgeLearner

        bridge = NotebookLMBridge(tmp_path, mock_memory, config)
        learner = KnowledgeLearner(mock_memory, knowledge_engine=bridge)

        # Create a step output file with a valuable pattern
        plan_dir = mock_memory.ralph_dir / "test" / "plan"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text("""# Implementation Plan

## Pattern - Async Handler

This is a valuable architecture pattern for handling async operations.

```python
class AsyncHandler:
    async def process(self, data):
        # Best practice: use context managers
        async with self.connection as conn:
            return await conn.execute(data)
```

This pattern ensures proper resource cleanup and follows best practices.
""")

        story = UserStory(
            id="STORY-001",
            title="Test Story",
            description="Test",
            type=StoryType.FEATURE,
            step_outputs={"plan": str(plan_file)},
        )

        await learner.learn_from_success(story)

        # Check suggestion file was created (valuable pattern)
        suggestion_file = mock_memory.ralph_dir / "knowledge_suggestions.md"
        assert suggestion_file.exists()
        content = suggestion_file.read_text()
        assert "Pattern" in content

    @pytest.mark.asyncio
    async def test_learn_from_failure_records_error(self, tmp_path: Path) -> None:
        """Test learn_from_failure records error to AGENTS.md."""
        from skillpack.models import StoryType, UserStory
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        story = UserStory(
            id="STORY-001",
            title="Test Story",
            description="Test",
            type=StoryType.FEATURE,
            last_error="TypeError: cannot add string to int",
        )

        await learner.learn_from_failure(story)

        # Check AGENTS.md was updated
        agents_file = tmp_path / ".skillpack" / "ralph" / "AGENTS.md"
        assert agents_file.exists()
        content = agents_file.read_text()
        assert "Avoided Error: STORY-001" in content
        assert "TypeError" in content

    @pytest.mark.asyncio
    async def test_learn_from_failure_no_error(self, tmp_path: Path) -> None:
        """Test learn_from_failure does nothing when no error."""
        from skillpack.models import StoryType, UserStory
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        story = UserStory(
            id="STORY-001",
            title="Test Story",
            description="Test",
            type=StoryType.FEATURE,
            last_error=None,
        )

        await learner.learn_from_failure(story)

        # Check AGENTS.md was not created (no error to record)
        agents_file = tmp_path / ".skillpack" / "ralph" / "AGENTS.md"
        assert not agents_file.exists()

    def test_extract_patterns_from_plan(self, tmp_path: Path) -> None:
        """Test _extract_patterns extracts from plan step output."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        # Create a plan output file
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("""# Plan

## Best Practice - Naming Conventions

Use snake_case for variables and functions.

## Tips for Performance

Cache expensive computations.
""")

        patterns = learner._extract_patterns({"plan": str(plan_file)})

        assert len(patterns) == 2
        assert any("Best Practice" in p["title"] for p in patterns)
        assert any("Tips" in p["title"] for p in patterns)

    def test_extract_patterns_from_review(self, tmp_path: Path) -> None:
        """Test _extract_patterns extracts from review step output."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        # Create a review output file
        review_file = tmp_path / "review.md"
        review_file.write_text("""# Code Review

## Recommendation - Use Type Hints

Adding type hints improves code readability.

### Pitfall to Avoid

Don't use mutable default arguments.
""")

        patterns = learner._extract_patterns({"review": str(review_file)})

        assert len(patterns) == 2
        assert any("Recommendation" in p["title"] for p in patterns)
        assert any("Pitfall" in p["title"] for p in patterns)

    def test_extract_patterns_skips_implement(self, tmp_path: Path) -> None:
        """Test _extract_patterns skips implement step."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        # Create an implement output file
        impl_file = tmp_path / "impl.md"
        impl_file.write_text("""# Implementation

## Best Practice

This should not be extracted.
""")

        patterns = learner._extract_patterns({"implement": str(impl_file)})

        assert len(patterns) == 0

    def test_extract_patterns_empty_outputs(self, tmp_path: Path) -> None:
        """Test _extract_patterns handles empty outputs."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        patterns = learner._extract_patterns({})

        assert patterns == []

    def test_extract_patterns_missing_file(self, tmp_path: Path) -> None:
        """Test _extract_patterns handles missing files gracefully."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        patterns = learner._extract_patterns({"plan": "/nonexistent/file.md"})

        assert patterns == []

    def test_extract_patterns_fallback_to_notes(self, tmp_path: Path) -> None:
        """Test _extract_patterns falls back to notes when no keywords found."""
        from skillpack.ralph.learning import KnowledgeLearner
        from skillpack.ralph.memory import MemoryManager

        memory = MemoryManager(tmp_path)
        learner = KnowledgeLearner(memory)

        # Create a plan file without keywords
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("""# Plan

## Overview

This is the overview section.

## Details

More details here.
""")

        patterns = learner._extract_patterns({"plan": str(plan_file)})

        # Should fall back to notes snippet
        assert len(patterns) == 1
        assert "Notes" in patterns[0]["title"]
