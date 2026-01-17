"""Type-safe configuration models with validation."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SandboxMode(str, Enum):
    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    DANGER_FULL = "danger-full-access"


class EngineType(str, Enum):
    CODEX = "codex"
    GEMINI = "gemini"
    CLAUDE = "claude"  # Future: Claude Code integration


class ReasoningEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"  # Extra High - maximum reasoning for complex tasks


class CodexConfig(BaseModel):
    sandbox: SandboxMode = SandboxMode.WORKSPACE_WRITE
    full_auto: bool = True
    model: str | None = None
    reasoning_effort: ReasoningEffort = ReasoningEffort.XHIGH
    timeout_seconds: int = 600


class GeminiConfig(BaseModel):
    headless: bool = True
    model: str | None = None
    timeout_seconds: int = 300


class ClaudeConfig(BaseModel):
    """Claude Code CLI integration.

    Note: dangerously_skip_permissions defaults to True for automated workflows.
    Workflow configs (plan.json, review.json) can override to False for safety.
    """
    model: str = "claude-sonnet-4-5-20250929"
    timeout_seconds: int = 600
    # WARNING: True skips permission prompts - useful for automation but use with caution.
    # Workflow JSON configs (workflows/*.json) can override this to False for safety.
    dangerously_skip_permissions: bool = True
    extended_thinking: bool = True  # Enable extended thinking for deeper reasoning


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


# =============================================================================
# Ralph - Industrial Automation Development System
# =============================================================================


class StepRetryConfig(BaseModel):
    """Configuration for step-level retry behavior."""

    max_attempts: int = 3
    backoff_seconds: float = 5.0
    exponential_backoff: bool = True
    retryable_errors: list[str] = ["rate_limit", "timeout", "network"]


class RalphConfig(BaseModel):
    """Configuration for Ralph engine selection."""

    # Engine routing for skill steps
    use_claude_for_plan: bool = True       # Use Claude Opus 4.5 for planning
    use_claude_for_review: bool = True     # Use Claude Opus 4.5 for review
    codex_for_implement: bool = True       # Use Codex GPT-5.2 for implementation
    gemini_for_ui: bool = True             # Use Gemini 3 Pro for UI design

    # Claude config for plan/review steps
    claude_model: str = "claude-opus-4-5-20251101"
    claude_extended_thinking: bool = True
    claude_timeout_seconds: int = 600

    # Execution settings
    auto_commit: bool = True               # Auto commit successful stories
    max_story_attempts: int = 3            # Max retries per story
    iteration_delay_seconds: float = 2.0   # Delay between iterations
    step_retry: StepRetryConfig = Field(default_factory=StepRetryConfig)


class StoryType(str, Enum):
    """Story type determines which skill pipeline to use."""
    FEATURE = "feature"     # plan → implement → review → verify
    UI = "ui"               # ui → implement → review → browser
    REFACTOR = "refactor"   # plan → implement → review → verify
    TEST = "test"           # implement → review → verify
    DOCS = "docs"           # plan → implement → review


class SkillStep(str, Enum):
    """Individual skill step in a pipeline."""
    PLAN = "plan"           # Claude Opus 4.5
    IMPLEMENT = "implement"  # Codex GPT-5.2
    REVIEW = "review"       # Claude Opus 4.5
    UI = "ui"               # Gemini 3 Pro
    VERIFY = "verify"       # pytest + ruff
    BROWSER = "browser"     # Playwright MCP


# Story type to skill pipeline mapping
STORY_PIPELINES: dict[StoryType, list[SkillStep]] = {
    StoryType.FEATURE: [
        SkillStep.PLAN, SkillStep.IMPLEMENT, SkillStep.REVIEW, SkillStep.VERIFY
    ],
    StoryType.UI: [
        SkillStep.UI, SkillStep.IMPLEMENT, SkillStep.REVIEW, SkillStep.BROWSER
    ],
    StoryType.REFACTOR: [
        SkillStep.PLAN, SkillStep.IMPLEMENT, SkillStep.REVIEW, SkillStep.VERIFY
    ],
    StoryType.TEST: [
        SkillStep.IMPLEMENT, SkillStep.REVIEW, SkillStep.VERIFY
    ],
    StoryType.DOCS: [
        SkillStep.PLAN, SkillStep.IMPLEMENT, SkillStep.REVIEW
    ],
}


class UserStory(BaseModel):
    """A single user story with tracking state."""
    model_config = {"arbitrary_types_allowed": True}

    id: str                                   # STORY-001
    title: str                                # Short title
    description: str                          # Detailed description
    type: StoryType                           # Determines skill pipeline
    priority: str = "p1"                      # p0-p3
    acceptance_criteria: list[str] = []       # Acceptance standards
    verification_commands: list[str] = []     # Custom verification commands

    # State tracking
    passes: bool = False                      # Whether completed
    attempts: int = 0                         # Attempt count
    max_attempts: int = 3                     # Max retries
    current_step: SkillStep | None = None     # Current execution step

    # Dependencies
    depends_on: list[str] = []                # Prerequisite story IDs

    # Execution records
    last_error: str | None = None
    completed_at: datetime | None = None
    step_outputs: dict[str, str] = {}         # {step: output_file}

    def get_pipeline(self) -> list[SkillStep]:
        """Get the skill pipeline for this story type."""
        return STORY_PIPELINES[self.type]


class PRD(BaseModel):
    """Product Requirements Document with stories."""
    model_config = {"arbitrary_types_allowed": True}

    id: str
    title: str
    description: str
    stories: list[UserStory] = []

    # Global configuration
    max_iterations: int = 100
    timeout_minutes: int = 180
    require_tests: bool = True
    require_lint: bool = True

    @property
    def is_complete(self) -> bool:
        """Check if all stories are complete."""
        return all(s.passes for s in self.stories)

    @property
    def completion_rate(self) -> float:
        """Calculate completion percentage."""
        if not self.stories:
            return 1.0
        return sum(1 for s in self.stories if s.passes) / len(self.stories)

    def next_story(self) -> UserStory | None:
        """Get the next story to execute (considering priority and dependencies)."""
        pending = [
            s for s in self.stories
            if not s.passes and s.attempts < s.max_attempts
        ]
        for story in sorted(pending, key=lambda s: (s.priority, s.attempts)):
            deps_ok = all(
                any(d.id == dep and d.passes for d in self.stories)
                for dep in story.depends_on
            )
            if deps_ok:
                return story
        return None


class RalphSession(BaseModel):
    """Session state for Ralph automation."""
    model_config = {"arbitrary_types_allowed": True}

    session_id: str
    prd_id: str
    repo: str
    started_at: datetime

    # Iteration tracking
    current_iteration: int = 0
    iterations: list[dict] = []               # Per-iteration records

    # Completion state
    completed: bool = False
    completed_at: datetime | None = None
    completion_signal: str | None = None      # <promise>COMPLETE</promise>

    # Statistics
    passed_stories: int = 0
    failed_stories: int = 0
