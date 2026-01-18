"""Core skill orchestrator with async execution and Rich UI."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from rich import box
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from .engines import Engine, get_engine
from .logging import get_console, log
from .models import (
    EngineType,
    GitCheckpoint,
    KnowledgeHooksConfig,
    NotebookLMConfig,
    QueryContext,
    RunMeta,
    RunResult,
    SkillpackConfig,
    WorkflowDef,
)

console = get_console()

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "workflows"
PROMPTS = ROOT / "prompts"


def generate_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_config(repo: Path) -> SkillpackConfig:
    """Load config from .skillpackrc or defaults."""
    rc_file = repo / ".skillpackrc"
    if rc_file.exists():
        data = json.loads(rc_file.read_text(encoding="utf-8"))
        return SkillpackConfig(**data)
    return SkillpackConfig()


def load_workflow(name: str) -> WorkflowDef:
    """Load and validate workflow definition."""
    path = WORKFLOWS / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown skill '{name}'. Missing: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkflowDef(**data)


def render_prompt(template: str, variables: dict[str, str]) -> str:
    """Render prompt template with variables."""
    content = (PROMPTS / template).read_text(encoding="utf-8")
    for key, value in variables.items():
        content = content.replace("{{" + key + "}}", value or "")
    return content


class GitManager:
    """Git operations with safety defaults."""

    def __init__(self, repo: Path):
        self.repo = repo

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + args,
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=check,
        )

    @property
    def is_repo(self) -> bool:
        try:
            self._run(["rev-parse", "--is-inside-work-tree"])
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @property
    def current_branch(self) -> str:
        result = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    @property
    def is_dirty(self) -> bool:
        result = self._run(["status", "--porcelain"])
        return bool(result.stdout.strip())

    def stash(self, message: str) -> bool:
        """Stash changes. Returns True if stash was created."""
        if not self.is_dirty:
            return False
        self._run(["stash", "push", "-u", "-m", message], check=False)
        return True

    def create_branch(self, name: str) -> bool:
        """Create and checkout branch."""
        try:
            self._run(["checkout", "-b", name])
            return True
        except subprocess.CalledProcessError:
            return False

    def restore_branch(self, branch: str, pop_stash: bool = False) -> None:
        """Restore to original branch."""
        self._run(["checkout", branch], check=False)
        if pop_stash:
            self._run(["stash", "pop"], check=False)

    def checkpoint(self, skill: str, run_id: str, stash: bool = True) -> GitCheckpoint:
        """Create a safe checkpoint before running skill."""
        if not self.is_repo:
            return GitCheckpoint(enabled=False, reason="not a git repo")

        checkpoint = GitCheckpoint(
            enabled=True,
            before_branch=self.current_branch,
            dirty=self.is_dirty,
        )

        if stash and checkpoint.dirty:
            checkpoint.stashed = self.stash(f"skillpack:{skill}:{run_id}")

        branch_name = f"skill/{skill}/{run_id}"
        if self.create_branch(branch_name):
            checkpoint.branch = branch_name

        return checkpoint


class SkillRunner:
    """Orchestrates skill execution with async support."""

    def __init__(
        self,
        repo: Path,
        config: SkillpackConfig | None = None,
        notebook_id: str | None = None,
        no_knowledge: bool = False,
    ):
        self.repo = repo.resolve()
        self.config = config or load_config(self.repo)
        self.git = GitManager(self.repo)
        self.notebook_id = notebook_id
        self.no_knowledge = no_knowledge
        self._knowledge_engine = None

    def _get_knowledge_engine(self):
        """Lazy-initialize knowledge engine if configured."""
        if self._knowledge_engine is not None:
            return self._knowledge_engine

        if self.no_knowledge or not self.notebook_id:
            return None

        try:
            from .ralph.memory import MemoryManager
            from .ralph.notebooklm import NotebookLMBridge

            memory = MemoryManager(self.repo)
            config = NotebookLMConfig(
                enabled=True,
                default_notebook_id=self.notebook_id,
            )
            self._knowledge_engine = NotebookLMBridge(self.repo, memory, config)
            return self._knowledge_engine
        except Exception as e:
            log.warning(f"Failed to initialize knowledge engine: {e}")
            return None

    async def _query_knowledge(
        self,
        hooks: KnowledgeHooksConfig,
        task: str,
    ) -> str:
        """Query NotebookLM for knowledge context."""
        engine = self._get_knowledge_engine()
        if not engine or not hooks.enabled or not hooks.query_before:
            return ""

        try:
            # Build query context
            context = QueryContext()

            # Expand queries with task placeholder
            queries = [q.replace("{{TASK}}", task) for q in hooks.queries]

            if not queries:
                return ""

            # Execute batch query
            responses = await engine.batch_query(queries, context)

            # Format knowledge context
            knowledge_text = engine.format_context(responses)
            if knowledge_text:
                log.info(f"[dim]Knowledge context retrieved ({len(responses)} queries)[/dim]")
            return knowledge_text

        except Exception as e:
            log.warning(f"Knowledge query failed (continuing without): {e}")
            return ""

    def _ensure_dirs(self, run_id: str, subdir: str) -> tuple[Path, Path]:
        """Create output directories."""
        root = self.repo / ".skillpack" / "runs" / run_id
        out = root / subdir
        out.mkdir(parents=True, exist_ok=True)
        return root, out

    def _write_meta(self, root: Path, meta: RunMeta) -> None:
        """Write run metadata."""
        meta_file = root / "meta.json"
        meta_file.write_text(
            meta.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

    async def _execute_variant(
        self,
        engine: Engine,
        prompt: str,
        output_file: Path,
        variant: int,
        progress: Progress,
        task_id: int,
    ) -> RunResult:
        """Execute a single variant."""
        result = await engine.execute(self.repo, prompt, output_file, variant)
        progress.update(task_id, advance=1)
        return result

    async def run(
        self,
        skill: str,
        task: str = "",
        plan_file: str | None = None,
        run_id: str | None = None,
        variants: int | None = None,
        no_git_checkpoint: bool = False,
        no_git_stash: bool = False,
        _pipeline_vars: dict[str, str] | None = None,
        **engine_overrides,
    ) -> RunMeta:
        """Execute a skill with full orchestration.

        Args:
            skill: Name of the skill/workflow to run
            task: Task description
            plan_file: Optional path to a plan file (its content becomes PLAN_TEXT)
            run_id: Optional custom run ID
            variants: Number of variants to generate
            no_git_checkpoint: Skip git branch/stash
            no_git_stash: Skip auto-stash (but still create branch)
            _pipeline_vars: Variables injected by pipeline (e.g., from pass_output_as)
            **engine_overrides: Override engine config options
        """
        # Load workflow
        workflow = load_workflow(skill)
        run_id = run_id or generate_run_id()
        variants = variants or workflow.variants

        # Log skill start
        log.skill_start(skill, run_id, variants)

        # Setup output dirs
        root, out_dir = self._ensure_dirs(run_id, workflow.output.dir)

        # Initialize metadata
        meta = RunMeta(
            run_id=run_id,
            skill=skill,
            engine=workflow.engine,
            variants=variants,
            repo=str(self.repo),
            started_at=datetime.now(),
            git=GitCheckpoint(enabled=False),
        )

        # Git checkpoint
        if not no_git_checkpoint:
            meta.git = self.git.checkpoint(skill, run_id, stash=not no_git_stash)
            if meta.git.branch:
                log.git_checkpoint(meta.git.branch, meta.git.stashed)

        # Load plan file if provided
        plan_text = ""
        if plan_file:
            plan_text = Path(plan_file).read_text(encoding="utf-8", errors="ignore")

        # Query knowledge if hooks are configured
        knowledge_context = ""
        if workflow.knowledge_hooks and not self.no_knowledge:
            knowledge_context = await self._query_knowledge(workflow.knowledge_hooks, task)

        # Build template variables
        template_vars = {
            "TASK": task,
            "PLAN_TEXT": plan_text,
            "KNOWLEDGE_CONTEXT": knowledge_context,
        }

        # Merge pipeline-injected variables (e.g., pass_output_as)
        if _pipeline_vars:
            template_vars.update(_pipeline_vars)

        # Render prompt (with knowledge context injection)
        prompt = render_prompt(workflow.prompt_template, template_vars)

        # If knowledge context exists but not in template, append it
        template_content = (PROMPTS / workflow.prompt_template).read_text()
        if knowledge_context and "{{KNOWLEDGE_CONTEXT}}" not in template_content:
            prompt = f"{prompt}\n\n## External Knowledge (from NotebookLM)\n\n{knowledge_context}"

        # Get engine with config
        engine_config = {}
        if workflow.engine == EngineType.CODEX and workflow.codex:
            engine_config = workflow.codex.model_dump()
        elif workflow.engine == EngineType.GEMINI and workflow.gemini:
            engine_config = workflow.gemini.model_dump()
        elif workflow.engine == EngineType.CLAUDE and workflow.claude:
            engine_config = workflow.claude.model_dump()

        # Apply overrides
        engine_config.update({k: v for k, v in engine_overrides.items() if v is not None})
        engine = get_engine(workflow.engine.value, engine_config)

        # Execute with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                f"[cyan]Running {skill}...",
                total=variants,
            )

            # Build tasks
            tasks = []
            for i in range(1, variants + 1):
                output_file = out_dir / workflow.output.pattern.format(i=i)
                tasks.append(
                    self._execute_variant(engine, prompt, output_file, i, progress, task_id)
                )

            # Execute concurrently (max 5 parallel)
            semaphore = asyncio.Semaphore(min(variants, 5))

            async def bounded_execute(coro):
                async with semaphore:
                    return await coro

            meta.results = await asyncio.gather(*[bounded_execute(t) for t in tasks])

        # Finalize metadata
        meta.completed_at = datetime.now()
        meta.success_count = sum(1 for r in meta.results if r.success)
        meta.failure_count = variants - meta.success_count
        meta.total_duration_ms = sum(r.duration_ms for r in meta.results)

        # Log completion
        log.skill_complete(
            skill, run_id, meta.success_count, meta.failure_count, meta.total_duration_ms
        )

        self._write_meta(root, meta)

        return meta

    def display_results(self, meta: RunMeta) -> None:
        """Display run results with Rich formatting."""
        # Summary panel
        status = "✅ Success" if meta.failure_count == 0 else f"⚠️ {meta.failure_count} failures"

        summary = Table(show_header=False, box=box.SIMPLE)
        summary.add_column("Key", style="dim")
        summary.add_column("Value")
        summary.add_row("Run ID", meta.run_id)
        summary.add_row("Skill", meta.skill)
        summary.add_row("Engine", meta.engine.value)
        summary.add_row("Variants", f"{meta.success_count}/{meta.variants}")
        summary.add_row("Duration", f"{meta.total_duration_ms}ms")
        summary.add_row("Status", status)

        if meta.git.enabled and meta.git.branch:
            summary.add_row("Branch", meta.git.branch)

        border = "green" if meta.failure_count == 0 else "yellow"
        console.print(Panel(summary, title="[bold]Run Summary", border_style=border))

        # Output files
        if meta.results:
            tree = Tree("[bold]📁 Outputs")
            for r in meta.results:
                if r.output_file and r.output_file.exists():
                    tree.add(f"[green]{r.output_file.relative_to(self.repo)}")
                elif r.error:
                    tree.add(f"[red]V{r.variant}: {r.error[:80]}")
            console.print(tree)


def doctor(repo: Path) -> None:
    """Check environment setup."""
    console.print(Panel("[bold]🩺 Skill Doctor", border_style="blue"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")

    # Git
    git = GitManager(repo)
    table.add_row(
        "Git Repo",
        "✅" if git.is_repo else "❌",
        str(repo) if git.is_repo else "Not a git repository",
    )

    # Required binaries
    for name, install_cmd in [
        ("git", "apt install git"),
        ("codex", "npm i -g @openai/codex"),
        ("gemini", "npm i -g @google/gemini-cli"),
        ("claude", "npm i -g @anthropic-ai/claude-code"),
    ]:
        path = shutil.which(name)
        table.add_row(
            name,
            "✅" if path else "⚠️ Optional" if name == "claude" else "❌",
            path or f"Install: {install_cmd}",
        )

    # Login status
    if shutil.which("codex"):
        result = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
        )
        table.add_row(
            "Codex Auth",
            "✅" if result.returncode == 0 else "❌",
            "Logged in" if result.returncode == 0 else "Run: codex login",
        )

    console.print(table)

    # Available workflows
    console.print("\n[bold]Available Skills:")
    for wf_file in sorted(WORKFLOWS.glob("*.json")):
        try:
            wf = load_workflow(wf_file.stem)
            console.print(f"  • [cyan]{wf.name}[/] ({wf.engine.value}, {wf.variants} variants)")
        except Exception as e:
            console.print(f"  • [red]{wf_file.stem}[/] (error: {e})")


async def run_pipeline(
    runner: SkillRunner,
    skills: list[str],
    task: str,
    **kwargs,
) -> list[RunMeta]:
    """Run multiple skills in sequence (pipeline).

    Supports workflow dependencies via `depends_on` and `pass_output_as` fields.
    When a workflow declares `depends_on`, it validates the dependency was executed.
    The `pass_output_as` field specifies which variable receives the previous output.
    """
    results = []
    outputs: dict[str, Path] = {}  # skill_name -> output_file
    total_skills = len(skills)

    log.info(f"[bold]Pipeline[/] starting with {total_skills} skills: {', '.join(skills)}")

    for idx, skill in enumerate(skills, 1):
        log.pipeline_step(idx, total_skills, skill)
        workflow = load_workflow(skill)
        extra_kwargs = dict(kwargs)

        # Validate dependency if declared
        if workflow.depends_on and workflow.depends_on not in outputs:
            # Check if dependency is in the pipeline but not yet executed
            if workflow.depends_on in skills:
                dep_idx = skills.index(workflow.depends_on)
                curr_idx = skills.index(skill)
                if dep_idx > curr_idx:
                    console.print(
                        f"[red]Pipeline error: '{skill}' depends on '{workflow.depends_on}' "
                        f"but it comes later in the pipeline"
                    )
                    break
            else:
                console.print(
                    f"[yellow]Warning: '{skill}' depends on '{workflow.depends_on}' "
                    f"which is not in this pipeline"
                )

        # Inject previous output based on pass_output_as or fallback to plan_file
        if workflow.depends_on and workflow.depends_on in outputs:
            dep_output = outputs[workflow.depends_on]
            if workflow.pass_output_as:
                # Will be passed as a template variable
                extra_kwargs["_pipeline_vars"] = {
                    workflow.pass_output_as: dep_output.read_text(encoding="utf-8", errors="ignore")
                }
            else:
                # Fallback: pass as plan_file
                extra_kwargs["plan_file"] = str(dep_output)
        elif outputs:
            # No explicit dependency, use last output as plan_file
            last_skill = skills[skills.index(skill) - 1] if skills.index(skill) > 0 else None
            if last_skill and last_skill in outputs:
                extra_kwargs["plan_file"] = str(outputs[last_skill])

        meta = await runner.run(skill, task, **extra_kwargs)
        results.append(meta)
        runner.display_results(meta)

        # Store first successful output for downstream skills
        for r in meta.results:
            if r.success and r.output_file and r.output_file.exists():
                outputs[skill] = r.output_file
                break

        if meta.failure_count == meta.variants:
            console.print(f"[red]Pipeline stopped: {skill} failed completely")
            break

    return results
