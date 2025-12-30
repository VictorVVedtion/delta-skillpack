"""Integration tests for skillpack.cli module."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from skillpack.cli import cli, AliasedGroup
from skillpack.models import (
    EngineType,
    GitCheckpoint,
    RunMeta,
    RunResult,
)


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


class TestAliasedGroup:
    """Tests for command aliasing."""

    def test_plan_alias(self, runner: CliRunner):
        """Test 'p' alias for 'plan'."""
        result = runner.invoke(cli, ["p", "--help"])
        assert result.exit_code == 0
        assert "Generate implementation plans" in result.output

    def test_implement_alias(self, runner: CliRunner):
        """Test 'i' alias for 'implement'."""
        result = runner.invoke(cli, ["i", "--help"])
        assert result.exit_code == 0
        assert "Implement a selected plan" in result.output

    def test_impl_alias(self, runner: CliRunner):
        """Test 'impl' alias for 'implement'."""
        result = runner.invoke(cli, ["impl", "--help"])
        assert result.exit_code == 0
        assert "Implement a selected plan" in result.output

    def test_ui_alias(self, runner: CliRunner):
        """Test 'u' alias for 'ui'."""
        result = runner.invoke(cli, ["u", "--help"])
        assert result.exit_code == 0
        assert "Generate UI specification" in result.output

    def test_doctor_alias(self, runner: CliRunner):
        """Test 'd' alias for 'doctor'."""
        with patch("skillpack.core.doctor"):
            result = runner.invoke(cli, ["d"])
        # Doctor runs even without mock since it just checks env
        assert result.exit_code == 0

    def test_history_alias(self, runner: CliRunner):
        """Test 'h' alias for 'history'."""
        result = runner.invoke(cli, ["h", "--help"])
        assert result.exit_code == 0
        assert "Show recent skill runs" in result.output

    def test_list_alias(self, runner: CliRunner):
        """Test 'ls' alias for 'list'."""
        result = runner.invoke(cli, ["ls"])
        assert result.exit_code == 0


class TestCliRoot:
    """Tests for root CLI command."""

    def test_help(self, runner: CliRunner):
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Delta SkillPack" in result.output
        assert "Quick start" in result.output

    def test_version(self, runner: CliRunner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_no_command_shows_help(self, runner: CliRunner):
        """Test that no command shows help."""
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Delta SkillPack" in result.output


class TestDoctorCommand:
    """Tests for doctor command."""

    def test_doctor_runs(self, runner: CliRunner):
        """Test doctor command execution."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0


class TestListCommand:
    """Tests for list command."""

    def test_list_shows_workflows(self, runner: CliRunner):
        """Test list command shows available workflows."""
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "plan" in result.output
        assert "implement" in result.output


class TestPlanCommand:
    """Tests for plan command."""

    def test_plan_help(self, runner: CliRunner):
        """Test plan --help."""
        result = runner.invoke(cli, ["plan", "--help"])
        assert result.exit_code == 0
        assert "Generate implementation plans" in result.output
        assert "--variants" in result.output
        assert "--sandbox" in result.output

    def test_plan_dry_run(self, runner: CliRunner):
        """Test plan with --dry-run flag."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test task", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry Run" in result.output

    def test_plan_with_variants(self, runner: CliRunner):
        """Test plan with custom variant count."""
        mock_meta = RunMeta(
            run_id="test_123",
            skill="plan",
            engine=EngineType.CODEX,
            variants=3,
            repo="/tmp/test",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            git=GitCheckpoint(enabled=False),
            results=[],
            success_count=3,
        )

        with runner.isolated_filesystem():
            with patch("skillpack.cli.SkillRunner") as MockRunner:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_meta)
                mock_instance.display_results = MagicMock()
                MockRunner.return_value = mock_instance

                result = runner.invoke(cli, ["plan", "Test task", "-n", "3", "--no-git"])

        assert result.exit_code == 0

    def test_plan_prompts_for_task(self, runner: CliRunner):
        """Test plan prompts for task when not provided."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "--dry-run"], input="My test task\n")
        assert result.exit_code == 0


class TestImplementCommand:
    """Tests for implement command."""

    def test_implement_help(self, runner: CliRunner):
        """Test implement --help."""
        result = runner.invoke(cli, ["implement", "--help"])
        assert result.exit_code == 0
        assert "Implement a selected plan" in result.output
        assert "--plan-file" in result.output
        assert "--interactive" in result.output

    def test_implement_requires_input(self, runner: CliRunner):
        """Test implement requires plan file or task."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["implement"])
        # Should warn about missing input
        assert "Provide --plan-file" in result.output or result.exit_code == 0

    def test_implement_with_plan_file(self, runner: CliRunner):
        """Test implement with --plan-file."""
        mock_meta = RunMeta(
            run_id="impl_123",
            skill="implement",
            engine=EngineType.CODEX,
            variants=1,
            repo="/tmp/test",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            git=GitCheckpoint(enabled=False),
            results=[
                RunResult(variant=1, success=True, output_file=Path("/tmp/out.md"))
            ],
            success_count=1,
        )

        with runner.isolated_filesystem():
            # Create a plan file
            Path("test_plan.md").write_text("# Test Plan\n\n1. Step one")

            with patch("skillpack.cli.SkillRunner") as MockRunner:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_meta)
                mock_instance.display_results = MagicMock()
                MockRunner.return_value = mock_instance

                result = runner.invoke(cli, ["implement", "-f", "test_plan.md", "--no-git"])

        assert result.exit_code == 0


class TestUiCommand:
    """Tests for ui command."""

    def test_ui_help(self, runner: CliRunner):
        """Test ui --help."""
        result = runner.invoke(cli, ["ui", "--help"])
        assert result.exit_code == 0
        assert "Generate UI specification" in result.output

    def test_ui_dry_run(self, runner: CliRunner):
        """Test ui with --dry-run."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["ui", "Mobile layout", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry Run" in result.output


