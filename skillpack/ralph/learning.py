"""Knowledge learning for Ralph automation.

Extracts reusable patterns and stores them in the AGENTS.md knowledge base.
"""
from __future__ import annotations

from pathlib import Path

from ..models import UserStory
from .memory import MemoryManager


class KnowledgeLearner:
    def __init__(self, memory: MemoryManager):
        self.memory = memory

    async def learn_from_success(self, story: UserStory) -> None:
        """Extract patterns from successful story outputs and update AGENTS.md."""
        patterns = self._extract_patterns(story.step_outputs)
        for pattern in patterns:
            self.memory.update_agents_md(pattern["title"], pattern["context"])

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
            except Exception:
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
