"""Unit tests for skillpack.models module."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from skillpack.models import (
    ClaudeConfig,
    CodexConfig,
    EngineType,
    GeminiConfig,
    GitCheckpoint,
    OutputConfig,
    RunMeta,
    RunResult,
    SandboxMode,
    SkillpackConfig,
    WorkflowDef,
)


class TestSandboxMode:
    """Tests for SandboxMode enum."""

    def test_values(self):
        assert SandboxMode.READ_ONLY.value == "read-only"
        assert SandboxMode.WORKSPACE_WRITE.value == "workspace-write"
        assert SandboxMode.DANGER_FULL.value == "danger-full-access"

    def test_string_conversion(self):
        assert str(SandboxMode.READ_ONLY) == "SandboxMode.READ_ONLY"
        assert SandboxMode("read-only") == SandboxMode.READ_ONLY


class TestEngineType:
    """Tests for EngineType enum."""

    def test_all_engines(self):
        assert EngineType.CODEX.value == "codex"
        assert EngineType.GEMINI.value == "gemini"
        assert EngineType.CLAUDE.value == "claude"


class TestCodexConfig:
    """Tests for CodexConfig model."""

    def test_defaults(self):
        config = CodexConfig()
        assert config.sandbox == SandboxMode.WORKSPACE_WRITE
        assert config.full_auto is True
        assert config.model is None
        assert config.timeout_seconds == 600

    def test_custom_values(self, sample_codex_config: CodexConfig):
        assert sample_codex_config.sandbox == SandboxMode.WORKSPACE_WRITE
        assert sample_codex_config.model == "gpt-5.2"
        assert sample_codex_config.timeout_seconds == 300

    def test_from_dict(self):
        data = {
            "sandbox": "workspace-write",
            "full_auto": True,
            "model": "gpt-5.2",
            "timeout_seconds": 900,
        }
        config = CodexConfig(**data)
        assert config.sandbox == SandboxMode.WORKSPACE_WRITE
        assert config.full_auto is True


class TestGeminiConfig:
    """Tests for GeminiConfig model."""

    def test_defaults(self):
        config = GeminiConfig()
        assert config.headless is True
        assert config.model is None
        assert config.timeout_seconds == 300

    def test_custom_values(self, sample_gemini_config: GeminiConfig):
        assert sample_gemini_config.model == "gemini-3-pro"


class TestClaudeConfig:
    """Tests for ClaudeConfig model."""

    def test_defaults(self):
        config = ClaudeConfig()
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.timeout_seconds == 600
        # Default is True for faster automated execution (skip permission prompts)
        assert config.dangerously_skip_permissions is True
        assert config.extended_thinking is True

    def test_custom_values(self, sample_claude_config: ClaudeConfig):
        # Fixture explicitly sets False to test override capability
        assert sample_claude_config.dangerously_skip_permissions is False
        assert sample_claude_config.model == "claude-sonnet-4-5-20250929"


class TestOutputConfig:
    """Tests for OutputConfig model."""

    def test_required_fields(self):
        config = OutputConfig(dir="plans", pattern="plan_{i}.md")
        assert config.dir == "plans"
        assert config.pattern == "plan_{i}.md"

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            OutputConfig()  # type: ignore

    def test_pattern_formatting(self):
        config = OutputConfig(dir="output", pattern="result_{i}.json")
        assert config.pattern.format(i=3) == "result_3.json"


class TestWorkflowDef:
    """Tests for WorkflowDef model."""

    def test_minimal_workflow(self):
        wf = WorkflowDef(
            name="test",
            engine=EngineType.CODEX,
            prompt_template="test.md",
            output=OutputConfig(dir="out", pattern="out_{i}.md"),
        )
        assert wf.name == "test"
        assert wf.variants == 1  # default
        assert wf.codex is None

    def test_full_workflow(self, sample_workflow_def: WorkflowDef):
        assert sample_workflow_def.name == "test-plan"
        assert sample_workflow_def.variants == 3
        assert sample_workflow_def.codex is not None
        assert sample_workflow_def.codex.sandbox == SandboxMode.WORKSPACE_WRITE

    def test_variant_bounds(self):
        # Min bound
        wf = WorkflowDef(
            name="test",
            engine=EngineType.CODEX,
            variants=1,
            prompt_template="test.md",
            output=OutputConfig(dir="out", pattern="out_{i}.md"),
        )
        assert wf.variants == 1

        # Max bound
        wf = WorkflowDef(
            name="test",
            engine=EngineType.CODEX,
            variants=10,
            prompt_template="test.md",
            output=OutputConfig(dir="out", pattern="out_{i}.md"),
        )
        assert wf.variants == 10

        # Exceeds max
        with pytest.raises(ValidationError):
            WorkflowDef(
                name="test",
                engine=EngineType.CODEX,
                variants=11,
                prompt_template="test.md",
                output=OutputConfig(dir="out", pattern="out_{i}.md"),
            )

        # Below min
        with pytest.raises(ValidationError):
            WorkflowDef(
                name="test",
                engine=EngineType.CODEX,
                variants=0,
                prompt_template="test.md",
                output=OutputConfig(dir="out", pattern="out_{i}.md"),
            )

    def test_pipeline_fields(self):
        wf = WorkflowDef(
            name="implement",
            engine=EngineType.CODEX,
            prompt_template="implement.md",
            output=OutputConfig(dir="impl", pattern="summary.md"),
            depends_on="plan",
            pass_output_as="PLAN_TEXT",
        )
        assert wf.depends_on == "plan"
        assert wf.pass_output_as == "PLAN_TEXT"


class TestGitCheckpoint:
    """Tests for GitCheckpoint model."""

    def test_defaults(self):
        cp = GitCheckpoint()
        assert cp.enabled is True
        assert cp.before_branch is None
        assert cp.branch is None
        assert cp.dirty is False
        assert cp.stashed is False
        assert cp.reason is None

    def test_disabled_checkpoint(self):
        cp = GitCheckpoint(enabled=False, reason="not a git repo")
        assert cp.enabled is False
        assert cp.reason == "not a git repo"

    def test_full_checkpoint(self):
        cp = GitCheckpoint(
            enabled=True,
            before_branch="main",
            branch="skill/plan/123",
            dirty=True,
            stashed=True,
        )
        assert cp.before_branch == "main"
        assert cp.branch == "skill/plan/123"
        assert cp.dirty is True
        assert cp.stashed is True


class TestRunResult:
    """Tests for RunResult model."""

    def test_success_result(self, sample_run_result: RunResult):
        assert sample_run_result.variant == 1
        assert sample_run_result.success is True
        assert sample_run_result.duration_ms == 1500

    def test_failure_result(self):
        result = RunResult(
            variant=2,
            success=False,
            error="Process timed out",
            duration_ms=60000,
        )
        assert result.success is False
        assert result.error == "Process timed out"
        assert result.output_file is None

    def test_with_output(self):
        result = RunResult(
            variant=1,
            success=True,
            output_file=Path("/tmp/output.md"),
            stdout="Generated plan successfully",
            stderr="",
        )
        assert result.output_file == Path("/tmp/output.md")


class TestRunMeta:
    """Tests for RunMeta model."""

    def test_minimal_meta(self):
        meta = RunMeta(
            run_id="test_123",
            skill="plan",
            engine=EngineType.CODEX,
            variants=5,
            repo="/path/to/repo",
            started_at=datetime.now(),
            git=GitCheckpoint(enabled=False),
        )
        assert meta.run_id == "test_123"
        assert meta.completed_at is None
        assert meta.results == []
        assert meta.success_count == 0
        assert meta.failure_count == 0

    def test_completed_meta(self, sample_run_meta: RunMeta):
        assert sample_run_meta.skill == "plan"
        assert len(sample_run_meta.results) == 1
        assert sample_run_meta.success_count == 1

    def test_json_serialization(self, sample_run_meta: RunMeta):
        json_str = sample_run_meta.model_dump_json(exclude_none=True)
        assert "run_id" in json_str
        assert "20250130_120000" in json_str


class TestSkillpackConfig:
    """Tests for SkillpackConfig model."""

    def test_defaults(self):
        config = SkillpackConfig()
        assert config.default_engine == EngineType.CODEX
        assert config.auto_stash is True
        assert config.auto_branch is True
        assert config.parallel_variants == 5
        assert config.log_level == "info"
        assert config.output_format == "rich"

    def test_custom_config(self, sample_skillpack_config: SkillpackConfig):
        assert sample_skillpack_config.parallel_variants == 5

    def test_nested_engine_configs(self):
        config = SkillpackConfig(
            codex=CodexConfig(sandbox=SandboxMode.WORKSPACE_WRITE),
            gemini=GeminiConfig(headless=False),
        )
        assert config.codex.sandbox == SandboxMode.WORKSPACE_WRITE
        assert config.gemini.headless is False

    def test_parallel_variants_bounds(self):
        # Valid bounds
        config = SkillpackConfig(parallel_variants=1)
        assert config.parallel_variants == 1

        config = SkillpackConfig(parallel_variants=10)
        assert config.parallel_variants == 10

        # Invalid bounds
        with pytest.raises(ValidationError):
            SkillpackConfig(parallel_variants=0)

        with pytest.raises(ValidationError):
            SkillpackConfig(parallel_variants=11)

    def test_log_level_literal(self):
        for level in ["debug", "info", "warning", "error"]:
            config = SkillpackConfig(log_level=level)  # type: ignore
            assert config.log_level == level

        with pytest.raises(ValidationError):
            SkillpackConfig(log_level="invalid")  # type: ignore

    def test_output_format_literal(self):
        for fmt in ["rich", "json", "plain"]:
            config = SkillpackConfig(output_format=fmt)  # type: ignore
            assert config.output_format == fmt
