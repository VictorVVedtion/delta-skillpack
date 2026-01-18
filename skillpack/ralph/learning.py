"""Knowledge learning for Ralph automation.

Extracts reusable patterns and stores them in the AGENTS.md knowledge base.
Optionally suggests valuable patterns for upload to NotebookLM.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..models import UserStory
from .memory import MemoryManager

if TYPE_CHECKING:
    from .notebooklm import NotebookLMBridge


class KnowledgeLearner:
    """Learns patterns from story execution and updates knowledge bases.

    When a knowledge_engine is provided, suggests valuable patterns
    for upload to NotebookLM.
    """

    # Keywords that indicate a valuable pattern
    VALUABLE_KEYWORDS = [
        "pattern",
        "solution",
        "approach",
        "learned",
        "best practice",
        "architecture",
        "refactor",
        "optimization",
    ]

    def __init__(
        self,
        memory: MemoryManager,
        knowledge_engine: NotebookLMBridge | None = None,
    ):
        self.memory = memory
        self.knowledge_engine = knowledge_engine

    async def learn_from_success(self, story: UserStory) -> None:
        """Extract patterns from successful story outputs and update AGENTS.md.

        If knowledge_engine is available, also suggests valuable patterns
        for upload to NotebookLM.
        """
        patterns = self._extract_patterns(story.step_outputs)

        for pattern in patterns:
            # 1. Update local AGENTS.md
            self.memory.update_agents_md(pattern["title"], pattern["context"])

            # 2. If valuable, suggest upload to NotebookLM
            if self.knowledge_engine and self._is_valuable_pattern(pattern):
                await self._suggest_upload(pattern)

    async def learn_from_failure(self, story: UserStory) -> None:
        """Record failure reasons to AGENTS.md."""
        if story.last_error:
            self.memory.update_agents_md(
                f"Avoided Error: {story.id}",
                f"Error: {story.last_error[:500]}\nContext: {story.title}",
            )

    def _extract_patterns(self, step_outputs: dict) -> list[dict]:
        """Extract reusable patterns from step outputs."""
        if not step_outputs:
            return []

        patterns: list[dict] = []
        keywords = (
            "pattern",
            "lesson",
            "pitfall",
            "best practice",
            "recommend",
            "tip",
            "gotcha",
        )

        for step, output_path in step_outputs.items():
            if step not in {"plan", "review"}:
                continue
            if not output_path:
                continue

            path = Path(output_path)
            if not path.exists():
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue

            sections: list[tuple[str, str]] = []
            current_title: str | None = None
            current_lines: list[str] = []

            for line in text.splitlines():
                heading = None
                if line.startswith("## "):
                    heading = line[3:].strip()
                elif line.startswith("### "):
                    heading = line[4:].strip()

                if heading is not None:
                    if current_title is not None:
                        sections.append((current_title, "\n".join(current_lines).strip()))
                    current_title = heading
                    current_lines = []
                elif current_title is not None:
                    current_lines.append(line)

            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))

            step_patterns = []
            for title, body in sections:
                title_lower = title.lower()
                if not any(keyword in title_lower for keyword in keywords):
                    continue
                if not body:
                    continue
                step_patterns.append(
                    {
                        "title": f"{step.title()} - {title}",
                        "context": body[:500],
                    }
                )

            if not step_patterns and text.strip():
                snippet = "\n".join(text.strip().splitlines()[:8]).strip()
                if snippet:
                    step_patterns.append(
                        {
                            "title": f"{step.title()} Notes",
                            "context": snippet[:500],
                        }
                    )

            patterns.extend(step_patterns)

        return patterns

    def _is_valuable_pattern(self, pattern: dict) -> bool:
        """Determine if a pattern is valuable enough to suggest for upload.

        Criteria:
        - Contains code snippets (``` or def/class keywords)
        - Is substantial (>200 characters)
        - Contains valuable keywords

        Args:
            pattern: Pattern dict with 'title' and 'context' keys

        Returns:
            True if the pattern meets all criteria for upload suggestion
        """
        context = pattern.get("context", "")

        # Check for code content
        has_code = (
            "```" in context or "def " in context or "class " in context or "import " in context
        )

        # Check for substantial content
        is_substantial = len(context) > 200

        # Check for valuable keywords
        context_lower = context.lower()
        has_keywords = any(kw in context_lower for kw in self.VALUABLE_KEYWORDS)

        return has_code and is_substantial and has_keywords

    async def _suggest_upload(self, pattern: dict) -> None:
        """Write pattern to knowledge_suggestions.md for potential NotebookLM upload.

        Args:
            pattern: Pattern dict with 'title' and 'context' keys
        """
        suggestion_file = self.memory.ralph_dir / "knowledge_suggestions.md"

        suggestion_file.parent.mkdir(parents=True, exist_ok=True)

        notebook_type = self._suggest_notebook_type(pattern)
        timestamp = datetime.now().isoformat()

        suggestion = f"""
## Suggested Pattern: {pattern["title"]}

**Extracted at:** {timestamp}
**Suggested Notebook:** {notebook_type}

**Context:**
{pattern["context"]}

---
"""

        try:
            with suggestion_file.open("a", encoding="utf-8") as f:
                f.write(suggestion)
        except OSError:
            # Graceful degradation - don't fail if we can't write suggestions
            pass

    def _suggest_notebook_type(self, pattern: dict) -> str:
        """Determine which NotebookLM notebook type is most appropriate.

        Args:
            pattern: Pattern dict with 'title' and 'context' keys

        Returns:
            Notebook type name (architecture, patterns, api, troubleshooting, domain)
        """
        context = pattern.get("context", "").lower()
        title = pattern.get("title", "").lower()
        combined = f"{title} {context}"

        if any(kw in combined for kw in ["architecture", "design", "system", "structure"]):
            return "architecture"
        elif any(kw in combined for kw in ["pattern", "best practice", "idiom", "convention"]):
            return "patterns"
        elif any(kw in combined for kw in ["api", "endpoint", "interface", "http", "rest"]):
            return "api"
        elif any(kw in combined for kw in ["error", "fix", "bug", "issue", "problem", "debug"]):
            return "troubleshooting"
        else:
            return "domain"
