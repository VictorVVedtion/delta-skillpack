"""Self-healing logic for Ralph automation.

Classifies errors and applies lightweight remediation steps.
"""
from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from enum import Enum

from ..models import UserStory
from .memory import MemoryManager
from .verify import QualityVerifier


class ErrorCategory(Enum):
    SYNTAX = "syntax"
    IMPORT = "import"
    TYPE = "type"
    TEST_FAILURE = "test"
    LINT = "lint"
    RUNTIME = "runtime"
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"


@dataclass
class HealingStrategy:
    category: ErrorCategory
    action: str  # regenerate, fix_imports, analyze_and_fix, auto_format, wait_and_retry
    prompt_modifier: str | None = None
    wait_seconds: float = 0
    max_attempts: int = 3


class SelfHealingOrchestrator:
    STRATEGIES = {
        ErrorCategory.SYNTAX: HealingStrategy(
            ErrorCategory.SYNTAX,
            "regenerate",
            "Previous attempt had syntax errors...",
        ),
        ErrorCategory.IMPORT: HealingStrategy(
            ErrorCategory.IMPORT,
            "fix_imports",
            "Fix import errors...",
        ),
        ErrorCategory.TEST_FAILURE: HealingStrategy(
            ErrorCategory.TEST_FAILURE,
            "analyze_and_fix",
            "Test failed: {error_output}",
        ),
        ErrorCategory.LINT: HealingStrategy(
            ErrorCategory.LINT,
            "auto_format",
        ),
        ErrorCategory.RATE_LIMIT: HealingStrategy(
            ErrorCategory.RATE_LIMIT,
            "wait_and_retry",
            wait_seconds=60,
        ),
    }

    def __init__(self, memory: MemoryManager, verifier: QualityVerifier):
        self.memory = memory
        self.verifier = verifier
        self._attempts: dict[tuple[str, ErrorCategory], int] = {}

    def classify_error(self, error_msg: str) -> ErrorCategory:
        """Classify errors based on simple keyword heuristics."""
        message = (error_msg or "").lower()
        if not message:
            return ErrorCategory.RUNTIME

        if any(token in message for token in ("rate limit", "too many requests", "429")):
            return ErrorCategory.RATE_LIMIT
        if "syntax" in message or "invalid syntax" in message:
            return ErrorCategory.SYNTAX
        if any(
            token in message
            for token in ("importerror", "modulenotfounderror", "no module named")
        ):
            return ErrorCategory.IMPORT
        if "typeerror" in message or "mypy" in message or "typing" in message:
            return ErrorCategory.TYPE
        if "lint" in message or "ruff" in message:
            return ErrorCategory.LINT
        if any(token in message for token in ("pytest", "tests failed", "assertionerror")):
            return ErrorCategory.TEST_FAILURE
        if any(
            token in message
            for token in ("network", "connection", "socket", "dns", "connect timeout")
        ):
            return ErrorCategory.NETWORK
        return ErrorCategory.RUNTIME

    async def heal(
        self,
        story: UserStory,
        error_msg: str,
        current_iteration: int,
    ) -> bool:
        """Attempt self-healing based on error classification."""
        category = self.classify_error(error_msg)
        strategy = self.STRATEGIES.get(category)
        if not strategy:
            self.memory.append_progress(
                current_iteration,
                story.id,
                "HEAL:SKIP",
                f"No strategy for {category.value}",
            )
            return False

        key = (story.id, category)
        attempts = self._attempts.get(key, 0)
        if attempts >= strategy.max_attempts:
            self.memory.append_progress(
                current_iteration,
                story.id,
                "HEAL:MAX",
                f"Max attempts reached for {category.value}",
            )
            return False

        self._attempts[key] = attempts + 1
        prompt_modifier = strategy.prompt_modifier
        if prompt_modifier:
            with contextlib.suppress(Exception):
                prompt_modifier = prompt_modifier.format(error_output=error_msg)
            story.step_outputs["self_heal_prompt"] = prompt_modifier

        self.memory.append_progress(
            current_iteration,
            story.id,
            f"HEAL:{strategy.action}",
            f"{category.value} -> {strategy.action} "
            f"({self._attempts[key]}/{strategy.max_attempts})",
        )

        if strategy.action == "wait_and_retry":
            await asyncio.sleep(strategy.wait_seconds)
            return True
        if strategy.action in {"auto_format", "fix_imports"}:
            return await self._run_auto_format()
        return strategy.action in {"regenerate", "analyze_and_fix"}

    async def _run_auto_format(self) -> bool:
        """Run ruff --fix auto format."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "--fix",
                ".",
                cwd=str(self.verifier.repo),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)
            return proc.returncode == 0
        except Exception:
            return False
