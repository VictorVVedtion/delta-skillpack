"""Quality verification for Ralph automation.

Handles test execution and lint checking as quality gates.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerifyResult:
    """Result of quality verification."""

    success: bool
    tests_passed: bool = True
    lint_passed: bool = True
    test_output: str = ""
    lint_output: str = ""
    error: str | None = None


class QualityVerifier:
    """Execute quality gates (pytest + ruff)."""

    def __init__(self, repo: Path):
        self.repo = Path(repo)

    async def verify(
        self,
        run_tests: bool = True,
        run_lint: bool = True,
        test_pattern: str | None = None,
    ) -> VerifyResult:
        """Run all verification checks."""
        result = VerifyResult(success=True)

        if run_tests:
            test_result = await self._run_pytest(test_pattern)
            result.tests_passed = test_result[0]
            result.test_output = test_result[1]
            if not test_result[0]:
                result.success = False
                result.error = f"Tests failed: {test_result[1][:500]}"

        if run_lint:
            lint_result = await self._run_ruff()
            result.lint_passed = lint_result[0]
            result.lint_output = lint_result[1]
            if not lint_result[0]:
                result.success = False
                result.error = f"Lint failed: {lint_result[1][:500]}"

        return result

    async def _run_pytest(
        self,
        pattern: str | None = None,
    ) -> tuple[bool, str]:
        """Run pytest and return (success, output)."""
        cmd = ["pytest", "--tb=short", "-q"]
        if pattern:
            cmd.append(pattern)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.repo),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=300,
            )
            output = stdout.decode() + stderr.decode()
            return proc.returncode == 0, output
        except TimeoutError:
            return False, "Tests timed out after 300s"
        except Exception as e:
            return False, str(e)

    async def _run_ruff(self) -> tuple[bool, str]:
        """Run ruff and return (success, output)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                ".",
                cwd=str(self.repo),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=60,
            )
            output = stdout.decode() + stderr.decode()
            return proc.returncode == 0, output
        except TimeoutError:
            return False, "Lint timed out after 60s"
        except Exception as e:
            return False, str(e)

    async def run_custom_commands(
        self,
        commands: list[str],
    ) -> tuple[bool, str]:
        """Run custom verification commands."""
        all_output = []
        for cmd in commands:
            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=str(self.repo),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=120,
                )
                output = stdout.decode() + stderr.decode()
                all_output.append(f"$ {cmd}\n{output}")
                if proc.returncode != 0:
                    return False, "\n".join(all_output)
            except Exception as e:
                all_output.append(f"$ {cmd}\nError: {e}")
                return False, "\n".join(all_output)
        return True, "\n".join(all_output)
