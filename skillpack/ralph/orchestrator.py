"""Story orchestrator for Ralph automation.

Routes stories to appropriate skill pipelines based on story type.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..core import SkillRunner
from ..models import PRD, SkillStep, UserStory
from .memory import MemoryManager
from .verify import QualityVerifier

if TYPE_CHECKING:
    pass


class StoryOrchestrator:
    """Story execution orchestrator - dispatches skill pipelines."""

    def __init__(self, repo: Path):
        self.repo = Path(repo)
        self.memory = MemoryManager(repo)
        self.runner = SkillRunner(repo)
        self.verifier = QualityVerifier(repo)
        self._current_iteration = 0

    async def execute_story(self, story: UserStory) -> bool:
        """Execute a story through its skill pipeline.

        Returns True if all steps pass, False otherwise.
        """
        pipeline = story.get_pipeline()
        story.attempts += 1
        story.current_step = None

        self.memory.append_progress(
            self._current_iteration,
            story.id,
            "START",
            f"Executing {story.type.value} story: {story.title}",
        )

        for step in pipeline:
            story.current_step = step
            self._save_state()

            try:
                success = await self._execute_step(story, step)
                if not success:
                    story.last_error = f"Step {step.value} failed"
                    self.memory.append_progress(
                        self._current_iteration,
                        story.id,
                        f"FAIL:{step.value}",
                        story.last_error or "Unknown error",
                    )
                    return False
            except Exception as e:
                story.last_error = str(e)
                self.memory.append_progress(
                    self._current_iteration,
                    story.id,
                    f"ERROR:{step.value}",
                    str(e)[:200],
                )
                return False

        # All steps passed
        story.passes = True
        story.completed_at = datetime.now()
        story.current_step = None

        self.memory.append_progress(
            self._current_iteration,
            story.id,
            "COMPLETE",
            f"Story completed successfully after {story.attempts} attempt(s)",
        )

        return True

    async def _execute_step(self, story: UserStory, step: SkillStep) -> bool:
        """Execute a single step in the pipeline."""
        if step == SkillStep.PLAN:
            return await self._run_plan(story)
        elif step == SkillStep.IMPLEMENT:
            return await self._run_implement(story)
        elif step == SkillStep.REVIEW:
            return await self._run_review(story)
        elif step == SkillStep.UI:
            return await self._run_ui(story)
        elif step == SkillStep.VERIFY:
            return await self._run_verify(story)
        elif step == SkillStep.BROWSER:
            return await self._run_browser(story)
        return False

    async def _run_plan(self, story: UserStory) -> bool:
        """Run plan skill for architecture analysis."""
        prompt = self._build_story_prompt(story, "plan")
        meta = await self.runner.run(
            skill="plan",
            task=prompt,
            variants=1,
        )
        if meta.success_count > 0 and meta.results:
            output_file = meta.results[0].output_file
            if output_file:
                story.step_outputs["plan"] = str(output_file)
                return True
        return False

    async def _run_implement(self, story: UserStory) -> bool:
        """Run implement skill for code generation."""
        prompt = self._build_story_prompt(story, "implement")

        # Pass previous step output if available
        plan_file = story.step_outputs.get("plan") or story.step_outputs.get("ui")

        meta = await self.runner.run(
            skill="implement",
            task=prompt,
            variants=1,
            previous_output=plan_file,
        )
        if meta.success_count > 0 and meta.results:
            output_file = meta.results[0].output_file
            if output_file:
                story.step_outputs["implement"] = str(output_file)
                return True
        return False

    async def _run_review(self, story: UserStory) -> bool:
        """Run review skill for code quality analysis."""
        prompt = f"Review changes for story: {story.id} - {story.title}"
        meta = await self.runner.run(
            skill="review",
            task=prompt,
            variants=1,
        )
        if meta.success_count > 0 and meta.results:
            output_file = meta.results[0].output_file
            if output_file:
                story.step_outputs["review"] = str(output_file)
                # Check for blocking issues in review output
                content = output_file.read_text(encoding="utf-8")
                if "BLOCKING" in content.upper() or "CRITICAL" in content.upper():
                    story.last_error = "Review found blocking issues"
                    return False
                return True
        return False

    async def _run_ui(self, story: UserStory) -> bool:
        """Run UI skill for visual design."""
        prompt = self._build_story_prompt(story, "ui")
        meta = await self.runner.run(
            skill="ui",
            task=prompt,
            variants=1,
        )
        if meta.success_count > 0 and meta.results:
            output_file = meta.results[0].output_file
            if output_file:
                story.step_outputs["ui"] = str(output_file)
                return True
        return False

    async def _run_verify(self, story: UserStory) -> bool:
        """Run verification (pytest + ruff)."""
        # Run standard verification
        result = await self.verifier.verify(
            run_tests=True,
            run_lint=True,
        )

        # Run custom verification commands if specified
        if result.success and story.verification_commands:
            custom_result = await self.verifier.run_custom_commands(
                story.verification_commands
            )
            if not custom_result[0]:
                story.last_error = f"Custom verification failed: {custom_result[1][:200]}"
                return False

        if not result.success:
            story.last_error = result.error
            return False

        story.step_outputs["verify"] = (
            f"Tests: {result.test_output[:500]}\nLint: {result.lint_output[:500]}"
        )
        return True

    async def _run_browser(self, story: UserStory) -> bool:
        """Run browser verification (Playwright MCP).

        Note: This is a placeholder. Full implementation requires
        Playwright MCP integration.
        """
        # For now, just run standard verification
        # Browser verification will be implemented in browser.py
        self.memory.append_progress(
            self._current_iteration,
            story.id,
            "BROWSER",
            "Browser verification skipped (not implemented)",
        )
        return True

    def _build_story_prompt(self, story: UserStory, step: str) -> str:
        """Build prompt with memory context."""
        progress = self.memory.read_progress(last_n=20)
        agents = self.memory.read_agents_md()
        git_summary = self.memory.get_git_summary(count=5)

        ac_list = "\n".join(f"- {ac}" for ac in story.acceptance_criteria)

        return f"""# Story: {story.id}
