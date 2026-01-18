"""Pytest fixtures and configuration for SkillPack tests."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

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


@pytest.fixture
def temp_repo() -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo,
            capture_output=True,
        )
        # Create initial commit
        (repo / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            capture_output=True,
        )
        yield repo


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory (non-git)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_codex_config() -> CodexConfig:
    """Sample Codex configuration."""
    return CodexConfig(
        sandbox=SandboxMode.WORKSPACE_WRITE,
        full_auto=True,
        model="gpt-5.2",
        timeout_seconds=300,
    )


@pytest.fixture
def sample_gemini_config() -> GeminiConfig:
    """Sample Gemini configuration."""
    return GeminiConfig(
        headless=True,
        model="gemini-3-pro",
        timeout_seconds=300,
    )


@pytest.fixture
def sample_claude_config() -> ClaudeConfig:
    """Sample Claude configuration."""
    return ClaudeConfig(
        model="claude-sonnet-4-5-20250929",
        timeout_seconds=600,
        dangerously_skip_permissions=False,
    )


@pytest.fixture
def sample_workflow_def() -> WorkflowDef:
    """Sample workflow definition."""
    return WorkflowDef(
        name="test-plan",
        engine=EngineType.CODEX,
        variants=3,
        prompt_template="plan.md",
        output=OutputConfig(dir="plans", pattern="plan_{i}.md"),
        codex=CodexConfig(
            sandbox=SandboxMode.WORKSPACE_WRITE,
            full_auto=True,
        ),
    )


@pytest.fixture
def sample_run_result() -> RunResult:
    """Sample run result."""
    return RunResult(
        variant=1,
        success=True,
        output_file=Path("/tmp/test_output.md"),
        duration_ms=1500,
        stdout="Success output",
    )


@pytest.fixture
def sample_run_meta(sample_run_result: RunResult) -> RunMeta:
    """Sample run metadata."""
    from datetime import datetime

    return RunMeta(
        run_id="20250130_120000",
        skill="plan",
        engine=EngineType.CODEX,
        variants=3,
        repo="/tmp/test-repo",
        started_at=datetime.now(),
        git=GitCheckpoint(enabled=True, branch="skill/plan/20250130_120000"),
        results=[sample_run_result],
        success_count=1,
    )


@pytest.fixture
def sample_skillpack_config() -> SkillpackConfig:
    """Sample skillpack configuration."""
    return SkillpackConfig(
        default_engine=EngineType.CODEX,
        auto_stash=True,
        auto_branch=True,
        parallel_variants=5,
        log_level="info",
        output_format="rich",
    )


@pytest.fixture
def mock_codex_binary():
    """Mock codex binary availability."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/codex"
        yield mock_which


@pytest.fixture
def mock_process_success():
    """Mock successful subprocess execution."""

    async def mock_run(*args, **kwargs):
        return (0, "Success output", "")

    with patch(
        "skillpack.engines.BaseEngine._run_process",
        new_callable=lambda: AsyncMock(side_effect=mock_run),
    ) as mock:
        yield mock


@pytest.fixture
def mock_process_failure():
    """Mock failed subprocess execution."""

    async def mock_run(*args, **kwargs):
        return (1, "", "Error: Command failed")

    with patch(
        "skillpack.engines.BaseEngine._run_process",
        new_callable=lambda: AsyncMock(side_effect=mock_run),
    ) as mock:
        yield mock


@pytest.fixture
def skillpack_rc(temp_repo: Path) -> Path:
    """Create a .skillpackrc file in temp repo."""
    config = {
        "default_engine": "codex",
        "auto_stash": True,
        "auto_branch": True,
        "parallel_variants": 3,
        "log_level": "debug",
        "output_format": "rich",
        "codex": {
            "sandbox": "workspace-write",
            "full_auto": True,
            "timeout_seconds": 300,
        },
    }
    rc_file = temp_repo / ".skillpackrc"
    rc_file.write_text(json.dumps(config, indent=2))
    return rc_file
