"""
Skillpack CLI 命令

提供 /do 命令的 CLI 接口。
"""

import json
from pathlib import Path
from typing import Optional

import click

from .models import (
    SkillpackConfig,
    KnowledgeConfig,
    RoutingConfig,
    CheckpointConfig,
    ParallelConfig,
    MCPConfig,
    CLIConfig,
    CrossValidationConfig,
    OutputConfig,
    ExecutionRoute,
)
from .router import TaskRouter
from .executor import TaskExecutor
from .checkpoint import CheckpointManager, Checkpoint


@click.group()
@click.version_option(version="5.4.2", prog_name="skillpack")
def cli():
    """Skillpack - 智能任务执行器 v5.4.2"""
    pass


@cli.command()
@click.argument("description", required=False)
@click.option("-q", "--quick", is_flag=True, help="强制 DIRECT 路由")
@click.option("-d", "--deep", is_flag=True, help="强制 RALPH 路由")
@click.option("--parallel/--no-parallel", default=None, help="并行执行控制")
@click.option("--cli", "cli_mode", is_flag=True, help="CLI 直接调用模式")
@click.option("-e", "--explain", is_flag=True, help="仅显示评分和路由")
@click.option("--resume", "resume_task", default=None, is_flag=False, flag_value="__latest__", help="从检查点恢复 (可指定 task_id)")
@click.option("--list-checkpoints", is_flag=True, help="列出可恢复任务")
@click.option("--quiet", is_flag=True, help="安静模式")
def do(
    description: Optional[str],
    quick: bool,
    deep: bool,
    parallel: Optional[bool],
    cli_mode: bool,
    explain: bool,
    resume_task: Optional[str],
    list_checkpoints: bool,
    quiet: bool,
):
    """执行任务"""
    if list_checkpoints:
        _list_checkpoints()
        return

    if resume_task is not None:
        # --resume 或 --resume <task_id>
        task_id = None if resume_task == "__latest__" else resume_task
        _resume_task(task_id)
        return
    
    if not description:
        click.echo("错误: 需要提供任务描述")
        return
    
    # 加载配置
    config = _load_config()
    
    # 路由分析
    router = TaskRouter(config)
    context = router.route(
        description=description,
        quick_mode=quick,
        deep_mode=deep,
        parallel_mode=parallel,
        cli_mode=cli_mode,
    )
    
    if explain:
        click.echo(router.explain_routing(context))
        return
    
    # 执行任务（传递配置）
    executor = TaskExecutor(config=config, quiet=quiet)
    status = executor.execute(context)
    
    if status.error:
        click.echo(f"✗ 执行失败: {status.error}")
    elif not quiet:
        click.echo("✓ 任务完成")


@cli.command()
def status():
    """查看当前任务状态"""
    current_dir = Path(".skillpack/current")
    
    if not current_dir.exists():
        click.echo("没有正在执行的任务")
        return
    
    checkpoint_file = current_dir / "checkpoint.json"
    if checkpoint_file.exists():
        try:
            data = json.loads(checkpoint_file.read_text())
            click.echo(f"任务: {data.get('description', 'N/A')}")
            click.echo(f"状态: {data.get('status', 'N/A')}")
            click.echo(f"进度: {data.get('progress', 0) * 100:.0f}%")
        except Exception:
            click.echo("无法读取任务状态")
    else:
        click.echo("没有正在执行的任务")


@cli.command()
@click.option("-y", "--yes", is_flag=True, help="跳过确认")
def init(yes: bool):
    """初始化 skillpack 配置"""
    config_path = Path(".skillpackrc")
    
    if config_path.exists() and not yes:
        if not click.confirm("配置文件已存在，是否覆盖？"):
            click.echo("取消初始化")
            return
    
    default_config = {
        "version": "5.4",
        "knowledge": {
            "default_notebook": None,
            "auto_query": True
        },
        "routing": {
            "weights": {
                "scope": 25,
                "dependency": 20,
                "technical": 20,
                "risk": 15,
                "time": 10,
                "ui": 10
            },
            "thresholds": {
                "direct": 20,
                "planned": 45,
                "ralph": 70
            }
        },
        "checkpoint": {
            "auto_save": True,
            "save_interval_minutes": 5
        },
        "parallel": {
            "enabled": False,
            "max_concurrent_tasks": 3
        }
    }
    
    config_path.write_text(json.dumps(default_config, indent=2, ensure_ascii=False))
    click.echo("✓ 配置文件已创建: .skillpackrc")


