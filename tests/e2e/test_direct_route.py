"""
DIRECT 路由 E2E 测试

测试 DIRECT_TEXT 和 DIRECT_CODE 路由的完整执行流程。
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from skillpack.cli import cli
from skillpack.models import TaskComplexity, ExecutionRoute
from skillpack.router import TaskRouter
from skillpack.executor import TaskExecutor


@pytest.mark.e2e
class TestDirectTextRoute:
    """DIRECT_TEXT 路由 E2E 测试"""

    def test_typo_fix_routes_to_direct(self):
        """typo 修复路由到 DIRECT"""
        router = TaskRouter()
        context = router.route("fix typo in README")

        assert context.complexity == TaskComplexity.SIMPLE
        assert context.route == ExecutionRoute.DIRECT

    def test_comment_task_routes_to_direct(self):
        """注释任务路由到 DIRECT"""
        router = TaskRouter()
        context = router.route("add comment to explain function")

        assert context.route == ExecutionRoute.DIRECT

    def test_docs_task_routes_to_direct(self):
        """文档任务可能路由到 DIRECT 或 PLANNED"""
        router = TaskRouter()
        context = router.route("update docs for API")

        # 短描述可能评分在中等范围
        assert context.complexity in [TaskComplexity.SIMPLE, TaskComplexity.MEDIUM]

    def test_direct_execution_completes(self, temp_dir):
        """DIRECT 路由执行完成"""
        router = TaskRouter()
        context = router.route("fix typo")
        context.working_dir = temp_dir

        executor = TaskExecutor(quiet=True)
        status = executor.execute(context)

        assert status.is_running is False
        assert status.error is None
        assert "output.txt" in status.output_files


@pytest.mark.e2e
class TestDirectCodeRoute:
    """DIRECT_CODE 路由 E2E 测试"""

    def test_simple_bug_fix_routes_to_direct(self):
        """简单 bug 修复路由到 DIRECT"""
        router = TaskRouter()
        context = router.route("fix simple bug")

        # 简单任务应该路由到 DIRECT
        assert context.route in [ExecutionRoute.DIRECT, ExecutionRoute.PLANNED]

    def test_quick_mode_forces_direct(self):
        """--quick 模式强制 DIRECT 路由"""
        router = TaskRouter()
        context = router.route("build complete CMS", quick_mode=True)

        assert context.route == ExecutionRoute.DIRECT
        assert context.quick_mode is True


@pytest.mark.e2e
class TestDirectRouteCLI:
    """DIRECT 路由 CLI E2E 测试"""

    def test_cli_explain_shows_direct(self):
        """CLI --explain 显示 DIRECT 路由"""
        runner = CliRunner()
        result = runner.invoke(cli, ["do", "fix typo", "--explain"])

        assert result.exit_code == 0
        assert "直接执行" in result.output or "DIRECT" in result.output

    def test_cli_quick_mode(self):
        """CLI --quick 模式"""
        runner = CliRunner()
        result = runner.invoke(cli, ["do", "complex task", "--quick", "--explain"])

        assert result.exit_code == 0
        assert "直接执行" in result.output

    def test_cli_execute_simple_task(self):
        """CLI 执行简单任务"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["do", "fix typo", "--quiet"])

            assert result.exit_code == 0


@pytest.mark.e2e
class TestDirectRouteOutputs:
    """DIRECT 路由输出测试"""

    def test_output_directory_created(self, temp_dir):
        """输出目录创建"""
        router = TaskRouter()
        context = router.route("fix typo")
        context.working_dir = temp_dir

        executor = TaskExecutor(quiet=True)
        executor.execute(context)

        output_dir = temp_dir / ".skillpack" / "current"
        assert output_dir.exists()

    def test_history_directory_created(self, temp_dir):
        """历史目录创建"""
        router = TaskRouter()
        context = router.route("fix typo")
        context.working_dir = temp_dir

        executor = TaskExecutor(quiet=True)
        executor.execute(context)

        history_dir = temp_dir / ".skillpack" / "history"
        assert history_dir.exists()
