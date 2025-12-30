#!/usr/bin/env python3
"""Delta SkillPack CLI - Modern terminal workflow orchestrator."""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

from .core import SkillRunner, doctor, load_config, load_workflow, run_pipeline, WORKFLOWS
from .models import SandboxMode, ApprovalMode
from .logging import init_logging, get_console

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
@click.option("--log-level", type=click.Choice(["debug", "info", "warning", "error"]), default="info", help="Log level")
@click.option("--log-file", type=click.Path(), default=None, help="Log file path")
@click.version_option(version="2.0.0", prog_name="skill")
@click.pass_context
def cli(ctx, repo: str, output_json: bool, quiet: bool, log_level: str, log_file: Optional[str]):
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


@cli.command()
@click.pass_context
def doctor(ctx):
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
    f = click.option(
        "--approval",
        type=click.Choice(["untrusted", "on-failure", "on-request", "never"]),
        help="Approval mode (Codex)",
    )(f)
    f = click.option("--model", "-m", help="Model override")(f)
    f = click.option("--full-auto", is_flag=True, help="Enable full-auto mode")(f)
    f = click.option("--dry-run", is_flag=True, help="Show what would run without executing")(f)
    return f


def run_skill_command(
    ctx,
    skill: str,
    task: str,
    plan_file: Optional[str] = None,
    **kwargs,
):
    """Common skill execution logic."""
    repo = ctx.obj["repo"]
    dry_run = kwargs.pop("dry_run", False)
    
    # Build engine overrides
    engine_overrides = {}
    if kwargs.get("sandbox"):
        engine_overrides["sandbox"] = SandboxMode(kwargs["sandbox"])
    if kwargs.get("approval"):
        engine_overrides["approval"] = ApprovalMode(kwargs["approval"])
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
def implement(ctx, task: str, plan_file: Optional[str], interactive: bool, **kwargs):
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
def run(ctx, skill_name: str, task: str, plan_file: Optional[str], **kwargs):
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
    if kwargs.get("approval"):
        engine_overrides["approval"] = ApprovalMode(kwargs["approval"])
    
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