@cli.command()
def history():
    """查看任务历史"""
    history_dir = Path(".skillpack/history")

    if not history_dir.exists():
        click.echo("没有历史记录")
        return

    entries = sorted(history_dir.iterdir(), reverse=True)
    if not entries:
        click.echo("没有历史记录")
        return

    click.echo("任务历史:")
    for entry in entries[:10]:
        click.echo(f"  - {entry.name}")


@cli.command()
@click.option("--today", is_flag=True, help="显示今日统计")
@click.option("--week", is_flag=True, help="显示本周统计")
@click.option("--json", "as_json", is_flag=True, help="JSON 格式输出")
@click.option("--export", type=click.Path(), help="导出到文件")
def stats(today: bool, week: bool, as_json: bool, export: str):
    """显示模型用量统计"""
    from .usage import UsageStore, UsageAnalyzer, print_dashboard, summary_to_json

    store = UsageStore()
    analyzer = UsageAnalyzer(store)

    # 确定时间范围
    if today:
        summary = analyzer.get_today_stats()
        period_label = "今日"
    elif week:
        summary = analyzer.get_week_stats()
        period_label = "本周"
    else:
        summary = analyzer.analyze()
        period_label = "全部"

    if as_json:
        # JSON 格式输出
        output = summary_to_json(summary)
        if export:
            Path(export).write_text(output, encoding="utf-8")
            click.echo(f"已导出到 {export}")
        else:
            click.echo(output)
        return

    # 仪表盘格式输出
    dashboard = print_dashboard(summary, period_label)

    if export:
        Path(export).write_text(dashboard, encoding="utf-8")
        click.echo(f"已导出到 {export}")
    else:
        click.echo(dashboard)


