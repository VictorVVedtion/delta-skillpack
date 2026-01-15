#!/usr/bin/env python3
"""Delta SkillPack CLI - Modern terminal workflow orchestrator."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich import box
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .core import WORKFLOWS, SkillRunner, load_workflow, run_pipeline
from .logging import get_console, init_logging
from .models import SandboxMode

console = get_console()


class AliasedGroup(click.Group):
    """Support command aliases."""
    
    def get_command(self, ctx, cmd_name):
        # Aliases
        aliases = {
            "p": "plan",
            "i": "implement", 
            "impl": "implement",
            "u": "ui",
            "d": "doctor",
            "r": "run",
            "h": "history",
            "ls": "list",
        }
        cmd_name = aliases.get(cmd_name, cmd_name)
        return super().get_command(ctx, cmd_name)


@click.group(cls=AliasedGroup, invoke_without_command=True)
@click.option("--repo", "-r", default=".", help="Repository path (default: current dir)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output")
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error"]),
    default="info",
    help="Log level",
)
@click.option("--log-file", type=click.Path(), default=None, help="Log file path")
@click.version_option(version="2.0.0", prog_name="skill")
@click.pass_context
def cli(ctx, repo: str, output_json: bool, quiet: bool, log_level: str, log_file: str | None):
    """Delta SkillPack - Workflow orchestrator for Codex, Gemini, and Claude.

    \b
    Quick start:
      skill doctor              # Check environment
      skill plan "Add charts"   # Generate 5 plans
      skill implement -f plan   # Execute a plan
      skill ui "Mobile layout"  # Generate UI spec

    \b
    Aliases:
      p → plan, i → implement, u → ui, d → doctor
    """
    # Initialize logging
    effective_level = "warning" if quiet else log_level
    init_logging(level=effective_level, log_file=Path(log_file) if log_file else None)  # type: ignore

    ctx.ensure_object(dict)
    ctx.obj["repo"] = Path(repo).resolve()
    ctx.obj["json"] = output_json
    ctx.obj["quiet"] = quiet

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command("doctor")
@click.pass_context
def doctor_cmd(ctx):
    """Check environment and list available skills."""
    from .core import doctor as run_doctor
    run_doctor(ctx.obj["repo"])


@cli.command("list")
@click.pass_context
def list_skills(ctx):
    """List available skills/workflows."""
    table = Table(title="Available Skills", box=box.ROUNDED)
    table.add_column("Skill", style="cyan")
    table.add_column("Engine")
    table.add_column("Variants")
    table.add_column("Output Dir")
    
    for wf_file in sorted(WORKFLOWS.glob("*.json")):
        try:
            wf = load_workflow(wf_file.stem)
            table.add_row(wf.name, wf.engine.value, str(wf.variants), wf.output.dir)
        except Exception:
            pass
    
    console.print(table)


def add_common_options(f):
    """Decorator to add common skill options."""
    f = click.option("--run-id", help="Custom run ID")(f)
    f = click.option("--variants", "-n", type=int, help="Number of variants")(f)
    f = click.option("--no-git", is_flag=True, help="Skip git checkpoint")(f)
    f = click.option("--no-stash", is_flag=True, help="Skip auto-stash")(f)
    f = click.option(
        "--sandbox",
        type=click.Choice(["read-only", "workspace-write", "danger-full-access"]),
        help="Sandbox mode (Codex)",
    )(f)
    f = click.option("--model", "-m", help="Model override")(f)
    f = click.option("--full-auto", is_flag=True, help="Enable full-auto mode")(f)
    f = click.option("--dry-run", is_flag=True, help="Show what would run without executing")(f)
    return f


def run_skill_command(
    ctx,
    skill: str,
    task: str,
    plan_file: str | None = None,
    **kwargs,
):
    """Common skill execution logic."""
    repo = ctx.obj["repo"]
    dry_run = kwargs.pop("dry_run", False)
    
    # Build engine overrides
    engine_overrides = {}
    if kwargs.get("sandbox"):
        engine_overrides["sandbox"] = SandboxMode(kwargs["sandbox"])
    if kwargs.get("model"):
        engine_overrides["model"] = kwargs["model"]
    if kwargs.get("full_auto"):
        engine_overrides["full_auto"] = True
    
    if dry_run:
        wf = load_workflow(skill)
        console.print(Panel(f"""
