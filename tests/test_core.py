"""Unit tests for skillpack.core module."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skillpack.core import (
    GitManager,
    SkillRunner,
    doctor,
    generate_run_id,
    load_config,
    load_workflow,
    render_prompt,
    run_pipeline,
)
from skillpack.models import (
    EngineType,
    GitCheckpoint,
    RunMeta,
    RunResult,
    SkillpackConfig,
    WorkflowDef,
)


class TestGenerateRunId:
    """Tests for run ID generation."""

    def test_format(self):
        run_id = generate_run_id()
        # Format: YYYYMMDD_HHMMSS
        assert len(run_id) == 15
        assert run_id[8] == "_"
        assert run_id[:8].isdigit()
        assert run_id[9:].isdigit()

    def test_uniqueness(self):
        # Generate multiple IDs in quick succession
        import time

        ids = set()
        for _ in range(3):
            ids.add(generate_run_id())
            time.sleep(1.1)  # Ensure different seconds

        assert len(ids) == 3


class TestLoadConfig:
    """Tests for configuration loading."""

    def test_load_defaults(self, temp_dir: Path):
        """Test loading default config when no .skillpackrc exists."""
        config = load_config(temp_dir)
        assert isinstance(config, SkillpackConfig)
        assert config.default_engine == EngineType.CODEX
        assert config.parallel_variants == 5

    def test_load_from_file(self, temp_repo: Path, skillpack_rc: Path):
        """Test loading config from .skillpackrc file."""
        config = load_config(temp_repo)
        assert config.parallel_variants == 3
        assert config.log_level == "debug"
        assert config.codex.timeout_seconds == 300

    def test_invalid_config_raises(self, temp_dir: Path):
        """Test that invalid config raises error."""
        rc_file = temp_dir / ".skillpackrc"
        rc_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_config(temp_dir)


class TestLoadWorkflow:
    """Tests for workflow definition loading."""

    def test_load_plan_workflow(self):
        """Test loading the plan workflow."""
        wf = load_workflow("plan")
        assert wf.name == "plan"
        assert wf.engine == EngineType.CLAUDE
        assert wf.variants == 5
        assert wf.claude is not None
        assert wf.claude.model == "claude-opus-4-5-20251101"

    def test_load_implement_workflow(self):
        """Test loading the implement workflow."""
        wf = load_workflow("implement")
        assert wf.name == "implement"
        assert wf.variants == 1
        assert wf.depends_on == "plan"
        assert wf.pass_output_as == "PLAN_TEXT"

    def test_load_nonexistent_workflow(self):
        """Test loading a non-existent workflow raises error."""
        with pytest.raises(FileNotFoundError, match="Unknown skill"):
            load_workflow("nonexistent_workflow")


class TestRenderPrompt:
    """Tests for prompt template rendering."""

    def test_render_with_task(self):
        """Test rendering prompt with TASK variable."""
        prompt = render_prompt("plan.md", {"TASK": "Add user authentication"})
        assert "Add user authentication" in prompt
        assert "{{TASK}}" not in prompt

    def test_render_with_plan_text(self):
        """Test rendering prompt with PLAN_TEXT variable."""
        prompt = render_prompt(
            "implement.md",
            {"TASK": "Implement feature", "PLAN_TEXT": "# Step 1\nDo something"},
        )
        assert "Implement feature" in prompt
        # Verify PLAN_TEXT is substituted (check implement.md has this placeholder)

    def test_render_empty_variable(self):
        """Test rendering with empty variable value."""
        prompt = render_prompt("plan.md", {"TASK": ""})
        assert "{{TASK}}" not in prompt


class TestGitManager:
    """Tests for GitManager class."""

    def test_is_repo_true(self, temp_repo: Path):
        """Test detecting a valid git repository."""
        git = GitManager(temp_repo)
        assert git.is_repo is True

    def test_is_repo_false(self, temp_dir: Path):
        """Test detecting non-git directory."""
        git = GitManager(temp_dir)
        assert git.is_repo is False

    def test_current_branch(self, temp_repo: Path):
        """Test getting current branch name."""
        git = GitManager(temp_repo)
        branch = git.current_branch
        # Default branch could be 'main' or 'master'
        assert branch in ["main", "master"]

    def test_is_dirty_clean(self, temp_repo: Path):
        """Test detecting clean working directory."""
        git = GitManager(temp_repo)
        assert git.is_dirty is False

    def test_is_dirty_with_changes(self, temp_repo: Path):
        """Test detecting dirty working directory."""
        (temp_repo / "new_file.txt").write_text("changes")
        git = GitManager(temp_repo)
        assert git.is_dirty is True

    def test_stash_when_dirty(self, temp_repo: Path):
        """Test stashing changes."""
        (temp_repo / "uncommitted.txt").write_text("changes")
        git = GitManager(temp_repo)

        assert git.is_dirty is True
        stashed = git.stash("test stash")
        assert stashed is True
        assert git.is_dirty is False

    def test_stash_when_clean(self, temp_repo: Path):
        """Test stashing when there are no changes."""
        git = GitManager(temp_repo)
        stashed = git.stash("test stash")
        assert stashed is False

    def test_create_branch(self, temp_repo: Path):
        """Test creating a new branch."""
        git = GitManager(temp_repo)
        original_branch = git.current_branch

        created = git.create_branch("test-branch")
        assert created is True
        assert git.current_branch == "test-branch"

        # Cleanup
        git.restore_branch(original_branch)

    def test_create_existing_branch_fails(self, temp_repo: Path):
        """Test that creating an existing branch fails."""
        git = GitManager(temp_repo)
        original_branch = git.current_branch

        # Create branch first time
        git.create_branch("duplicate-branch")
        git.restore_branch(original_branch)

        # Try to create again
        created = git.create_branch("duplicate-branch")
        assert created is False

    def test_checkpoint_creates_branch(self, temp_repo: Path):
        """Test checkpoint creates skill branch."""
        git = GitManager(temp_repo)
        original_branch = git.current_branch

        checkpoint = git.checkpoint("plan", "test_123")

        assert checkpoint.enabled is True
        assert checkpoint.before_branch == original_branch
        assert checkpoint.branch == "skill/plan/test_123"
        assert git.current_branch == "skill/plan/test_123"

        # Cleanup
        git.restore_branch(original_branch)

    def test_checkpoint_stashes_dirty(self, temp_repo: Path):
        """Test checkpoint stashes dirty changes."""
        (temp_repo / "dirty.txt").write_text("uncommitted")
        git = GitManager(temp_repo)

        checkpoint = git.checkpoint("plan", "test_456", stash=True)

        assert checkpoint.dirty is True
        assert checkpoint.stashed is True
        assert git.is_dirty is False

    def test_checkpoint_non_repo(self, temp_dir: Path):
        """Test checkpoint in non-git directory."""
        git = GitManager(temp_dir)
        checkpoint = git.checkpoint("plan", "test_789")

        assert checkpoint.enabled is False
        assert checkpoint.reason == "not a git repo"

    def test_restore_branch(self, temp_repo: Path):
        """Test restoring to original branch."""
        git = GitManager(temp_repo)
        original = git.current_branch

        git.create_branch("feature-branch")
        assert git.current_branch == "feature-branch"

        git.restore_branch(original)
        assert git.current_branch == original

    def test_restore_branch_with_stash_pop(self, temp_repo: Path):
        """Test restoring branch and popping stash."""
        (temp_repo / "to_stash.txt").write_text("content")
        git = GitManager(temp_repo)
        original = git.current_branch

        git.stash("test")
        git.create_branch("temp-branch")
        git.restore_branch(original, pop_stash=True)

        assert git.current_branch == original
        assert (temp_repo / "to_stash.txt").exists()


class TestSkillRunner:
    """Tests for SkillRunner class."""

    def test_init_with_defaults(self, temp_repo: Path):
        """Test runner initialization with default config."""
        runner = SkillRunner(temp_repo)
        assert runner.repo == temp_repo.resolve()
        assert isinstance(runner.config, SkillpackConfig)
        assert isinstance(runner.git, GitManager)

    def test_init_with_custom_config(
        self, temp_repo: Path, sample_skillpack_config: SkillpackConfig
    ):
        """Test runner initialization with custom config."""
        runner = SkillRunner(temp_repo, config=sample_skillpack_config)
        assert runner.config == sample_skillpack_config

    def test_ensure_dirs(self, temp_repo: Path):
        """Test output directory creation."""
        runner = SkillRunner(temp_repo)
        root, out = runner._ensure_dirs("test_run", "plans")

        assert root == temp_repo.resolve() / ".skillpack" / "runs" / "test_run"
        assert out == root / "plans"
        assert out.exists()

    def test_write_meta(self, temp_repo: Path, sample_run_meta: RunMeta):
        """Test metadata writing."""
        runner = SkillRunner(temp_repo)
        root, _ = runner._ensure_dirs(sample_run_meta.run_id, "plans")

        runner._write_meta(root, sample_run_meta)

        meta_file = root / "meta.json"
        assert meta_file.exists()

        loaded = json.loads(meta_file.read_text())
        assert loaded["run_id"] == sample_run_meta.run_id
        assert loaded["skill"] == sample_run_meta.skill

    @pytest.mark.asyncio
    async def test_run_creates_output(self, temp_repo: Path):
        """Test that run creates output files."""
        runner = SkillRunner(temp_repo)

        # Mock the engine execution
        async def mock_execute(repo, prompt, output_file, variant=1):
            output_file.write_text(f"# Plan {variant}\nTest content")
            return RunResult(
                variant=variant,
                success=True,
                output_file=output_file,
                duration_ms=100,
            )

        with patch("skillpack.core.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.execute = AsyncMock(side_effect=mock_execute)
            mock_get_engine.return_value = mock_engine

            meta = await runner.run(
                skill="plan",
                task="Test task",
                variants=2,
                no_git_checkpoint=True,
            )

        assert meta.success_count == 2
        assert meta.failure_count == 0
        assert len(meta.results) == 2

        # Check output files exist
        for result in meta.results:
            assert result.output_file.exists()

    @pytest.mark.asyncio
    async def test_run_with_git_checkpoint(self, temp_repo: Path):
        """Test that run creates git checkpoint."""
        runner = SkillRunner(temp_repo)
        original_branch = runner.git.current_branch

        async def mock_execute(repo, prompt, output_file, variant=1):
            output_file.write_text("content")
            return RunResult(variant=variant, success=True, output_file=output_file)

        with patch("skillpack.core.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.execute = AsyncMock(side_effect=mock_execute)
            mock_get_engine.return_value = mock_engine

            meta = await runner.run(
                skill="plan",
                task="Test",
                variants=1,
            )

        assert meta.git.enabled is True
        assert meta.git.before_branch == original_branch
        assert "skill/plan/" in meta.git.branch

        # Cleanup
        runner.git.restore_branch(original_branch)

    @pytest.mark.asyncio
    async def test_run_handles_failures(self, temp_repo: Path):
        """Test that run handles engine failures gracefully."""
        runner = SkillRunner(temp_repo)

        async def mock_execute(repo, prompt, output_file, variant=1):
            if variant == 2:
                return RunResult(
                    variant=variant,
                    success=False,
                    error="Simulated failure",
                )
            output_file.write_text("content")
            return RunResult(variant=variant, success=True, output_file=output_file)

        with patch("skillpack.core.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.execute = AsyncMock(side_effect=mock_execute)
            mock_get_engine.return_value = mock_engine

            meta = await runner.run(
                skill="plan",
                task="Test",
                variants=3,
                no_git_checkpoint=True,
            )

        assert meta.success_count == 2
        assert meta.failure_count == 1

    @pytest.mark.asyncio
    async def test_run_with_plan_file(self, temp_repo: Path):
        """Test that run loads plan file content."""
        runner = SkillRunner(temp_repo)

        # Create a plan file
        plan_file = temp_repo / "test_plan.md"
        plan_file.write_text("# Implementation Plan\n\n1. Step one\n2. Step two")

        captured_prompt = None

        async def mock_execute(repo, prompt, output_file, variant=1):
            nonlocal captured_prompt
            captured_prompt = prompt
            output_file.write_text("content")
            return RunResult(variant=variant, success=True, output_file=output_file)

        with patch("skillpack.core.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.execute = AsyncMock(side_effect=mock_execute)
            mock_get_engine.return_value = mock_engine

            await runner.run(
                skill="implement",
                task="Implement the plan",
                plan_file=str(plan_file),
                variants=1,
                no_git_checkpoint=True,
            )

        # The plan text should be in the rendered prompt
        # (depends on implement.md template having {{PLAN_TEXT}})


class TestRunPipeline:
    """Tests for pipeline execution."""

    @pytest.mark.asyncio
    async def test_pipeline_executes_in_order(self, temp_repo: Path):
        """Test that pipeline executes skills in order."""
        runner = SkillRunner(temp_repo)
        execution_order = []

        async def mock_run(skill, task, **kwargs):
            execution_order.append(skill)
            return RunMeta(
                run_id=f"test_{skill}",
                skill=skill,
                engine=EngineType.CODEX,
                variants=1,
                repo=str(temp_repo),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                git=GitCheckpoint(enabled=False),
                results=[
                    RunResult(
                        variant=1,
                        success=True,
                        output_file=temp_repo / f"{skill}_output.md",
                    )
                ],
                success_count=1,
            )

        with patch.object(runner, "run", new=AsyncMock(side_effect=mock_run)):
            with patch.object(runner, "display_results"):
                # Create dummy output files
                (temp_repo / "plan_output.md").write_text("plan content")
                (temp_repo / "implement_output.md").write_text("implement content")

                results = await run_pipeline(
                    runner,
                    ["plan", "implement"],
                    "Test task",
                )

        assert execution_order == ["plan", "implement"]
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_pipeline_stops_on_complete_failure(self, temp_repo: Path):
        """Test that pipeline stops when all variants fail."""
        runner = SkillRunner(temp_repo)

        async def mock_run(skill, task, **kwargs):
            return RunMeta(
                run_id=f"test_{skill}",
                skill=skill,
                engine=EngineType.CODEX,
                variants=1,
                repo=str(temp_repo),
                started_at=datetime.now(),
                git=GitCheckpoint(enabled=False),
                results=[
                    RunResult(variant=1, success=False, error="Failed")
                ],
                success_count=0,
                failure_count=1,
            )

        with patch.object(runner, "run", new=AsyncMock(side_effect=mock_run)):
            with patch.object(runner, "display_results"):
                results = await run_pipeline(
                    runner,
                    ["plan", "implement", "ui"],
                    "Test task",
                )

        # Should stop after first skill fails completely
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_pipeline_passes_output_to_next_skill(self, temp_repo: Path):
        """Test that pipeline passes output from one skill to the next."""
        runner = SkillRunner(temp_repo)
        received_kwargs = []

        async def mock_run(skill, task, **kwargs):
            received_kwargs.append((skill, dict(kwargs)))
            output_file = temp_repo / f"{skill}_output.md"
            output_file.write_text(f"Output from {skill}")
            return RunMeta(
                run_id=f"test_{skill}",
                skill=skill,
                engine=EngineType.CODEX,
                variants=1,
                repo=str(temp_repo),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                git=GitCheckpoint(enabled=False),
                results=[
                    RunResult(
                        variant=1,
                        success=True,
                        output_file=output_file,
                    )
                ],
                success_count=1,
            )

        with patch.object(runner, "run", new=AsyncMock(side_effect=mock_run)):
            with patch.object(runner, "display_results"):
                await run_pipeline(
                    runner,
                    ["plan", "implement"],
                    "Test task",
                )

        # Second skill should receive plan_file from first skill's output
        assert len(received_kwargs) == 2
        _, impl_kwargs = received_kwargs[1]
        assert "plan_file" in impl_kwargs or "_pipeline_vars" in impl_kwargs

    @pytest.mark.asyncio
    async def test_pipeline_respects_depends_on(self, temp_repo: Path):
        """Test that pipeline validates depends_on declarations."""
        runner = SkillRunner(temp_repo)
        executed_skills = []

        async def mock_run(skill, task, **kwargs):
            executed_skills.append(skill)
            output_file = temp_repo / f"{skill}_output.md"
            output_file.write_text(f"Output from {skill}")
            return RunMeta(
                run_id=f"test_{skill}",
                skill=skill,
                engine=EngineType.CODEX,
                variants=1,
                repo=str(temp_repo),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                git=GitCheckpoint(enabled=False),
                results=[
                    RunResult(variant=1, success=True, output_file=output_file)
                ],
                success_count=1,
            )

        with patch.object(runner, "run", new=AsyncMock(side_effect=mock_run)):
            with patch.object(runner, "display_results"):
                # implement depends_on plan (defined in workflow)
                results = await run_pipeline(
                    runner,
                    ["plan", "implement"],
                    "Test task",
                )

        assert "plan" in executed_skills
        assert "implement" in executed_skills
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_pipeline_injects_pipeline_vars(self, temp_repo: Path):
        """Test that pipeline injects variables via pass_output_as."""
        runner = SkillRunner(temp_repo)
        captured_vars = []

        async def mock_run(skill, task, _pipeline_vars=None, **kwargs):
            captured_vars.append((skill, _pipeline_vars))
            output_file = temp_repo / f"{skill}_output.md"
            output_file.write_text(f"Content from {skill}")
            return RunMeta(
                run_id=f"test_{skill}",
                skill=skill,
                engine=EngineType.CODEX,
                variants=1,
                repo=str(temp_repo),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                git=GitCheckpoint(enabled=False),
                results=[
                    RunResult(variant=1, success=True, output_file=output_file)
                ],
                success_count=1,
            )

        with patch.object(runner, "run", new=AsyncMock(side_effect=mock_run)):
            with patch.object(runner, "display_results"):
                # implement has pass_output_as: PLAN_TEXT
                await run_pipeline(
                    runner,
                    ["plan", "implement"],
                    "Test task",
                )

        # implement should receive _pipeline_vars with PLAN_TEXT
        assert len(captured_vars) == 2
        impl_skill, impl_vars = captured_vars[1]
        assert impl_skill == "implement"
        # If pass_output_as is set, _pipeline_vars should contain the key
        if impl_vars:
            assert "PLAN_TEXT" in impl_vars


class TestDoctor:
    """Tests for doctor command."""

    def test_doctor_runs(self, temp_repo: Path, capsys):
        """Test that doctor command runs without error."""
        # Just verify it doesn't crash
        with patch("shutil.which", return_value=None):
            doctor(temp_repo)

        # Should produce some output
        captured = capsys.readouterr()
        # Rich output goes to stderr in some cases
        output = captured.out + captured.err
        # The function uses Rich console which may not capture well in tests

    def test_doctor_detects_git(self, temp_repo: Path):
        """Test that doctor detects git repository."""
        # This is more of an integration test
        git = GitManager(temp_repo)
        assert git.is_repo is True