def _load_config() -> SkillpackConfig:
    """加载配置 - 完整解析 .skillpackrc"""
    # 查找配置文件：项目根目录 > 全局目录
    local_config = Path(".skillpackrc")
    global_config = Path.home() / ".claude" / ".skillpackrc"

    data = {}
    if local_config.exists():
        try:
            data = json.loads(local_config.read_text())
        except json.JSONDecodeError:
            return SkillpackConfig()
    elif global_config.exists():
        try:
            data = json.loads(global_config.read_text())
        except json.JSONDecodeError:
            return SkillpackConfig()

    if not data:
        return SkillpackConfig()

    # 解析 knowledge 配置
    knowledge_data = data.get("knowledge", {})
    knowledge = KnowledgeConfig(
        default_notebook=knowledge_data.get("default_notebook"),
        auto_query=knowledge_data.get("auto_query", True),
    )

    # 解析 routing 配置
    routing_data = data.get("routing", {})
    routing = RoutingConfig(
        weights=routing_data.get("weights", RoutingConfig().weights),
        thresholds=routing_data.get("thresholds", RoutingConfig().thresholds),
    )

    # 解析 checkpoint 配置
    checkpoint_data = data.get("checkpoint", {})
    checkpoint = CheckpointConfig(
        auto_save=checkpoint_data.get("auto_save", True),
        atomic_writes=checkpoint_data.get("atomic_writes", True),
        backup_count=checkpoint_data.get("backup_count", 3),
        save_interval_minutes=checkpoint_data.get("save_interval_minutes", 5),
        max_history=checkpoint_data.get("max_history", 10),
    )

    # 解析 parallel 配置
    parallel_data = data.get("parallel", {})
    parallel = ParallelConfig(
        enabled=parallel_data.get("enabled", False),
        max_concurrent_tasks=parallel_data.get("max_concurrent_tasks", 3),
        poll_interval_seconds=parallel_data.get("poll_interval_seconds", 5),
        task_timeout_seconds=parallel_data.get("task_timeout_seconds", 300),
        allow_cross_model_parallel=parallel_data.get("allow_cross_model_parallel", True),
        fallback_to_serial_on_failure=parallel_data.get("fallback_to_serial_on_failure", True),
    )

    # 解析 mcp 配置
    mcp_data = data.get("mcp", {})
    mcp = MCPConfig(
        timeout_seconds=mcp_data.get("timeout_seconds", 180),
        max_retries=mcp_data.get("max_retries", 1),
        auto_fallback_to_cli=mcp_data.get("auto_fallback_to_cli", True),
    )

    # 解析 cli 配置（关键！）
    # v5.4.2: 优先使用 codex_command，codex_path 为废弃别名
    cli_data = data.get("cli", {})
    codex_cmd = cli_data.get("codex_command") or cli_data.get("codex_path") or "codex"
    gemini_cmd = cli_data.get("gemini_command") or cli_data.get("gemini_path") or "gemini"
    cli = CLIConfig(
        prefer_cli_over_mcp=cli_data.get("prefer_cli_over_mcp", True),
        cli_timeout_seconds=cli_data.get("cli_timeout_seconds", 600),
        codex_command=codex_cmd,
        gemini_command=gemini_cmd,
        auto_context=cli_data.get("auto_context", True),
        max_context_files=cli_data.get("max_context_files", 15),
        max_lines_per_file=cli_data.get("max_lines_per_file", 800),
    )

    # 解析 cross_validation 配置 (v5.4)
    cv_data = data.get("cross_validation", {})
    cross_validation = CrossValidationConfig(
        enabled=cv_data.get("enabled", True),
        require_arbitration_on_disagreement=cv_data.get("require_arbitration_on_disagreement", True),
        min_confidence_for_auto_pass=cv_data.get("min_confidence_for_auto_pass", "high"),
    )

    # 解析 output 配置
    output_data = data.get("output", {})
    output = OutputConfig(
        current_dir=output_data.get("current_dir", ".skillpack/current"),
        history_dir=output_data.get("history_dir", ".skillpack/history"),
    )

    return SkillpackConfig(
        version=data.get("version", "5.4"),
        knowledge=knowledge,
        routing=routing,
        checkpoint=checkpoint,
        parallel=parallel,
        mcp=mcp,
        cli=cli,
        cross_validation=cross_validation,
        output=output,
    )


def _list_checkpoints():
    """列出可恢复的检查点"""
    config = _load_config()
    manager = CheckpointManager(
        current_dir=config.output.current_dir,
        history_dir=config.output.history_dir,
    )

    checkpoints = manager.list_checkpoints()

    if not checkpoints:
        click.echo("没有可恢复的任务")
        return

    click.echo("可恢复的任务:\n")
    click.echo("─" * 70)

    for i, cp in enumerate(checkpoints[:10], 1):
        location_icon = "📍" if cp.get("location") == "current" else "📁"
        status_icon = _get_status_icon(cp.get("status", "unknown"))
        progress = cp.get("progress", 0) * 100
        can_resume = cp.get("can_resume", False)

        click.echo(f"{location_icon} [{i}] {cp.get('task_id', 'N/A')[:20]}")
        click.echo(f"    📋 {cp.get('description', 'N/A')[:50]}")
        click.echo(f"    🔀 路由: {cp.get('route', 'N/A')} | {status_icon} 状态: {cp.get('status', 'N/A')}")
        click.echo(f"    📊 进度: {progress:.0f}% ({cp.get('current_phase', 0)}/{cp.get('total_phases', 0)} 阶段)")
        click.echo(f"    🕐 更新: {cp.get('updated_at', 'N/A')[:19]}")

        if can_resume:
            resume_phase = cp.get("resume_phase")
            if resume_phase:
                click.echo(f"    ✅ 可恢复: 从阶段 {resume_phase} 继续")
            else:
                click.echo(f"    ✅ 可恢复")
        else:
            click.echo(f"    ⚪ 不可恢复")

        click.echo("─" * 70)

    click.echo(f"\n使用 'skillpack do --resume' 恢复最近任务")
    click.echo(f"使用 'skillpack do --resume <task_id>' 恢复指定任务")


def _get_status_icon(status: str) -> str:
    """获取状态图标"""
    icons = {
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "paused": "⏸️",
        "pending": "⏳",
    }
    return icons.get(status, "❓")


