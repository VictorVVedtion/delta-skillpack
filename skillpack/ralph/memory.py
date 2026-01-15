"""Memory persistence for Ralph automation.

4 Memory Channels:
- PRD State: .skillpack/ralph/prd.json (JSON read/write)
- Progress Log: .skillpack/ralph/progress.txt (append-only)
- Knowledge Base: .skillpack/ralph/AGENTS.md (append-only)
- Git History: git log (read-only)
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from ..models import PRD, RalphSession


class MemoryManager:
    """Persistent memory management across iterations."""

    def __init__(self, repo: Path):
        self.repo = Path(repo)
        self.ralph_dir = self.repo / ".skillpack" / "ralph"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        self.ralph_dir.mkdir(parents=True, exist_ok=True)
        (self.ralph_dir / "iterations").mkdir(exist_ok=True)
        (self.ralph_dir / "screenshots").mkdir(exist_ok=True)

    # =========================================================================
    # PRD Management
    # =========================================================================

    def load_prd(self) -> PRD | None:
        """Load PRD from disk."""
        prd_file = self.ralph_dir / "prd.json"
        if not prd_file.exists():
            return None
        try:
            data = json.loads(prd_file.read_text(encoding="utf-8"))
            return PRD.model_validate(data)
        except Exception:
            return None

    def save_prd(self, prd: PRD) -> None:
        """Save PRD to disk."""
        prd_file = self.ralph_dir / "prd.json"
        prd_file.write_text(
            prd.model_dump_json(indent=2),
            encoding="utf-8",
        )

    # =========================================================================
    # Session Management
    # =========================================================================

    def load_session(self) -> RalphSession | None:
        """Load session state from disk."""
        session_file = self.ralph_dir / "session.json"
        if not session_file.exists():
            return None
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            return RalphSession.model_validate(data)
        except Exception:
            return None

    def save_session(self, session: RalphSession) -> None:
        """Save session state to disk."""
        session_file = self.ralph_dir / "session.json"
        session_file.write_text(
            session.model_dump_json(indent=2),
            encoding="utf-8",
        )

    # =========================================================================
    # Progress Log (append-only)
    # =========================================================================

    def append_progress(
        self,
        iteration: int,
        story_id: str,
        action: str,
        message: str,
    ) -> None:
        """Append to progress log."""
        timestamp = datetime.now().isoformat()
        line = f"[{timestamp}] I{iteration:03d} | {story_id} | {action}: {message}\n"
        progress_file = self.ralph_dir / "progress.txt"
        with progress_file.open("a", encoding="utf-8") as f:
            f.write(line)

    def read_progress(self, last_n: int = 30) -> str:
        """Read last N lines from progress log."""
        progress_file = self.ralph_dir / "progress.txt"
        if not progress_file.exists():
            return ""
        lines = progress_file.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[-last_n:])

    # =========================================================================
    # Knowledge Base (AGENTS.md)
    # =========================================================================

    def update_agents_md(self, pattern: str, context: str) -> None:
        """Update knowledge base with new pattern."""
        agents_file = self.ralph_dir / "AGENTS.md"
        content = (
            agents_file.read_text(encoding="utf-8")
            if agents_file.exists()
            else "# Team Knowledge\n\n"
        )
        if pattern not in content:
            content += f"\n## {pattern}\n{context}\n"
            agents_file.write_text(content, encoding="utf-8")

    def read_agents_md(self) -> str:
        """Read knowledge base."""
        agents_file = self.ralph_dir / "AGENTS.md"
        if not agents_file.exists():
            return ""
        return agents_file.read_text(encoding="utf-8")

    # =========================================================================
    # Git History (read-only)
    # =========================================================================

    def get_git_summary(self, count: int = 10) -> str:
        """Get recent Git commit summary."""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"-{count}"],
                cwd=str(self.repo),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def get_git_diff(self, base: str = "HEAD~5") -> str:
        """Get recent Git diff."""
        try:
            result = subprocess.run(
                ["git", "diff", base, "--stat"],
                cwd=str(self.repo),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    # =========================================================================
    # Iteration Output
    # =========================================================================

    def get_iteration_dir(self, iteration: int) -> Path:
        """Get directory for iteration outputs."""
        iteration_dir = self.ralph_dir / "iterations" / f"{iteration:03d}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        return iteration_dir

    def save_step_output(
        self,
        iteration: int,
        step: str,
        content: str,
    ) -> Path:
        """Save step output to iteration directory."""
        iteration_dir = self.get_iteration_dir(iteration)
        output_file = iteration_dir / f"{step}_output.md"
        output_file.write_text(content, encoding="utf-8")
        return output_file
