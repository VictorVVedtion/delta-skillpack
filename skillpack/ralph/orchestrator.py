"""Story orchestrator for Ralph automation.

Routes stories to appropriate skill pipelines based on story type.
Now with ClaudeEngine integration for plan and review steps.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..core import SkillRunner
from ..engines import ClaudeEngine
from ..models import (
    PRD,
    ClaudeConfig,
    QueryContext,
    RalphConfig,
    SkillStep,
    StepRetryConfig,
    UserStory,
)
from .browser import PlaywrightMCPBridge
from .dev_server import DevServerManager
from .memory import MemoryManager
from .notebooklm import NotebookLMBridge
from .verify import QualityVerifier

if TYPE_CHECKING:
    pass


class StoryOrchestrator:
    """Story execution orchestrator - dispatches skill pipelines.

    Now supports direct ClaudeEngine execution for plan and review steps.
    """

    def __init__(self, repo: Path, ralph_config: RalphConfig | None = None):
        self.repo = Path(repo)
        self.memory = MemoryManager(repo)
        self.runner = SkillRunner(repo)
        self.verifier = QualityVerifier(repo)
        self._current_iteration = 0

        # Ralph configuration
        self.config = ralph_config or RalphConfig()

        # Initialize ClaudeEngine for direct execution
        if self.config.use_claude_for_plan or self.config.use_claude_for_review:
            claude_config = ClaudeConfig(
                model=self.config.claude_model,
                extended_thinking=self.config.claude_extended_thinking,
                timeout_seconds=self.config.claude_timeout_seconds,
            )
            self.claude_engine = ClaudeEngine(claude_config)
        else:
            self.claude_engine = None

        # Initialize NotebookLM knowledge engine
        if self.config.use_notebooklm and self.config.notebooklm.enabled:
            self.knowledge_engine: NotebookLMBridge | None = NotebookLMBridge(
                repo,
                self.memory,
                self.config.notebooklm,
            )
        else:
            self.knowledge_engine = None

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

            success, error, error_action = await self._execute_step_with_retry(
                story, step, self.config.step_retry
            )
            if not success:
                story.last_error = error or f"Step {step.value} failed"
                action = f"{error_action}:{step.value}" if error_action else f"FAIL:{step.value}"
                self.memory.append_progress(
                    self._current_iteration,
                    story.id,
                    action,
                    story.last_error or "Unknown error",
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

    def _is_retryable_error(self, error: str | None, config: StepRetryConfig) -> bool:
        """Check if an error message should trigger retry."""
        if not error:
            return False
        lowered = error.lower()
        return any(token in lowered for token in config.retryable_errors)

    async def _execute_step_with_retry(
        self,
        story: UserStory,
        step: SkillStep,
        config: StepRetryConfig,
    ) -> tuple[bool, str | None, str]:
        """Execute a step with retries based on error classification."""
        last_error: str | None = None
        last_error_action = "FAIL"

        for attempt in range(1, config.max_attempts + 1):
            try:
                success = await self._execute_step(story, step)
                if success:
                    story.last_error = None
                    return True, None, ""
                last_error = story.last_error or f"Step {step.value} failed"
                last_error_action = "FAIL"
            except Exception as exc:
                last_error = str(exc)
                last_error_action = "ERROR"

            story.last_error = last_error

            if attempt >= config.max_attempts:
                return False, last_error, last_error_action

            if not self._is_retryable_error(last_error, config):
                return False, last_error, last_error_action

            backoff = config.backoff_seconds
            if config.exponential_backoff:
                backoff *= 2 ** (attempt - 1)

            self.memory.append_progress(
                self._current_iteration,
                story.id,
                f"RETRY:{step.value}",
                f"Attempt {attempt}/{config.max_attempts} failed: "
                f"{(last_error or 'Unknown error')[:200]}. Retrying in {backoff:.1f}s",
            )
            await asyncio.sleep(backoff)

        return False, last_error, last_error_action

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
        """Run plan skill for architecture analysis.

        Uses ClaudeEngine directly if configured, otherwise falls back to SkillRunner.
        Optionally queries NotebookLM for architectural knowledge before planning.
        """
        # Query knowledge before planning if enabled
        if self.knowledge_engine and self.config.knowledge_query_before_plan:
            context = QueryContext(
                story_id=story.id,
                story_type=story.type,
                current_step=SkillStep.PLAN,
            )
            try:
                knowledge = await self.knowledge_engine.batch_query(
                    [
                        f"What is the recommended architecture for: {story.title}",
                        f"Are there existing patterns for: {story.description[:200]}",
                    ],
                    context,
                )
                if knowledge:
                    formatted = self.knowledge_engine.format_context(knowledge)
                    if formatted:
                        story.step_outputs["knowledge_context"] = formatted
                        self.memory.append_progress(
                            self._current_iteration,
                            story.id,
                            "KNOWLEDGE:PLAN",
                            f"Retrieved {len(knowledge)} knowledge items for planning",
                        )
            except Exception as e:
                # Graceful degradation - log but continue without knowledge
                self.memory.append_progress(
                    self._current_iteration,
                    story.id,
                    "KNOWLEDGE:WARN",
                    f"Failed to fetch knowledge for plan: {e!s}",
                )

        prompt = self._build_story_prompt(story, "plan")

        # Use Claude directly if configured and available
        if self.config.use_claude_for_plan and self.claude_engine:
            if self.claude_engine.available:
                self.memory.append_progress(
                    self._current_iteration,
                    story.id,
                    "PLAN:CLAUDE",
                    f"Using Claude Opus 4.5 for planning ({self.config.claude_model})",
                )
                output_dir = (
                    self.repo
                    / ".skillpack"
                    / "ralph"
                    / "iterations"
                    / f"{self._current_iteration:03d}"
                )
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"plan_{story.id}.md"

                result = await self.claude_engine.execute(
                    repo=self.repo,
                    prompt=prompt,
                    output_file=output_file,
                    variant=1,
                )

                if result.success and result.output_file:
                    story.step_outputs["plan"] = str(result.output_file)
                    return True
                else:
                    story.last_error = result.error or "Claude plan execution failed"
                    return False
            else:
                self.memory.append_progress(
                    self._current_iteration,
                    story.id,
                    "PLAN:FALLBACK",
                    "Claude not available, using SkillRunner",
                )

        # Fallback to SkillRunner
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
        if meta.results:
            story.last_error = meta.results[0].error or "Plan execution failed"
        else:
            story.last_error = "Plan execution failed"
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
            plan_file=plan_file,  # Pass previous step output as plan context
        )
        if meta.success_count > 0 and meta.results:
            output_file = meta.results[0].output_file
            if output_file:
                story.step_outputs["implement"] = str(output_file)
                return True
        if meta.results:
            story.last_error = meta.results[0].error or "Implement execution failed"
        else:
            story.last_error = "Implement execution failed"
        return False

    async def _run_review(self, story: UserStory) -> bool:
        """Run review skill for code quality analysis.

        Uses ClaudeEngine directly if configured, otherwise falls back to SkillRunner.
        Optionally queries NotebookLM for coding standards before reviewing.
        """
        # Query knowledge for review standards if enabled
        if self.knowledge_engine and self.config.knowledge_query_before_review:
            context = QueryContext(
                story_id=story.id,
                story_type=story.type,
                current_step=SkillStep.REVIEW,
            )
            try:
                knowledge = await self.knowledge_engine.batch_query(
                    [
                        "What are the coding standards for this project?",
                        "What security guidelines should be followed?",
                    ],
                    context,
                )
                if knowledge:
                    formatted = self.knowledge_engine.format_context(knowledge)
                    if formatted:
                        story.step_outputs["review_standards"] = formatted
                        self.memory.append_progress(
                            self._current_iteration,
                            story.id,
                            "KNOWLEDGE:REVIEW",
                            f"Retrieved {len(knowledge)} knowledge items for review",
                        )
            except Exception:
                # Graceful degradation - continue without knowledge
                pass

        prompt = self._build_review_prompt(story)

        # Use Claude directly if configured and available
        if self.config.use_claude_for_review and self.claude_engine:
            if self.claude_engine.available:
                self.memory.append_progress(
                    self._current_iteration,
                    story.id,
                    "REVIEW:CLAUDE",
                    f"Using Claude Opus 4.5 for review ({self.config.claude_model})",
                )
                output_dir = (
                    self.repo
                    / ".skillpack"
                    / "ralph"
                    / "iterations"
                    / f"{self._current_iteration:03d}"
                )
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"review_{story.id}.md"

                result = await self.claude_engine.execute(
                    repo=self.repo,
                    prompt=prompt,
                    output_file=output_file,
                    variant=1,
                )

                if result.success and result.output_file:
                    story.step_outputs["review"] = str(result.output_file)
                    # Check for blocking issues in review output
                    content = result.output_file.read_text(encoding="utf-8")
                    if "BLOCKING" in content.upper() or "CRITICAL" in content.upper():
                        story.last_error = "Review found blocking issues"
                        return False
                    return True
                else:
                    story.last_error = result.error or "Claude review execution failed"
                    return False
            else:
                self.memory.append_progress(
                    self._current_iteration,
                    story.id,
                    "REVIEW:FALLBACK",
                    "Claude not available, using SkillRunner",
                )

        # Fallback to SkillRunner
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
        if meta.results:
            story.last_error = meta.results[0].error or "Review execution failed"
        else:
            story.last_error = "Review execution failed"
        return False

    def _build_review_prompt(self, story: UserStory) -> str:
        """Build review prompt with context."""
        progress = self.memory.read_progress(last_n=10)
        git_diff = self.memory.get_git_diff()

        return f"""# Code Review Request

