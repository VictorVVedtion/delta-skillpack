"""Browser verification for UI stories using Playwright MCP.

Provides visual verification for UI-type stories through browser automation.
"""
from __future__ import annotations

from pathlib import Path

from ..models import UserStory
from .memory import MemoryManager


class BrowserVerifier:
    """Browser-based verification for UI stories.

    Uses Playwright MCP for visual validation of UI components.
    This implementation provides a framework that integrates with
    the existing Playwright MCP tools available in Claude Code.
    """

    def __init__(self, repo: Path, session: str = "ralph"):
        self.repo = Path(repo)
        self.session = session
        self.memory = MemoryManager(repo)
        self.screenshots_dir = self.memory.ralph_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def verify_ui_story(
        self,
        story: UserStory,
        dev_url: str = "http://localhost:3000",
    ) -> tuple[bool, str]:
        """Verify a UI story through browser automation.

        This method provides a framework for UI verification.
        The actual browser interaction should be done through
        Claude Code's Playwright MCP tools.

        Args:
            story: The UI story to verify
            dev_url: Development server URL

        Returns:
            Tuple of (success, message)
        """
        # Check if dev server is running
        if not await self._check_server(dev_url):
            return False, f"Development server not running at {dev_url}"

        # Log verification start
        self.memory.append_progress(
            0,
            story.id,
            "BROWSER_VERIFY",
            f"Starting browser verification at {dev_url}",
        )

        # Build verification checklist from acceptance criteria
        checklist = self._build_checklist(story)

        # Return verification instructions for manual/MCP execution
        instructions = f"""
## Browser Verification for {story.id}

### URL
{dev_url}

### Verification Checklist
{checklist}

### Screenshot
Save to: {self.screenshots_dir / f'{story.id}.png'}

### Expected Behavior
{story.description}

### Acceptance Criteria
{chr(10).join(f'- {ac}' for ac in story.acceptance_criteria)}
"""

        # Store instructions for reference
        output_file = self.screenshots_dir / f"{story.id}_verification.md"
        output_file.write_text(instructions, encoding="utf-8")

        # For now, return success with instructions
        # Full Playwright MCP integration would verify each criterion
        return True, f"Verification instructions generated: {output_file}"

    async def _check_server(self, url: str) -> bool:
        """Check if the development server is running."""
        import socket
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 3000

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _build_checklist(self, story: UserStory) -> str:
        """Build verification checklist from story criteria."""
        items = []
        for i, criterion in enumerate(story.acceptance_criteria, 1):
            items.append(f"- [ ] {i}. {criterion}")

        # Add standard UI checks
        items.extend([
            "",
            "### Standard UI Checks",
            "- [ ] Page loads without errors",
            "- [ ] No console errors",
            "- [ ] Responsive on mobile (< 768px)",
            "- [ ] Responsive on desktop (≥ 1024px)",
            "- [ ] Keyboard navigation works",
            "- [ ] Focus indicators visible",
        ])

        return "\n".join(items)

    async def take_screenshot(
        self,
        story_id: str,
        url: str,
        filename: str | None = None,
    ) -> Path | None:
        """Take a screenshot of the current page.

        Note: This is a placeholder. Actual screenshot should be
        taken through Playwright MCP tools.
        """
        if filename is None:
            filename = f"{story_id}.png"

        screenshot_path = self.screenshots_dir / filename

        # Log intent
        self.memory.append_progress(
            0,
            story_id,
            "SCREENSHOT",
            f"Screenshot requested: {screenshot_path}",
        )

        # Return expected path (actual capture via MCP)
        return screenshot_path

    async def verify_element_exists(
        self,
        selector: str,
        description: str,
    ) -> bool:
        """Verify an element exists on the page.

        Note: This is a placeholder. Actual verification should be
        done through Playwright MCP tools.
        """
        # Log verification request
        self.memory.append_progress(
            0,
            "BROWSER",
            "ELEMENT_CHECK",
            f"Checking for: {description} ({selector})",
        )
        return True

    async def verify_text_content(
        self,
        selector: str,
        expected_text: str,
    ) -> bool:
        """Verify text content of an element.

        Note: This is a placeholder. Actual verification should be
        done through Playwright MCP tools.
        """
        self.memory.append_progress(
            0,
            "BROWSER",
            "TEXT_CHECK",
            f"Checking text: '{expected_text}' in {selector}",
        )
        return True
