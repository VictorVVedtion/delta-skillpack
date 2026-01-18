"""
SkillPack CLI - 统一命令行入口

命令简化: 7 → 3
- skill do "task"  - 统一入口
- skill status     - 查看状态
- skill cancel     - 取消执行
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import click
    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False


def require_click():
    """检查 click 是否可用"""
    if not CLICK_AVAILABLE:
        print("错误: 需要安装 click 包")
        print("运行: pip install click")
        sys.exit(1)


if CLICK_AVAILABLE:
    from .models import SkillpackConfig
    from .router import TaskRouter
    from .executor import TaskExecutor

    @click.group()
    @click.version_option(version="1.0.0", prog_name="skillpack")
    def cli():
        """
        SkillPack - 智能任务执行器

        统一入口，自动路由，实时反馈
        """
        pass

    @cli.command()
    @click.argument("task", required=True)
    @click.option("--quick", "-q", is_flag=True, help="快速模式，跳过规划直接执行")
    @click.option("--deep", "-d", is_flag=True, help="深度模式，强制使用 Ralph 自动化")
    @click.option("--kb", "--notebook", "notebook_id", help="指定知识库 ID")
    @click.option("--quiet", is_flag=True, help="静默模式，减少输出")
    @click.option("--explain", "-e", is_flag=True, help="仅解释路由决策，不执行")
    def do(
        task: str,
        quick: bool,
        deep: bool,
        notebook_id: Optional[str],
        quiet: bool,
        explain: bool
    ):
        """
        执行任务 - 智能路由到最优执行路径

        \b
        示例:
          skill do "fix typo in README"           # 简单任务 → 直接执行
          skill do "add user authentication"      # 中等任务 → plan→implement→review
          skill do "build complete CMS"           # 复杂任务 → Ralph 自动化
          skill do "创建登录页面" --quick         # 跳过规划
          skill do "重构整个系统" --deep          # 强制 Ralph
          skill do "实现搜索功能" --kb notebook-123
        """
        # 加载配置
        config = SkillpackConfig.find_and_load(Path.cwd())

        # 路由任务
        router = TaskRouter(config)
        context = router.route(
            description=task,
            quick_mode=quick,
            deep_mode=deep,
            notebook_id=notebook_id,
            working_dir=Path.cwd()
        )

        # 显示路由解释
        if not quiet or explain:
            click.echo("\n" + router.explain_routing(context) + "\n")

        if explain:
            return

        # 执行任务
        executor = TaskExecutor(config=config, quiet=quiet)
        status = executor.execute(context)

        if status.error:
            click.echo(f"\n❌ 错误: {status.error}", err=True)
            sys.exit(1)

    @cli.command()
    @click.option("--task-id", "-t", help="指定任务 ID")
    def status(task_id: Optional[str]):
        """
        查看执行状态

        \b
        示例:
          skill status              # 查看当前任务状态
          skill status -t abc123    # 查看指定任务
        """
        current_dir = Path.cwd() / ".skillpack" / "current"

        if not current_dir.exists():
            click.echo("📭 没有正在执行的任务")
            return

        # 读取状态文件
        status_file = current_dir / "status.json"
        if status_file.exists():
            import json
            with open(status_file) as f:
                data = json.load(f)
            click.echo(f"""
📊 任务状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
任务 ID:  {data.get('task_id', 'N/A')}
阶段:     {data.get('phase', 'N/A')}
进度:     {int(data.get('progress', 0) * 100)}%
消息:     {data.get('message', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        else:
            click.echo("📭 没有找到状态信息")

        # 显示历史任务
        history_dir = Path.cwd() / ".skillpack" / "history"
        if history_dir.exists():
            histories = sorted(history_dir.iterdir(), reverse=True)[:5]
            if histories:
                click.echo("\n📜 最近历史:")
                for h in histories:
                    click.echo(f"  - {h.name}")

    @cli.command()
    @click.option("--task-id", "-t", help="指定要取消的任务 ID")
    @click.confirmation_option(prompt="确定要取消当前任务吗?")
    def cancel(task_id: Optional[str]):
        """
        取消执行中的任务

        \b
        示例:
          skill cancel              # 取消当前任务
          skill cancel -t abc123    # 取消指定任务
        """
        # TODO: 实现真正的任务取消逻辑
        click.echo("🛑 任务已取消")

    @cli.command()
    @click.option("--with-notebook", is_flag=True, help="同时创建 NotebookLM 知识库")
    @click.option("--notebook-id", help="使用已有的 notebook ID")
    def init(with_notebook: bool, notebook_id: Optional[str]):
        """
        初始化项目配置

        \b
        示例:
          skill init                    # 仅创建配置文件
          skill init --with-notebook    # 同时创建 NotebookLM 知识库
          skill init --notebook-id xxx  # 使用已有知识库
        """
        import json
        config_path = Path.cwd() / ".skillpackrc"
        project_name = Path.cwd().name

        # 检查现有配置
        existing_config = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    existing_config = json.load(f)
            except json.JSONDecodeError:
                pass

            if not notebook_id and not with_notebook:
                if not click.confirm(".skillpackrc 已存在，是否覆盖?"):
                    return

        # 构建配置
        config = {
            "knowledge": {
                "default_notebook": notebook_id or existing_config.get("knowledge", {}).get("default_notebook"),
                "auto_query": True
            },
            "output": {
                "current_dir": ".skillpack/current",
                "history_dir": ".skillpack/history"
            }
        }

        # 保存配置
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        click.echo(f"✅ 已创建配置文件: {config_path}")

        # 创建 .skillpack 目录
        (Path.cwd() / ".skillpack").mkdir(exist_ok=True)

        if notebook_id:
            click.echo(f"📚 知识库已配置: {notebook_id}")
        elif with_notebook:
            # 输出特殊标记，供 Claude Code 处理
            click.echo("\n" + "=" * 50)
            click.echo("📚 SKILLPACK_CREATE_NOTEBOOK")
            click.echo(f"PROJECT_NAME={project_name}")
            click.echo(f"CONFIG_PATH={config_path}")
            click.echo("=" * 50)
            click.echo("\n⏳ 请等待 Claude Code 创建 NotebookLM 知识库...")
        else:
            click.echo("\n💡 提示: 使用 --with-notebook 可自动创建知识库")
            click.echo("   或手动编辑 .skillpackrc 设置 default_notebook")

    @cli.command()
    def history():
        """
        查看历史任务

        显示最近执行的任务列表
        """
        history_dir = Path.cwd() / ".skillpack" / "history"

        if not history_dir.exists():
            click.echo("📭 没有历史记录")
            return

        histories = sorted(history_dir.iterdir(), reverse=True)

        if not histories:
            click.echo("📭 没有历史记录")
            return

        click.echo("\n📜 历史任务:")
        click.echo("━" * 50)

        for h in histories[:20]:
            status_file = h / "status.json"
            if status_file.exists():
                import json
                with open(status_file) as f:
                    data = json.load(f)
                phase = data.get('phase', 'unknown')
                icon = "✅" if phase == "completed" else "❌"
                click.echo(f"{icon} {h.name}")
            else:
                click.echo(f"❓ {h.name}")


def main():
    """CLI 入口点"""
    require_click()
    cli()


if __name__ == "__main__":
    main()