## Story: {story.id} - {story.title}

{story.description}

## Acceptance Criteria
{chr(10).join(f"- {ac}" for ac in story.acceptance_criteria)}

## Recent Changes (git diff)
```
{git_diff[:5000] if git_diff else "No changes detected"}
```

## Review Checklist
- [ ] Code correctness and logic
- [ ] Error handling
- [ ] Security vulnerabilities
- [ ] Performance implications
- [ ] Code style and readability
- [ ] Test coverage
- [ ] Documentation

## Recent Progress
{progress}

Please provide a thorough code review. Mark any blocking issues with "BLOCKING:" prefix.
"""

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
        if meta.results:
            story.last_error = meta.results[0].error or "UI execution failed"
        else:
            story.last_error = "UI execution failed"
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
            custom_result = await self.verifier.run_custom_commands(story.verification_commands)
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
        """Run browser verification (Playwright MCP)."""
        dev_url = "http://localhost:3000"
        server_manager = DevServerManager(self.repo, port=3000)

        started = await server_manager.start()
        if not started:
            story.last_error = f"Dev server failed to start for {dev_url}"
            return False

        bridge = PlaywrightMCPBridge(self.repo, self.memory, self.config)
        try:
            success, message = await bridge.verify_ui_story(story, dev_url=dev_url)
        finally:
            await server_manager.stop()

        if success:
            result_file = self.memory.ralph_dir / "browser_verify_result.json"
            if result_file.exists():
                story.step_outputs["browser"] = str(result_file)
            else:
                story.step_outputs["browser"] = message
            return True

        story.last_error = message
        return False

    def _build_story_prompt(self, story: UserStory, step: str) -> str:
        """Build prompt with memory context."""
        progress = self.memory.read_progress(last_n=20)
        agents = self.memory.read_agents_md()
        git_summary = self.memory.get_git_summary(count=5)

        ac_list = "\n".join(f"- {ac}" for ac in story.acceptance_criteria)

        # Get knowledge context if available
        knowledge_context = story.step_outputs.get("knowledge_context", "")
        review_standards = story.step_outputs.get("review_standards", "")

        prompt = f"""# Story: {story.id}
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

        # Append knowledge context if available
        if knowledge_context:
            prompt += f"\n{knowledge_context}\n"

        if review_standards:
            prompt += f"\n{review_standards}\n"

        return prompt

    def _save_state(self) -> None:
        """Save current PRD state to disk."""
        prd = self.memory.load_prd()
        if prd:
            self.memory.save_prd(prd)

    def _mark_complete(self) -> None:
        """Write completion marker for stop hook detection."""
        marker_file = self.repo / ".skillpack" / "ralph" / ".complete"
        try:
            marker_file.write_text(datetime.now().isoformat(), encoding="utf-8")
            self.memory.append_progress(
                self._current_iteration,
                "LOOP",
                "COMPLETE:MARKER",
                "Wrote completion marker file",
            )
        except Exception as exc:
            self.memory.append_progress(
                self._current_iteration,
                "LOOP",
                "COMPLETE:MARKER_ERROR",
                str(exc)[:200],
            )

    def calculate_dynamic_iterations(self, prd: PRD) -> int:
        """Calculate dynamic max iterations based on PRD complexity.

        Formula: base + (stories × 15) + complexity_bonus
        Range: 30-500
        """
        base = 30
        story_factor = len(prd.stories) * 15

        # Complexity bonus based on story types
        complexity_bonus = 0
        for story in prd.stories:
            if story.type.value in ("feature", "refactor"):
                complexity_bonus += 10
            elif story.type.value == "ui":
                complexity_bonus += 15  # UI stories often need more iterations

        total = base + story_factor + complexity_bonus
        return max(30, min(500, total))  # Clamp to 30-500

    def get_parallel_stories(self, prd: PRD, max_parallel: int = 3) -> list[UserStory]:
        """Get stories that can be executed in parallel (no dependencies)."""
        pending = [s for s in prd.stories if not s.passes and s.attempts < s.max_attempts]

        parallel: list[UserStory] = []
        for story in sorted(pending, key=lambda s: (s.priority, s.attempts)):
            # Check dependencies
            deps_ok = all(
                any(d.id == dep and d.passes for d in prd.stories) for dep in story.depends_on
            )
            if not deps_ok:
                continue

            # Check if any parallel story would conflict
            conflict = False
            for ps in parallel:
                # Same dependency would conflict
                if set(story.depends_on) & set(ps.depends_on):
                    conflict = True
                    break
                # If one depends on the other
                if story.id in ps.depends_on or ps.id in story.depends_on:
                    conflict = True
                    break

            if not conflict:
                parallel.append(story)
                if len(parallel) >= max_parallel:
                    break

        return parallel

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

    async def run_parallel_iteration(self, prd: PRD, max_parallel: int = 3) -> tuple[bool, str]:
        """Run multiple independent stories in parallel.

        Returns (complete, status_message).
        """
        self._current_iteration += 1

        # Get stories that can run in parallel
        stories = self.get_parallel_stories(prd, max_parallel)
        if not stories:
            if prd.is_complete:
                return True, "<promise>COMPLETE</promise>"
            # Fall back to sequential if no parallel candidates
            return await self.run_iteration(prd)

        self.memory.append_progress(
            self._current_iteration,
            "LOOP",
            "PARALLEL",
            f"Executing {len(stories)} stories in parallel: {[s.id for s in stories]}",
        )

        # Execute stories in parallel with semaphore
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_with_semaphore(story: UserStory) -> bool:
            async with semaphore:
                return await self.execute_story(story)

        results = await asyncio.gather(
            *[execute_with_semaphore(s) for s in stories],
            return_exceptions=True,
        )

        # Process results
        successes = sum(1 for r in results if r is True)
        failures = len(results) - successes

        # Save updated state
        self.memory.save_prd(prd)

        status = f"Parallel: {successes} succeeded, {failures} failed"
        return prd.is_complete, status

    async def run_loop(
        self,
        prd: PRD,
        max_iterations: int | None = None,
        parallel: bool = False,
        max_parallel: int = 3,
    ) -> bool:
        """Run the automation loop until complete or max iterations.

        Args:
            prd: Product Requirements Document to execute
            max_iterations: Override max iterations (None = dynamic calculation)
            parallel: Enable parallel story execution
            max_parallel: Maximum concurrent stories when parallel=True

        Returns True if PRD is fully complete.
        """
        self.memory.save_prd(prd)

        # Use dynamic iteration limit if not specified
        if max_iterations is None:
            max_iterations = self.calculate_dynamic_iterations(prd)

        self.memory.append_progress(
            0,
            "LOOP",
            "CONFIG",
            f"Max iterations: {max_iterations}, Parallel: {parallel}, Max parallel: {max_parallel}",
        )

        for i in range(max_iterations):
            self._current_iteration = i + 1

            if parallel:
                complete, status = await self.run_parallel_iteration(prd, max_parallel)
            else:
                complete, status = await self.run_iteration(prd)

            self.memory.append_progress(
                self._current_iteration,
                "LOOP",
                "STATUS",
                f"Iteration {i + 1}: {status}",
            )

            if complete:
                self._mark_complete()
                return True

            # Brief pause to avoid rate limiting
            await asyncio.sleep(self.config.iteration_delay_seconds)

        if prd.is_complete:
            self._mark_complete()
        return prd.is_complete
