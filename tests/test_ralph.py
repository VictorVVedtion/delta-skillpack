"""Tests for Ralph industrial automation module."""

from __future__ import annotations

from datetime import datetime

import pytest

from skillpack.models import (
    PRD,
    STORY_PIPELINES,
    RalphSession,
    SkillStep,
    StoryType,
    UserStory,
)
from skillpack.ralph import DevServerManager, MemoryManager, PlaywrightMCPBridge, QualityVerifier

# =============================================================================
# Model Tests
# =============================================================================


class TestStoryType:
    """Tests for StoryType enum."""

    def test_all_types_have_pipelines(self):
        """All story types should have pipeline definitions."""
        for story_type in StoryType:
            assert story_type in STORY_PIPELINES, f"Missing pipeline for {story_type}"

    def test_pipeline_steps_are_valid(self):
        """All pipeline steps should be valid SkillStep values."""
        for story_type, pipeline in STORY_PIPELINES.items():
            for step in pipeline:
                assert isinstance(step, SkillStep), f"Invalid step in {story_type}"


class TestUserStory:
    """Tests for UserStory model."""

    def test_create_minimal_story(self):
        """Test creating a story with minimal fields."""
        story = UserStory(
            id="STORY-001",
            title="Test story",
            description="A test story",
            type=StoryType.FEATURE,
        )
        assert story.id == "STORY-001"
        assert story.priority == "p1"
        assert story.passes is False
        assert story.attempts == 0

    def test_get_pipeline_feature(self):
        """Feature stories should have full pipeline."""
        story = UserStory(
            id="STORY-001",
            title="Feature",
            description="Test",
            type=StoryType.FEATURE,
        )
        pipeline = story.get_pipeline()
        assert SkillStep.PLAN in pipeline
        assert SkillStep.IMPLEMENT in pipeline
        assert SkillStep.REVIEW in pipeline
        assert SkillStep.VERIFY in pipeline

    def test_get_pipeline_ui(self):
        """UI stories should include browser verification."""
        story = UserStory(
            id="STORY-002",
            title="UI",
            description="Test",
            type=StoryType.UI,
        )
        pipeline = story.get_pipeline()
        assert SkillStep.UI in pipeline
        assert SkillStep.BROWSER in pipeline
        assert SkillStep.PLAN not in pipeline

    def test_get_pipeline_test(self):
        """Test stories should skip planning."""
        story = UserStory(
            id="STORY-003",
            title="Test",
            description="Test",
            type=StoryType.TEST,
        )
        pipeline = story.get_pipeline()
        assert SkillStep.PLAN not in pipeline
        assert SkillStep.IMPLEMENT in pipeline


class TestPRD:
    """Tests for PRD model."""

    @pytest.fixture
    def sample_prd(self):
        """Create a sample PRD for testing."""
        return PRD(
            id="PRD-001",
            title="Test PRD",
            description="A test PRD",
            stories=[
                UserStory(
                    id="STORY-001",
                    title="First",
                    description="First story",
                    type=StoryType.FEATURE,
                    priority="p0",
                ),
                UserStory(
                    id="STORY-002",
                    title="Second",
                    description="Second story",
                    type=StoryType.UI,
                    priority="p1",
                    depends_on=["STORY-001"],
                ),
            ],
        )

    def test_is_complete_false_initially(self, sample_prd):
        """PRD should not be complete initially."""
        assert sample_prd.is_complete is False

    def test_is_complete_true_when_all_pass(self, sample_prd):
        """PRD should be complete when all stories pass."""
        for story in sample_prd.stories:
            story.passes = True
        assert sample_prd.is_complete is True

    def test_completion_rate(self, sample_prd):
        """Test completion rate calculation."""
        assert sample_prd.completion_rate == 0.0
        sample_prd.stories[0].passes = True
        assert sample_prd.completion_rate == 0.5
        sample_prd.stories[1].passes = True
        assert sample_prd.completion_rate == 1.0

    def test_next_story_returns_first_pending(self, sample_prd):
        """Next story should be first pending with met dependencies."""
        next_story = sample_prd.next_story()
        assert next_story.id == "STORY-001"

    def test_next_story_respects_dependencies(self, sample_prd):
        """Next story should skip stories with unmet dependencies."""
        # STORY-002 depends on STORY-001, so it should not be next
        sample_prd.stories[0].passes = False
        sample_prd.stories[0].attempts = 3  # Max out first story
        next_story = sample_prd.next_story()
        # STORY-002 still can't be selected because STORY-001 hasn't passed
        assert next_story is None

    def test_next_story_selects_dependent_after_completion(self, sample_prd):
        """Dependent story should be selected after dependency passes."""
        sample_prd.stories[0].passes = True
        next_story = sample_prd.next_story()
        assert next_story.id == "STORY-002"

    def test_next_story_none_when_all_complete(self, sample_prd):
        """Next story should be None when all complete."""
        for story in sample_prd.stories:
            story.passes = True
        assert sample_prd.next_story() is None


