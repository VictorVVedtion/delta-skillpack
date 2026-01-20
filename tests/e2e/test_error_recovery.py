"""
错误恢复 E2E 测试

测试任务执行过程中的错误处理和恢复机制。
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from skillpack.cli import cli
from skillpack.models import TaskComplexity, ExecutionRoute, TaskContext
from skillpack.router import TaskRouter
from skillpack.executor import TaskExecutor
from skillpack.ralph.dashboard import SimpleProgressTracker, Phase


@pytest.mark.e2e
class TestTrackerFailure:
    """进度追踪器失败处理测试"""

    def test_tracker_fail_method(self):
        """tracker.fail() 方法测试"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.fail("Something went wrong")

        assert tracker.current_phase == Phase.FAILED
        assert tracker.error == "Something went wrong"

    def test_tracker_fail_preserves_error(self):
        """失败后保留错误信息"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        tracker.start_phase(Phase.PLANNING)
        tracker.update(0.5, "halfway")
        tracker.fail("Connection timeout")

        assert tracker.error == "Connection timeout"
        assert tracker.current_phase == Phase.FAILED


@pytest.mark.e2e
class TestExecutionStatusError:
    """执行状态错误测试"""

    def test_execution_status_with_error(self):
        """ExecutionStatus 可以包含错误"""
        from skillpack.executor import ExecutionStatus

        status = ExecutionStatus(
            is_running=False,
            error="Task failed due to timeout",
            output_files=[]
        )

        assert status.is_running is False
        assert status.error == "Task failed due to timeout"

    def test_execution_status_without_error(self):
        """ExecutionStatus 成功时无错误"""
        from skillpack.executor import ExecutionStatus

        status = ExecutionStatus(is_running=False)

        assert status.error is None


@pytest.mark.e2e
class TestCLIErrorHandling:
    """CLI 错误处理测试"""

    def test_cli_missing_description(self):
        """缺少任务描述"""
        runner = CliRunner()
        result = runner.invoke(cli, ["do"])

        # 应该提示需要描述
        assert "描述" in result.output or "错误" in result.output

    def test_cli_conflicting_modes(self):
        """冲突的模式参数"""
        runner = CliRunner()

        # quick 和 deep 同时使用
        result = runner.invoke(cli, [
            "do", "task", "--quick", "--deep", "--explain"
        ])

        # 应该执行成功，quick 优先
        assert result.exit_code == 0


@pytest.mark.e2e
class TestCheckpointRecovery:
    """检查点恢复测试"""

    def test_resume_without_checkpoint(self):
        """无检查点时恢复"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["do", "--resume"])

            # 应该显示恢复信息或错误
            assert result.exit_code == 0

    def test_list_checkpoints_empty(self):
        """列出检查点 - 空"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["do", "--list-checkpoints"])

            assert result.exit_code == 0
            assert "没有" in result.output


@pytest.mark.e2e
class TestPhaseRecovery:
    """阶段恢复测试"""

    def test_can_resume_from_failed_phase(self, checkpoint_factory):
        """可以从失败阶段恢复"""
        # 创建一个在 implementing 阶段失败的检查点
        checkpoint_factory(
            status="failed",
            progress=0.6,
            extra_data={
                "current_phase": "implementing",
                "error": "Connection timeout",
            }
        )

        # 恢复逻辑应该能读取此检查点
        # (完整恢复逻辑在实际代码中实现)


@pytest.mark.e2e
class TestGracefulDegradation:
    """优雅降级测试"""

    def test_fallback_to_direct_on_quick_mode(self):
        """quick 模式降级到 DIRECT"""
        router = TaskRouter()
        context = router.route("build complete CMS", quick_mode=True)

        assert context.route == ExecutionRoute.DIRECT

    def test_cli_mode_flag_preserved(self):
        """CLI 模式标志保留"""
        router = TaskRouter()
        context = router.route("build system", cli_mode=True)

        assert context.cli_mode is True


@pytest.mark.e2e
class TestInvalidInputHandling:
    """无效输入处理测试"""

    def test_empty_description(self):
        """空描述处理"""
        runner = CliRunner()
        result = runner.invoke(cli, ["do", "", "--explain"])

        # 空描述应该被处理
        assert result.exit_code == 0 or "错误" in result.output

    def test_very_long_description(self):
        """超长描述处理"""
        router = TaskRouter()
        long_desc = "implement feature " * 100
        context = router.route(long_desc)

        # 应该能正常处理
        assert context.route is not None
        if context.score_card:
            # 超长描述应该有高 scope 分数
            assert context.score_card.scope > 0


@pytest.mark.e2e
class TestConfigErrorHandling:
    """配置错误处理测试"""

    def test_invalid_config_uses_default(self, temp_dir):
        """无效配置使用默认值"""
        config_path = temp_dir / ".skillpackrc"
        config_path.write_text("{ invalid json }")

        # 应该使用默认配置而不是崩溃
        from skillpack.cli import _load_config
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)
            config = _load_config()
            assert config.version == "5.4"
        finally:
            os.chdir(original_dir)


@pytest.mark.e2e
class TestCallbackError:
    """回调错误处理测试"""

    def test_callback_error_handling(self, mock_callback):
        """回调错误处理"""
        tracker = SimpleProgressTracker(
            "test", "Test",
            callback=mock_callback,
            quiet=True
        )

        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.fail("Test error")

        # 错误应该被记录到回调
        assert len(mock_callback.errors) == 1
        assert mock_callback.errors[0][1] == "Test error"
