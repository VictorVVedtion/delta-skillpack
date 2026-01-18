"""Development server management for UI verification."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import IO


class DevServerManager:
    """Start/stop and health check a local dev server."""

    def __init__(self, repo: Path, port: int = 3000):
        self.repo = Path(repo)
        self.port = port
        self._process: asyncio.subprocess.Process | None = None
        self._log_handle: IO[str] | None = None
        self._started_by_us = False

    async def start(self, command: str = "npm run dev") -> bool:
        """Start the development server."""
        if await self.is_running():
            return True

        if self._process and self._process.returncode is None:
            return await self.wait_for_ready()

        self._close_log()
        self._ensure_log()

        env = os.environ.copy()
        env["PORT"] = str(self.port)

        try:
            self._process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.repo),
                stdout=self._log_handle,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
        except Exception:
            self._close_log()
            self._process = None
            self._started_by_us = False
            return False

        self._started_by_us = True
        return await self.wait_for_ready()

    async def stop(self) -> None:
        """Stop the development server if we started it."""
        if not self._started_by_us or not self._process:
            return

        if self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=10)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()

        self._process = None
        self._started_by_us = False
        self._close_log()

    async def is_running(self) -> bool:
        """Check whether the server is running."""
        if self._process and self._process.returncode is not None:
            return False
        return await self._check_port()

    async def wait_for_ready(self, timeout: int = 30) -> bool:
        """Wait until the dev server accepts connections."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self._process and self._process.returncode is not None:
                return False
            if await self._check_port():
                return True
            await asyncio.sleep(0.5)
        return False

    async def _check_port(self) -> bool:
        try:
            conn = asyncio.open_connection("127.0.0.1", self.port)
            reader, writer = await asyncio.wait_for(conn, timeout=2)
            writer.close()
            if hasattr(writer, "wait_closed"):
                await writer.wait_closed()
            return True
        except Exception:
            return False

    def _ensure_log(self) -> None:
        log_dir = self.repo / ".skillpack" / "ralph"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "dev_server.log"
        self._log_handle = log_path.open("a", encoding="utf-8")

    def _close_log(self) -> None:
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None
