"""Engine abstraction layer with async execution."""

from __future__ import annotations

import asyncio
import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from .models import ClaudeConfig, CodexConfig, GeminiConfig, RunResult


@runtime_checkable
class Engine(Protocol):
    """Protocol for execution engines."""

    @property
    def name(self) -> str: ...

    @property
    def available(self) -> bool: ...

    async def execute(
        self,
        repo: Path,
        prompt: str,
        output_file: Path,
        variant: int = 1,
    ) -> RunResult: ...


class BaseEngine(ABC):
    """Base class with common utilities."""

    def __init__(self):
        self._binary: str | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name identifier."""
        ...

    @property
    def available(self) -> bool:
        return shutil.which(self._binary) is not None if self._binary else False

    async def _run_process(
        self,
        cmd: list[str],
        cwd: Path,
        input_text: str | None = None,
        timeout: int = 600,
    ) -> tuple[int, str, str]:
        """Run subprocess with async support and timeout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdin=asyncio.subprocess.PIPE if input_text else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input_text.encode() if input_text else None),
                timeout=timeout,
            )
            return proc.returncode or 0, stdout.decode(), stderr.decode()
        except asyncio.TimeoutError:  # noqa: UP041 - needed for Python 3.10 compatibility
            proc.kill()
            await proc.wait()  # Ensure process is cleaned up
            return -1, "", f"Process timed out after {timeout}s"
        except OSError as e:
            return -1, "", f"Process execution failed: {e}"


class CodexEngine(BaseEngine):
    """OpenAI Codex CLI engine."""

    def __init__(self, config: CodexConfig):
        super().__init__()
        self._binary = "codex"
        self.config = config

    @property
    def name(self) -> str:
        return "codex"

    async def execute(
        self,
        repo: Path,
        prompt: str,
        output_file: Path,
        variant: int = 1,
    ) -> RunResult:
        start = time.perf_counter()

        if not self.available:
            return RunResult(
                variant=variant,
                success=False,
                error="codex not found. Install: npm i -g @openai/codex",
            )

        cmd = ["codex", "exec"]

        if self.config.full_auto:
            cmd.append("--full-auto")

        cmd += ["--sandbox", self.config.sandbox.value]

        if self.config.model:
            cmd += ["--model", self.config.model]

        # Note: reasoning_effort is set via model selection (o3 models support extended reasoning)
        # Codex CLI doesn't have a --reasoning-effort flag, use -c for config if needed

        cmd += ["--output-last-message", str(output_file), "-"]

        variant_prompt = f"{prompt}\n\n(Variation tag: V{variant})\n"

        returncode, stdout, stderr = await self._run_process(
            cmd, repo, variant_prompt, self.config.timeout_seconds
        )

        duration = int((time.perf_counter() - start) * 1000)

        return RunResult(
            variant=variant,
            success=returncode == 0,
            output_file=output_file if returncode == 0 else None,
            duration_ms=duration,
            error=stderr[:2000] if returncode != 0 else None,
            stdout=stdout[:2000] if stdout else None,
            stderr=stderr[:2000] if stderr else None,
        )


class GeminiEngine(BaseEngine):
    """Google Gemini CLI engine."""

    def __init__(self, config: GeminiConfig):
        super().__init__()
        self._binary = "gemini"
        self.config = config

    @property
    def name(self) -> str:
        return "gemini"

    async def execute(
        self,
        repo: Path,
        prompt: str,
        output_file: Path,
        variant: int = 1,
    ) -> RunResult:
        start = time.perf_counter()

        if not self.available:
            return RunResult(
                variant=variant,
                success=False,
                error="gemini not found. Install: npm i -g @google/gemini-cli",
            )

        cmd = ["gemini", "--prompt", prompt]

        returncode, stdout, stderr = await self._run_process(
            cmd, repo, timeout=self.config.timeout_seconds
        )

        duration = int((time.perf_counter() - start) * 1000)

        if returncode == 0:
            output_file.write_text(stdout, encoding="utf-8")

        return RunResult(
            variant=variant,
            success=returncode == 0,
            output_file=output_file if returncode == 0 else None,
            duration_ms=duration,
            error=stderr[:2000] if returncode != 0 else None,
            stdout=stdout[:2000] if stdout else None,
            stderr=stderr[:2000] if stderr else None,
        )


class ClaudeEngine(BaseEngine):
    """Claude Code CLI engine (future)."""

    def __init__(self, config: ClaudeConfig):
        super().__init__()
        self._binary = "claude"
        self.config = config

    @property
    def name(self) -> str:
        return "claude"

    async def execute(
        self,
        repo: Path,
        prompt: str,
        output_file: Path,
        variant: int = 1,
    ) -> RunResult:
        start = time.perf_counter()

        if not self.available:
            return RunResult(
                variant=variant,
                success=False,
                error="claude not found. Install: npm i -g @anthropic-ai/claude-code",
            )

        cmd = ["claude", "--print"]

        if self.config.dangerously_skip_permissions:
            cmd += ["--dangerously-skip-permissions"]

        cmd += ["--model", self.config.model]

        # Note: extended_thinking is enabled via model selection (opus models support it)
        # Claude CLI doesn't have a --thinking-budget flag

        cmd += ["-p", prompt]

        returncode, stdout, stderr = await self._run_process(
            cmd, repo, timeout=self.config.timeout_seconds
        )

        duration = int((time.perf_counter() - start) * 1000)

        if returncode == 0:
            output_file.write_text(stdout, encoding="utf-8")

        return RunResult(
            variant=variant,
            success=returncode == 0,
            output_file=output_file if returncode == 0 else None,
            duration_ms=duration,
            error=stderr[:2000] if returncode != 0 else None,
            stdout=stdout[:2000] if stdout else None,
            stderr=stderr[:2000] if stderr else None,
        )


def get_engine(engine_type: str, config: dict | None = None) -> Engine:
    """Factory for engine instances."""
    engines = {
        "codex": (CodexEngine, CodexConfig),
        "gemini": (GeminiEngine, GeminiConfig),
        "claude": (ClaudeEngine, ClaudeConfig),
    }

    if engine_type not in engines:
        raise ValueError(f"Unknown engine: {engine_type}")

    engine_cls, config_cls = engines[engine_type]
    cfg = config_cls(**(config or {}))
    return engine_cls(cfg)
