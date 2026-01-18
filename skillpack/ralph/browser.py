"""Playwright MCP integration for UI story verification."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..engines import ClaudeEngine
from ..models import ClaudeConfig, RalphConfig, UserStory
from .memory import MemoryManager


class PlaywrightMCPBridge:
    """Bridge to trigger Playwright MCP verification via Claude."""

    def __init__(
        self,
        repo: Path,
        memory: MemoryManager,
        ralph_config: RalphConfig | None = None,
    ):
        self.repo = Path(repo)
        self.memory = memory
        self.config = ralph_config or RalphConfig()

    async def verify_ui_story(
        self,
        story: UserStory,
        dev_url: str = "http://localhost:3000",
    ) -> tuple[bool, str]:
        """Trigger Playwright MCP verification via a Claude prompt."""
        if not await self._check_server(dev_url):
            return False, f"Dev server not running at {dev_url}"

        prompt = self._build_verification_prompt(story, dev_url)

        # Use model from config instead of hardcoding
        engine = ClaudeEngine(
            ClaudeConfig(
                model=self.config.claude_model,
                timeout_seconds=self.config.claude_timeout_seconds,
            )
        )
        output_file = self.memory.ralph_dir / "browser_verify_result.json"
        result = await engine.execute(self.repo, prompt, output_file)

        if not result.success:
            return False, result.error or "Browser verification failed"

        return self._parse_verification_result(output_file)

    def _build_verification_prompt(self, story: UserStory, dev_url: str) -> str:
        """Build a Playwright MCP verification prompt."""
        acceptance = "\n".join(f"- {item}" for item in story.acceptance_criteria)
        if not acceptance:
            acceptance = "- (none)"

        screenshot_path = self.memory.ralph_dir / "screenshots" / f"{story.id}.png"

        return f"""You are a UI verification agent. Use Playwright MCP tools
to validate a local dev server.

Target URL: {dev_url}

Story ID: {story.id}
Title: {story.title}
Description: {story.description}

Acceptance Criteria:
{acceptance}

Instructions:
- Open the target URL in a browser via Playwright MCP.
- Verify each acceptance criterion with concrete UI checks.
- Capture one representative screenshot and save it to: {screenshot_path}
- If a check cannot be validated, mark it failed and explain why.
- If the page fails to load, return success=false.

Return ONLY a JSON object (no markdown, no commentary) with this schema:
{{
  "success": true|false,
  "message": "short summary",
  "url": "{dev_url}",
  "screenshot": "{screenshot_path}",
  "checks": [
    {{"criterion": "...", "passed": true|false, "notes": "..."}}
  ]
}}
"""

    def _parse_verification_result(self, output_file: Path) -> tuple[bool, str]:
        """Parse JSON verification result."""
        if not output_file.exists():
            return False, f"Missing verification output: {output_file}"

        content = output_file.read_text(encoding="utf-8").strip()
        if not content:
            return False, "Browser verification returned empty output"

        data = self._extract_json(content)
        if data is None:
            snippet = content[:300]
            return False, f"Unable to parse verification JSON: {snippet}"

        success_value = data.get("success")
        if isinstance(success_value, str):
            success = success_value.strip().lower() == "true"
        else:
            success = bool(success_value)

        message = data.get("message") or data.get("summary")
        if not success:
            message = message or data.get("error") or "Browser verification failed"
        else:
            message = message or "Browser verification completed"

        return success, message

    async def _check_server(self, url: str, timeout: int = 5) -> bool:
        """Check whether the development server is running."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or "localhost"
            port = parsed.port
            if port is None:
                port = 443 if parsed.scheme == "https" else 80

            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            writer.close()
            if hasattr(writer, "wait_closed"):
                await writer.wait_closed()
            return True
        except Exception:
            return False

    def _extract_json(self, content: str) -> dict[str, Any] | None:
        """Extract JSON object from raw output."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return None