[bold]Dry Run: {skill}[/]
• Engine: {wf.engine.value}
• Variants: {kwargs.get('variants') or wf.variants}
• Output: .skillpack/runs/<id>/{wf.output.dir}/
• Task: {task[:100]}...
        """.strip(), border_style="yellow"))
        return
    
    runner = SkillRunner(repo)
    
    async def execute():
        meta = await runner.run(
            skill=skill,
            task=task,
            plan_file=plan_file,
            run_id=kwargs.get("run_id"),
            variants=kwargs.get("variants"),
            no_git_checkpoint=kwargs.get("no_git", False),
            no_git_stash=kwargs.get("no_stash", False),
            **engine_overrides,
        )
        runner.display_results(meta)
        return meta
    
    return asyncio.run(execute())


@cli.command()
@click.argument("task", required=False, default="")
@add_common_options
@click.pass_context
def plan(ctx, task: str, **kwargs):
    """Generate implementation plans (read-only, parallel variants).
    
    \b
    Examples:
      skill plan "Add candlestick chart to Trade page"
      skill plan "Implement user authentication" -n 3
      skill plan "Refactor API layer" --model gpt-4
    """
    if not task:
        task = Prompt.ask("[cyan]Enter task description")
    
    run_skill_command(ctx, "plan", task, **kwargs)


@cli.command()
@click.argument("task", required=False, default="")
@click.option("--plan-file", "-f", help="Plan file to implement")
@click.option("--interactive", "-i", is_flag=True, help="Interactively select plan")
@add_common_options
@click.pass_context
def implement(ctx, task: str, plan_file: str | None, interactive: bool, **kwargs):
    """Implement a selected plan (workspace-write).
    
    \b
    Examples:
      skill implement -f .skillpack/runs/xxx/plans/plan_1.md
      skill implement -i  # Interactive plan selection
      skill implement "Apply the auth plan" -f plan.md
    """
    repo = ctx.obj["repo"]
    
    # Interactive plan selection
    if interactive and not plan_file:
        runs_dir = repo / ".skillpack" / "runs"
        if runs_dir.exists():
            plans = list(runs_dir.glob("*/plans/plan_*.md"))
            if plans:
                plans = sorted(plans, key=lambda p: p.stat().st_mtime, reverse=True)[:10]
                console.print("[bold]Recent plans:")
                for i, p in enumerate(plans, 1):
                    preview = p.read_text()[:100].replace("\n", " ")
                    console.print(f"  {i}. {p.relative_to(repo)} - {preview}...")
                
                choice = Prompt.ask("Select plan", choices=[str(i) for i in range(1, len(plans)+1)])
                plan_file = str(plans[int(choice)-1])
    
    if not plan_file and not task:
        console.print("[yellow]Provide --plan-file or task description")
        return
    
    run_skill_command(ctx, "implement", task, plan_file=plan_file, **kwargs)


@cli.command()
@click.argument("task", required=False, default="")
@add_common_options
@click.pass_context
def ui(ctx, task: str, **kwargs):
    """Generate UI specification (Gemini, headless).
    
    \b
    Examples:
      skill ui "Mobile layout for Trade page"
      skill ui "Component tree for Dashboard"
    """
    if not task:
        task = Prompt.ask("[cyan]Enter UI task description")
    
    run_skill_command(ctx, "ui", task, **kwargs)


@cli.command()
@click.argument("skill_name")
@click.argument("task", required=False, default="")
@click.option("--plan-file", "-f", help="Plan file input")
@add_common_options
@click.pass_context
def run(ctx, skill_name: str, task: str, plan_file: str | None, **kwargs):
    """Run any workflow by name.
    
    \b
    Examples:
      skill run review "Check code quality"
      skill run deploy --full-auto
    """
    run_skill_command(ctx, skill_name, task, plan_file=plan_file, **kwargs)


@cli.command()
@click.argument("skills", nargs=-1, required=True)
@click.argument("task")
@add_common_options
@click.pass_context
def pipeline(ctx, skills: tuple[str, ...], task: str, **kwargs):
    """Run multiple skills in sequence.
    
    \b
    Examples:
      skill pipeline plan implement "Add user auth"
      skill pipeline plan implement ui "Build dashboard"
    """
    repo = ctx.obj["repo"]
    
    # Build engine overrides
    engine_overrides = {}
    if kwargs.get("sandbox"):
        engine_overrides["sandbox"] = SandboxMode(kwargs["sandbox"])
    
    runner = SkillRunner(repo)
    
    async def execute():
        return await run_pipeline(
            runner,
            list(skills),
            task,
            run_id=kwargs.get("run_id"),
            variants=kwargs.get("variants"),
            no_git_checkpoint=kwargs.get("no_git", False),
            no_git_stash=kwargs.get("no_stash", False),
            **engine_overrides,
        )
    
    asyncio.run(execute())


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of runs to show")
@click.pass_context
def history(ctx, limit: int):
    """Show recent skill runs."""
    repo = ctx.obj["repo"]
    runs_dir = repo / ".skillpack" / "runs"
    
    if not runs_dir.exists():
        console.print("[yellow]No runs found")
        return
    
    table = Table(title="Recent Runs", box=box.ROUNDED)
    table.add_column("Run ID")
    table.add_column("Skill")
    table.add_column("Engine")
    table.add_column("Success")
    table.add_column("Duration")
    
    import json
    runs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    
    for run_dir in runs:
        meta_file = run_dir / "meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                success = f"{meta.get('success_count', '?')}/{meta.get('variants', '?')}"
                duration = f"{meta.get('total_duration_ms', 0)}ms"
                table.add_row(
                    meta.get("run_id", run_dir.name),
                    meta.get("skill", "?"),
                    meta.get("engine", "?"),
                    success,
                    duration,
                )
            except Exception:
                table.add_row(run_dir.name, "?", "?", "?", "?")
    
    console.print(table)


@cli.command()
@click.argument("run_id")
@click.pass_context
def show(ctx, run_id: str):
    """Show details of a specific run."""
    repo = ctx.obj["repo"]
    run_dir = repo / ".skillpack" / "runs" / run_id
    
    if not run_dir.exists():
        console.print(f"[red]Run not found: {run_id}")
        return
    
    meta_file = run_dir / "meta.json"
    if meta_file.exists():
        from rich.syntax import Syntax
        content = meta_file.read_text()
        console.print(Syntax(content, "json", theme="monokai"))
    
    # List outputs
    console.print("\n[bold]Outputs:")
    for f in run_dir.rglob("*.md"):
        console.print(f"  • {f.relative_to(run_dir)}")


# =============================================================================
# Ralph - Industrial Automation Development
# =============================================================================


@cli.group()
@click.pass_context
def ralph(ctx):
    """Ralph - PRD-driven autonomous development.

    \b
    Quick start:
      skill ralph init "Add user authentication"
      skill ralph status
      skill ralph start
    """
    pass


@ralph.command("init")
@click.argument("task")
@click.option("--prd-file", "-f", help="Use existing PRD JSON file")
@click.pass_context
def ralph_init(ctx, task: str, prd_file: str | None):
    """Initialize PRD from task description.

    \b
    Examples:
      skill ralph init "Add K-line chart to Trade page"
      skill ralph init -f requirements.json
    """
    import json
    from datetime import datetime

    from .models import PRD, StoryType, UserStory
    from .ralph import MemoryManager

    repo = ctx.obj["repo"]
    memory = MemoryManager(repo)

    if prd_file:
        # Load existing PRD
        prd_path = Path(prd_file)
        if not prd_path.exists():
            console.print(f"[red]PRD file not found: {prd_file}")
            return
        try:
            data = json.loads(prd_path.read_text())
            prd = PRD.model_validate(data)
        except Exception as e:
            console.print(f"[red]Failed to parse PRD: {e}")
            return
    else:
        # Generate a simple PRD from task
        prd_id = f"PRD-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        prd = PRD(
            id=prd_id,
            title=task[:50],
            description=task,
            stories=[
                UserStory(
                    id="STORY-001",
                    title=task[:30],
                    description=task,
                    type=StoryType.FEATURE,
                    priority="p1",
                    acceptance_criteria=["Implementation complete", "Tests pass"],
                )
            ],
        )
        console.print(
            "[yellow]Note: Generated simple PRD. "
            "For complex tasks, use 'skill plan' first to generate detailed plans."
        )

    memory.save_prd(prd)
    console.print(f"[green]PRD initialized: {prd.id}")
    console.print(f"  Stories: {len(prd.stories)}")
    for story in prd.stories:
        console.print(f"    • {story.id} [{story.priority}] {story.title} ({story.type.value})")


@ralph.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def ralph_status(ctx, as_json: bool):
    """Show current PRD execution status."""
    import json as json_module

    from .ralph import MemoryManager

    repo = ctx.obj["repo"]
    memory = MemoryManager(repo)

    prd = memory.load_prd()
    if prd is None:
        if as_json:
            console.print("{}")
        else:
            console.print("[yellow]No PRD found. Run 'skill ralph init' first.")
        return

    if as_json:
        data = {
            "id": prd.id,
            "title": prd.title,
            "completion_rate": prd.completion_rate,
            "is_complete": prd.is_complete,
            "stories": len(prd.stories),
            "passed": sum(1 for s in prd.stories if s.passes),
            "pending": sum(1 for s in prd.stories if not s.passes),
        }
        console.print(json_module.dumps(data, indent=2))
    else:
        table = Table(title=f"PRD: {prd.title}", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Type")
        table.add_column("Priority")
        table.add_column("Status")
        table.add_column("Attempts")

        for story in prd.stories:
            status = "[green]✓[/]" if story.passes else "[yellow]○[/]"
            table.add_row(
                story.id,
                story.title[:30],
                story.type.value,
                story.priority,
                status,
                str(story.attempts),
            )

        console.print(table)
        console.print(f"\nCompletion: {prd.completion_rate * 100:.1f}%")


@ralph.command("start")
@click.option("--max-iterations", "-n", default=100, help="Maximum iterations")
@click.option("--dry-run", is_flag=True, help="Show what would run")
@click.pass_context
def ralph_start(ctx, max_iterations: int, dry_run: bool):
    """Start Ralph automation loop.

    \b
    Examples:
      skill ralph start
      skill ralph start --max-iterations 50
      skill ralph start --dry-run
    """
    from .ralph import MemoryManager, StoryOrchestrator

    repo = ctx.obj["repo"]
    memory = MemoryManager(repo)

    prd = memory.load_prd()
    if prd is None:
        console.print("[red]No PRD found. Run 'skill ralph init' first.")
        return

    if dry_run:
        console.print(Panel(f"""
