"""Type-safe configuration models with validation."""
from __future__ import annotations
from enum import Enum
from typing import Literal, Any
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
from datetime import datetime


class SandboxMode(str, Enum):
    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    DANGER_FULL = "danger-full-access"


class ApprovalMode(str, Enum):
    UNTRUSTED = "untrusted"
    ON_FAILURE = "on-failure"
    ON_REQUEST = "on-request"
    NEVER = "never"


class EngineType(str, Enum):
    CODEX = "codex"
    GEMINI = "gemini"
    CLAUDE = "claude"  # Future: Claude Code integration


class CodexConfig(BaseModel):
    sandbox: SandboxMode = SandboxMode.READ_ONLY
    approval: ApprovalMode = ApprovalMode.ON_REQUEST
    full_auto: bool = False
    model: str | None = None
    timeout_seconds: int = 600


class GeminiConfig(BaseModel):
    headless: bool = True
    model: str | None = None
    timeout_seconds: int = 300


class ClaudeConfig(BaseModel):
    """Future: Claude Code CLI integration."""
    model: str = "claude-sonnet-4-20250514"
    timeout_seconds: int = 600
    dangerously_skip_permissions: bool = False


class OutputConfig(BaseModel):
    dir: str
    pattern: str  # e.g. "plan_{i}.md" or "summary.md"


class WorkflowDef(BaseModel):
    """Validated workflow definition."""
    name: str
    engine: EngineType
    variants: int = Field(default=1, ge=1, le=10)
    prompt_template: str
    output: OutputConfig
    codex: CodexConfig | None = None
    gemini: GeminiConfig | None = None
    claude: ClaudeConfig | None = None
    # Pipeline support
    depends_on: str | None = None  # Previous skill that must complete first
    pass_output_as: str | None = None  # Variable name to inject previous output

    @field_validator("codex", "gemini", "claude", mode="before")
    @classmethod
    def parse_engine_config(cls, v, info):
        if v is None:
            return None
        return v


class GitCheckpoint(BaseModel):
    enabled: bool = True
    before_branch: str | None = None
    branch: str | None = None
    dirty: bool = False
    stashed: bool = False
    reason: str | None = None


class RunResult(BaseModel):
    """Result of a single variant execution."""
    model_config = {"arbitrary_types_allowed": True}

    variant: int
    success: bool
    output_file: Path | None = None
    duration_ms: int = 0
    error: str | None = None
    stdout: str | None = None
    stderr: str | None = None


class RunMeta(BaseModel):
    """Metadata for a complete skill run."""
    model_config = {"arbitrary_types_allowed": True}

    run_id: str
    skill: str
    engine: EngineType
    variants: int
    repo: str
    started_at: datetime
    completed_at: datetime | None = None
    git: GitCheckpoint
    results: list[RunResult] = []
    total_duration_ms: int = 0
    success_count: int = 0
    failure_count: int = 0


class SkillpackConfig(BaseModel):
    """Global/repo-level configuration (.skillpackrc)."""
    default_engine: EngineType = EngineType.CODEX
    auto_stash: bool = True
    auto_branch: bool = True
    parallel_variants: int = Field(default=5, ge=1, le=10)
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    output_format: Literal["rich", "json", "plain"] = "rich"
    # Engine defaults
    codex: CodexConfig = Field(default_factory=CodexConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
