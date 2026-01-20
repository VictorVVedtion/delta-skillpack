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
)
from .router import TaskRouter
from .executor import TaskExecutor


@click.group()
@click.version_option(version="2.0.0", prog_name="skillpack")
def cli():
    """Skillpack - 智能任务执行器 v5.4.0"""
    pass


@cli.command()
@click.argument("description", required=False)
@click.option("-q", "--quick", is_flag=True, help="强制 DIRECT 路由")
@click.option("-d", "--deep", is_flag=True, help="强制 RALPH 路由")
@click.option("--parallel/--no-parallel", default=None, help="并行执行控制")
@click.option("--cli", "cli_mode", is_flag=True, help="CLI 直接调用模式")
@click.option("-e", "--explain", is_flag=True, help="仅显示评分和路由")
@click.option("--resume", is_flag=True, help="从检查点恢复")
@click.option("--list-checkpoints", is_flag=True, help="列出可恢复任务")
@click.option("--quiet", is_flag=True, help="安静模式")
def do(
    description: Optional[str],
    quick: bool,
    deep: bool,
    parallel: Optional[bool],
    cli_mode: bool,
    explain: bool,
    resume: bool,
    list_checkpoints: bool,
    quiet: bool,
):
    """执行任务"""
    if list_checkpoints:
        _list_checkpoints()
        return
    
    if resume:
        _resume_task()
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
    cli_data = data.get("cli", {})
    cli = CLIConfig(
        prefer_cli_over_mcp=cli_data.get("prefer_cli_over_mcp", True),
        cli_timeout_seconds=cli_data.get("cli_timeout_seconds", 600),
        codex_command=cli_data.get("codex_command", cli_data.get("codex_path", "codex")),
        gemini_command=cli_data.get("gemini_command", cli_data.get("gemini_path", "gemini")),
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
    history_dir = Path(".skillpack/history")
    
    if not history_dir.exists():
        click.echo("没有可恢复的任务")
        return
    
    checkpoints = list(history_dir.glob("*/checkpoint.json"))
    if not checkpoints:
        click.echo("没有可恢复的任务")
        return
    
    click.echo("可恢复的任务:")
    for cp in checkpoints[:10]:
        try:
            data = json.loads(cp.read_text())
            click.echo(f"  - {cp.parent.name}: {data.get('description', 'N/A')}")
        except Exception:
            pass


def _resume_task():
    """恢复任务"""
    click.echo("正在恢复任务...")
    # TODO: 实现完整的恢复逻辑
    click.echo("恢复功能尚未完全实现")


if __name__ == "__main__":
    cli()