class TestRalphSession:
    """Tests for RalphSession model."""

    def test_create_session(self):
        """Test creating a Ralph session."""
        session = RalphSession(
            session_id="sess-001",
            prd_id="PRD-001",
            repo="/tmp/test",
            started_at=datetime.now(),
        )
        assert session.current_iteration == 0
        assert session.completed is False


# =============================================================================
# Memory Manager Tests
# =============================================================================


class TestMemoryManager:
    """Tests for MemoryManager."""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create a memory manager with temp directory."""
        return MemoryManager(tmp_path)

    def test_creates_directories(self, memory):
        """Memory manager should create required directories."""
        assert memory.ralph_dir.exists()
        assert (memory.ralph_dir / "iterations").exists()
        assert (memory.ralph_dir / "screenshots").exists()

    def test_save_load_prd(self, memory):
        """Test saving and loading PRD."""
        prd = PRD(
            id="PRD-001",
            title="Test",
            description="Test PRD",
            stories=[
                UserStory(
                    id="STORY-001",
                    title="Test",
                    description="Test",
                    type=StoryType.FEATURE,
                )
            ],
        )
        memory.save_prd(prd)
        loaded = memory.load_prd()
        assert loaded is not None
        assert loaded.id == "PRD-001"
        assert len(loaded.stories) == 1

    def test_load_prd_returns_none_if_missing(self, memory):
        """Load should return None if no PRD exists."""
        assert memory.load_prd() is None

    def test_append_and_read_progress(self, memory):
        """Test progress log operations."""
        memory.append_progress(1, "STORY-001", "START", "Starting story")
        memory.append_progress(1, "STORY-001", "COMPLETE", "Done")

        progress = memory.read_progress(last_n=10)
        assert "STORY-001" in progress
        assert "START" in progress
        assert "COMPLETE" in progress

    def test_read_progress_limits_lines(self, memory):
        """Progress should limit to last N lines."""
        for i in range(20):
            memory.append_progress(i, f"STORY-{i:03d}", "TEST", f"Message {i}")

        progress = memory.read_progress(last_n=5)
        lines = progress.strip().split("\n")
        assert len(lines) == 5
        assert "STORY-019" in progress

    def test_update_agents_md(self, memory):
        """Test updating knowledge base."""
        memory.update_agents_md("Pattern 1", "Context for pattern 1")
        memory.update_agents_md("Pattern 2", "Context for pattern 2")

        content = memory.read_agents_md()
        assert "Pattern 1" in content
        assert "Pattern 2" in content

    def test_agents_md_no_duplicates(self, memory):
        """Same pattern should not be added twice."""
        memory.update_agents_md("Pattern 1", "Context 1")
        memory.update_agents_md("Pattern 1", "Context 2")

        content = memory.read_agents_md()
        assert content.count("Pattern 1") == 1

    def test_get_iteration_dir(self, memory):
        """Test iteration directory creation."""
        dir1 = memory.get_iteration_dir(1)
        dir2 = memory.get_iteration_dir(2)

        assert dir1.exists()
        assert dir2.exists()
        assert dir1.name == "001"
        assert dir2.name == "002"

    def test_save_step_output(self, memory):
        """Test saving step output."""
        output_path = memory.save_step_output(1, "plan", "# Plan Output\nContent here")

        assert output_path.exists()
        assert output_path.name == "plan_output.md"
        assert "Plan Output" in output_path.read_text()


# =============================================================================
# Quality Verifier Tests
# =============================================================================


class TestQualityVerifier:
    """Tests for QualityVerifier."""

    @pytest.fixture
    def verifier(self, tmp_path):
        """Create a verifier with temp directory."""
        return QualityVerifier(tmp_path)

    @pytest.mark.asyncio
    async def test_verify_with_no_tests(self, verifier):
        """Verify should handle missing test files gracefully."""
        result = await verifier.verify(run_tests=True, run_lint=False)
        # Will fail because no tests exist in temp dir
        assert result.success is False or result.tests_passed is False

    @pytest.mark.asyncio
    async def test_run_custom_commands_success(self, verifier):
        """Test running custom commands that succeed."""
        success, output = await verifier.run_custom_commands(["echo 'hello'"])
        assert success is True
        assert "hello" in output

    @pytest.mark.asyncio
    async def test_run_custom_commands_failure(self, verifier):
        """Test running custom commands that fail."""
        success, output = await verifier.run_custom_commands(["exit 1"])
        assert success is False


# =============================================================================
# Browser Verification Tests
# =============================================================================


def _unused_port() -> int:
    return 65535


class TestPlaywrightMCPBridge:
    """Tests for PlaywrightMCPBridge."""

    @pytest.fixture
    def bridge(self, tmp_path):
        """Create a Playwright MCP bridge with temp directory."""
        memory = MemoryManager(tmp_path)
        return PlaywrightMCPBridge(tmp_path, memory)

    def test_build_verification_prompt(self, bridge):
        """Prompt should include story context and acceptance criteria."""
        story = UserStory(
            id="STORY-001",
            title="UI Test",
            description="Test",
            type=StoryType.UI,
            acceptance_criteria=["Button visible", "Form submits"],
        )
        prompt = bridge._build_verification_prompt(story, "http://localhost:3000")
        assert "STORY-001" in prompt
        assert "Button visible" in prompt
        assert "Form submits" in prompt

    def test_parse_verification_result(self, bridge, tmp_path):
        """Parse JSON verification output."""
        output_file = tmp_path / "result.json"
        output_file.write_text('{"success": true, "message": "OK"}', encoding="utf-8")
        success, message = bridge._parse_verification_result(output_file)
        assert success is True
        assert message == "OK"

    @pytest.mark.asyncio
    async def test_check_server_not_running(self, bridge):
        """Server check should return False if not running."""
        port = _unused_port()
        result = await bridge._check_server(f"http://localhost:{port}")
        assert result is False


# =============================================================================
# Dev Server Manager Tests
# =============================================================================


class TestDevServerManager:
    """Tests for DevServerManager."""

    @pytest.mark.asyncio
    async def test_is_running_false_on_unused_port(self, tmp_path):
        """is_running should return False on an unused port."""
        port = _unused_port()
        manager = DevServerManager(tmp_path, port=port)
        assert await manager.is_running() is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestRalphIntegration:
    """Integration tests for Ralph workflow."""

    @pytest.fixture
    def setup_ralph(self, tmp_path):
        """Set up Ralph environment for testing."""
        memory = MemoryManager(tmp_path)

        prd = PRD(
            id="PRD-INT-001",
            title="Integration Test",
            description="Test PRD for integration",
            stories=[
                UserStory(
                    id="STORY-001",
                    title="First Story",
                    description="First test story",
                    type=StoryType.DOCS,  # Docs type has shortest pipeline
                    priority="p0",
                    acceptance_criteria=["Docs created"],
                ),
            ],
        )
        memory.save_prd(prd)

        return memory, prd

    def test_full_memory_workflow(self, setup_ralph):
        """Test complete memory workflow."""
        memory, prd = setup_ralph

        # Append progress
        memory.append_progress(1, "STORY-001", "START", "Starting")
        memory.append_progress(1, "STORY-001", "PLAN", "Planning")
        memory.append_progress(1, "STORY-001", "IMPLEMENT", "Implementing")
        memory.append_progress(1, "STORY-001", "COMPLETE", "Done")

        # Update knowledge base
        memory.update_agents_md("Test Pattern", "Learned during test")

        # Verify state
        loaded_prd = memory.load_prd()
        assert loaded_prd.id == "PRD-INT-001"

        progress = memory.read_progress()
        assert "STORY-001" in progress
        assert "COMPLETE" in progress

        agents = memory.read_agents_md()
        assert "Test Pattern" in agents

    def test_story_state_persistence(self, setup_ralph):
        """Test that story state persists across saves."""
        memory, prd = setup_ralph

        # Modify story state
        story = prd.stories[0]
        story.attempts = 2
        story.passes = True
        story.step_outputs["plan"] = "/path/to/plan.md"

        memory.save_prd(prd)

        # Reload and verify
        loaded = memory.load_prd()
        loaded_story = loaded.stories[0]

        assert loaded_story.attempts == 2
        assert loaded_story.passes is True
        assert loaded_story.step_outputs["plan"] == "/path/to/plan.md"