def _resume_task(task_id: Optional[str] = None):
    """
    恢复任务

    Args:
        task_id: 指定任务 ID（可选）
    """
    config = _load_config()
    manager = CheckpointManager(
        current_dir=config.output.current_dir,
        history_dir=config.output.history_dir,
        atomic_writes=config.checkpoint.atomic_writes,
        backup_count=config.checkpoint.backup_count,
    )

    # 获取可恢复的检查点
    checkpoint = manager.get_resumable_checkpoint(task_id)

    if not checkpoint:
        click.echo("❌ 没有找到可恢复的任务")
        if task_id:
            click.echo(f"   指定的任务 ID '{task_id}' 不存在")
        click.echo("   使用 'skillpack do --list-checkpoints' 查看可用任务")
        return

    # 检查是否可恢复
    resume_info = checkpoint.get_resume_info()
    can_resume = resume_info.get("can_resume", False)

    if not can_resume:
        click.echo(f"⚪ 任务 '{checkpoint.task_id}' 已完成，无需恢复")
        return

    # 显示恢复信息
    click.echo(f"""
════════════════════════════════════════════════════════════
🔄 恢复任务
════════════════════════════════════════════════════════════
📋 任务: {checkpoint.task_description}
🆔 ID: {checkpoint.task_id}
🔀 路由: {checkpoint.route}
📊 进度: {checkpoint.progress * 100:.0f}% ({checkpoint.current_phase}/{checkpoint.total_phases} 阶段)
────────────────────────────────────────────────────────────
""")

    # 显示阶段状态
    click.echo("阶段状态:")
    for phase in checkpoint.phases:
        if hasattr(phase, "number"):
            num, name, status = phase.number, phase.name, phase.status
        else:
            num = phase.get("number", 0)
            name = phase.get("name", "")
            status = phase.get("status", "pending")

        status_icon = _get_status_icon(status)
        click.echo(f"  {status_icon} Phase {num}: {name} - {status}")

    click.echo("────────────────────────────────────────────────────────────")

    # 确认恢复
    resume_phase = resume_info.get("resume_phase")
    if resume_phase:
        click.echo(f"将从 Phase {resume_phase} 继续执行")

    if not click.confirm("是否继续恢复任务？"):
        click.echo("取消恢复")
        return

    # 执行恢复
    click.echo("\n正在恢复任务...")

    # 重建 TaskContext
    from .models import TaskContext, TaskComplexity

    # 确定复杂度
    route_str = checkpoint.route
    complexity_map = {
        "DIRECT": TaskComplexity.SIMPLE,
        "PLANNED": TaskComplexity.MEDIUM,
        "RALPH": TaskComplexity.COMPLEX,
        "ARCHITECT": TaskComplexity.ARCHITECT,
        "UI_FLOW": TaskComplexity.UI,
    }
    complexity = complexity_map.get(route_str, TaskComplexity.MEDIUM)

    # 确定路由
    route_enum_map = {
        "DIRECT": ExecutionRoute.DIRECT,
        "PLANNED": ExecutionRoute.PLANNED,
        "RALPH": ExecutionRoute.RALPH,
        "ARCHITECT": ExecutionRoute.ARCHITECT,
        "UI_FLOW": ExecutionRoute.UI_FLOW,
    }
    route = route_enum_map.get(route_str, ExecutionRoute.DIRECT)

    context = TaskContext(
        description=checkpoint.task_description,
        complexity=complexity,
        route=route,
        working_dir=Path.cwd(),
    )

    # 创建执行器并恢复
    executor = TaskExecutor(config=config)

    # 设置恢复模式（跳过已完成阶段）
    # 注意：这里需要在 executor 中实现恢复逻辑
    # 当前简化实现：重新执行所有阶段
    click.echo(f"\n⚠️ 注意: 当前版本将重新执行任务")
    click.echo(f"   后续版本将支持从中断点精确恢复\n")

    status = executor.execute(context)

    if status.error:
        click.echo(f"✗ 恢复执行失败: {status.error}")
        manager.mark_failed(status.error)
    else:
        click.echo("✓ 任务恢复完成")
        manager.mark_completed()


if __name__ == "__main__":
    cli()