[bold]Dry Run: Ralph Automation[/]
• PRD: {prd.id}
• Stories: {len(prd.stories)}
• Max Iterations: {max_iterations}
• Would execute until complete or max iterations reached
        """.strip(), border_style="yellow"))
        return

    console.print("[bold]Starting Ralph automation loop[/]")
    console.print(f"  PRD: {prd.id}")
    console.print(f"  Stories: {len(prd.stories)}")
    console.print(f"  Max Iterations: {max_iterations}")
    console.print()

    orchestrator = StoryOrchestrator(repo)
    complete = asyncio.run(orchestrator.run_loop(prd, max_iterations))

    if complete:
        console.print("\n[green]<promise>COMPLETE</promise>[/]")
    else:
        console.print("\n[yellow]Loop ended without completing all stories.[/]")


@ralph.command("next-story")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def ralph_next_story(ctx, as_json: bool):
    """Get next story to execute (for scripts)."""
    import json as json_module

    from .ralph import MemoryManager

    repo = ctx.obj["repo"]
    memory = MemoryManager(repo)

    prd = memory.load_prd()
    if prd is None:
        console.print("null" if as_json else "[yellow]No PRD found")
        return

    story = prd.next_story()
    if story is None:
        console.print("null" if as_json else "[yellow]No pending stories")
        return

    if as_json:
        data = {
            "id": story.id,
            "title": story.title,
            "type": story.type.value,
            "priority": story.priority,
            "attempts": story.attempts,
        }
        console.print(json_module.dumps(data))
    else:
        console.print(f"{story.id}: {story.title} ({story.type.value})")


@ralph.command("story-status")
@click.option("--story-id", required=True, help="Story ID to check")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def ralph_story_status(ctx, story_id: str, as_json: bool):
    """Get status of a specific story."""
    import json as json_module

    from .ralph import MemoryManager

    repo = ctx.obj["repo"]
    memory = MemoryManager(repo)

    prd = memory.load_prd()
    if prd is None:
        console.print("null" if as_json else "[yellow]No PRD found")
        return

    story = next((s for s in prd.stories if s.id == story_id), None)
    if story is None:
        console.print("null" if as_json else f"[yellow]Story not found: {story_id}")
        return

    if as_json:
        data = {
            "id": story.id,
            "title": story.title,
            "type": story.type.value,
            "passes": story.passes,
            "attempts": story.attempts,
            "last_error": story.last_error,
        }
        console.print(json_module.dumps(data))
    else:
        status = "[green]✓ Passed[/]" if story.passes else "[yellow]○ Pending[/]"
        console.print(f"{story.id}: {status}")
        if story.last_error:
            console.print(f"  Last error: {story.last_error}")


@ralph.command("execute-pipeline")
@click.option("--story-id", required=True, help="Story ID to execute")
@click.option("--steps", required=True, help="Comma-separated steps")
@click.pass_context
def ralph_execute_pipeline(ctx, story_id: str, steps: str):
    """Execute skill pipeline for a story.

    \b
    Examples:
      skill ralph execute-pipeline --story-id STORY-001 --steps "plan,implement,review,verify"
    """
    from .ralph import MemoryManager, StoryOrchestrator

    repo = ctx.obj["repo"]
    memory = MemoryManager(repo)

    prd = memory.load_prd()
    if prd is None:
        console.print("[red]No PRD found")
        return

    story = next((s for s in prd.stories if s.id == story_id), None)
    if story is None:
        console.print(f"[red]Story not found: {story_id}")
        return

    console.print(f"[bold]Executing pipeline for {story_id}[/]")
    console.print(f"  Steps: {steps}")

    orchestrator = StoryOrchestrator(repo)
    success = asyncio.run(orchestrator.execute_story(story))

    memory.save_prd(prd)

    if success:
        console.print(f"[green]✓ {story_id} completed successfully[/]")
    else:
        console.print(f"[red]✗ {story_id} failed: {story.last_error}[/]")


@ralph.command("mark-failed")
@click.option("--story-id", required=True, help="Story ID to mark")
@click.option("--error", required=True, help="Error message")
@click.pass_context
def ralph_mark_failed(ctx, story_id: str, error: str):
    """Mark a story as failed (for scripts)."""
    from .ralph import MemoryManager

    repo = ctx.obj["repo"]
    memory = MemoryManager(repo)

    prd = memory.load_prd()
    if prd is None:
        console.print("[red]No PRD found")
        return

    story = next((s for s in prd.stories if s.id == story_id), None)
    if story is None:
        console.print(f"[red]Story not found: {story_id}")
        return

    story.last_error = error
    story.attempts += 1
    memory.save_prd(prd)

    console.print(f"[yellow]Marked {story_id} as failed: {error}")


@ralph.command("cancel")
@click.pass_context
def ralph_cancel(ctx):
    """Cancel current Ralph loop."""
    repo = ctx.obj["repo"]
    cancel_file = repo / ".skillpack" / "ralph" / ".cancel"
    cancel_file.write_text("cancel")
    console.print("[yellow]Cancel signal sent. Loop will stop after current iteration.")


def main():
    """Entry point."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