## {story.title}

{story.description}

## Acceptance Criteria
{ac_list}

## Step: {step}

## Memory Context

### Recent Progress
{progress}

### Team Knowledge
{agents[:2000] if agents else "No prior knowledge recorded."}

### Git Summary
{git_summary}
"""

    def _save_state(self) -> None:
        """Save current PRD state to disk."""
        prd = self.memory.load_prd()
        if prd:
            self.memory.save_prd(prd)

    async def run_iteration(self, prd: PRD) -> tuple[bool, str]:
        """Run a single iteration of the automation loop.

        Returns (complete, status_message).
        """
        self._current_iteration += 1

        # Get next story to execute
        story = prd.next_story()
        if story is None:
            if prd.is_complete:
                return True, "<promise>COMPLETE</promise>"
            return False, "No eligible stories to execute"

        # Execute the story
        success = await self.execute_story(story)

        # Save updated state
        self.memory.save_prd(prd)

        if success:
            status = f"Story {story.id} completed successfully"
        else:
            status = f"Story {story.id} failed: {story.last_error}"

        return prd.is_complete, status

    async def run_loop(
        self,
        prd: PRD,
        max_iterations: int = 100,
    ) -> bool:
        """Run the automation loop until complete or max iterations.

        Returns True if PRD is fully complete.
        """
        self.memory.save_prd(prd)

        for i in range(max_iterations):
            self._current_iteration = i + 1

            complete, status = await self.run_iteration(prd)

            self.memory.append_progress(
                self._current_iteration,
                "LOOP",
                "STATUS",
                f"Iteration {i + 1}: {status}",
            )

            if complete:
                return True

            # Brief pause to avoid rate limiting
            await asyncio.sleep(2)

        return prd.is_complete