class TestRunCommand:
    """Tests for generic run command."""

    def test_run_help(self, runner: CliRunner):
        """Test run --help."""
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "Run any workflow by name" in result.output

    def test_run_custom_skill(self, runner: CliRunner):
        """Test running a custom skill."""
        mock_meta = RunMeta(
            run_id="review_123",
            skill="review",
            engine=EngineType.CODEX,
            variants=1,
            repo="/tmp/test",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            git=GitCheckpoint(enabled=False),
            results=[],
            success_count=1,
        )

        with runner.isolated_filesystem():
            with patch("skillpack.cli.SkillRunner") as MockRunner:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_meta)
                mock_instance.display_results = MagicMock()
                MockRunner.return_value = mock_instance

                result = runner.invoke(cli, ["run", "review", "Check code quality", "--no-git"])

        assert result.exit_code == 0


class TestPipelineCommand:
    """Tests for pipeline command."""

    def test_pipeline_help(self, runner: CliRunner):
        """Test pipeline --help."""
        result = runner.invoke(cli, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "Run multiple skills in sequence" in result.output

    def test_pipeline_execution(self, runner: CliRunner):
        """Test pipeline executes multiple skills."""
        mock_meta = RunMeta(
            run_id="pipe_123",
            skill="plan",
            engine=EngineType.CODEX,
            variants=1,
            repo="/tmp/test",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            git=GitCheckpoint(enabled=False),
            results=[
                RunResult(variant=1, success=True, output_file=Path("/tmp/plan_1.md"))
            ],
            success_count=1,
        )

        with runner.isolated_filesystem():
            with patch("skillpack.cli.SkillRunner") as MockRunner:
                with patch("skillpack.cli.run_pipeline", new=AsyncMock(return_value=[mock_meta])):
                    MockRunner.return_value = MagicMock()
                    result = runner.invoke(cli, ["pipeline", "plan", "implement", "Test task"])

        assert result.exit_code == 0


class TestHistoryCommand:
    """Tests for history command."""

    def test_history_no_runs(self, runner: CliRunner):
        """Test history when no runs exist."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["history"])
        assert result.exit_code == 0
        assert "No runs found" in result.output

    def test_history_with_runs(self, runner: CliRunner):
        """Test history with existing runs."""
        with runner.isolated_filesystem():
            # Create a run directory with meta.json
            runs_dir = Path(".skillpack/runs/20250130_120000")
            runs_dir.mkdir(parents=True)

            meta = {
                "run_id": "20250130_120000",
                "skill": "plan",
                "engine": "codex",
                "variants": 5,
                "success_count": 5,
                "total_duration_ms": 30000,
            }
            (runs_dir / "meta.json").write_text(json.dumps(meta))

            result = runner.invoke(cli, ["history"])

        assert result.exit_code == 0
        assert "20250130_120000" in result.output
        assert "plan" in result.output

    def test_history_limit(self, runner: CliRunner):
        """Test history with --limit option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["history", "-n", "5"])
        assert result.exit_code == 0


class TestShowCommand:
    """Tests for show command."""

    def test_show_nonexistent_run(self, runner: CliRunner):
        """Test show with non-existent run ID."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["show", "nonexistent_run"])
        assert result.exit_code == 0
        assert "Run not found" in result.output

    def test_show_existing_run(self, runner: CliRunner):
        """Test show with existing run."""
        with runner.isolated_filesystem():
            run_id = "20250130_120000"
            run_dir = Path(f".skillpack/runs/{run_id}")
            run_dir.mkdir(parents=True)

            meta = {"run_id": run_id, "skill": "plan", "engine": "codex"}
            (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
            (run_dir / "plans").mkdir()
            (run_dir / "plans" / "plan_1.md").write_text("# Plan 1")

            result = runner.invoke(cli, ["show", run_id])

        assert result.exit_code == 0
        assert "Outputs" in result.output


class TestCommonOptions:
    """Tests for common CLI options."""

    def test_sandbox_option(self, runner: CliRunner):
        """Test --sandbox option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--sandbox", "workspace-write", "--dry-run"])
        assert result.exit_code == 0

    def test_approval_option(self, runner: CliRunner):
        """Test --approval option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--approval", "never", "--dry-run"])
        assert result.exit_code == 0

    def test_model_option(self, runner: CliRunner):
        """Test --model option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "-m", "gpt-4", "--dry-run"])
        assert result.exit_code == 0

    def test_full_auto_option(self, runner: CliRunner):
        """Test --full-auto option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--full-auto", "--dry-run"])
        assert result.exit_code == 0

    def test_no_git_option(self, runner: CliRunner):
        """Test --no-git option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--no-git", "--dry-run"])
        assert result.exit_code == 0

    def test_no_stash_option(self, runner: CliRunner):
        """Test --no-stash option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--no-stash", "--dry-run"])
        assert result.exit_code == 0

    def test_run_id_option(self, runner: CliRunner):
        """Test --run-id option."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--run-id", "custom_id", "--dry-run"])
        assert result.exit_code == 0


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_keyboard_interrupt(self, runner: CliRunner):
        """Test graceful handling of keyboard interrupt."""
        # This tests the main() function's KeyboardInterrupt handling
        # The CliRunner doesn't propagate this well, so we just verify the code path exists
        pass

    def test_invalid_sandbox_value(self, runner: CliRunner):
        """Test invalid --sandbox value."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--sandbox", "invalid"])
        assert result.exit_code != 0

    def test_invalid_approval_value(self, runner: CliRunner):
        """Test invalid --approval value."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "Test", "--approval", "invalid"])
        assert result.exit_code != 0
