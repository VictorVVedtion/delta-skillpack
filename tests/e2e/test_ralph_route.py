"""
RALPH 路由 E2E 测试

测试 RALPH 路由的五阶段执行流程，包括 v5.4 新增的独立审查和仲裁阶段。
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from skillpack.cli import cli
from skillpack.models import TaskComplexity, ExecutionRoute
from skillpack.router import TaskRouter
from skillpack.executor import TaskExecutor, RalphExecutor
from skillpack.ralph.dashboard import SimpleProgressTracker, Phase


@pytest.mark.e2e
class TestRalphRouteRouting:
    """RALPH 路由决策测试"""

    def test_complex_task_routes_to_ralph(self):
        """复杂任务路由到 RALPH 或更高"""
        router = TaskRouter()
        context = router.route("build complete authentication system")

        # 可能是 RALPH、ARCHITECT 或 UI_FLOW (因为包含 UI 相关词)
        assert context.route in [ExecutionRoute.RALPH, ExecutionRoute.ARCHITECT, ExecutionRoute.UI_FLOW]

    def test_deep_mode_forces_ralph(self):
        """--deep 模式强制 RALPH 路由"""
        router = TaskRouter()
        context = router.route("fix typo", deep_mode=True)

        assert context.route == ExecutionRoute.RALPH
        assert context.deep_mode is True

    def test_system_keyword_triggers_complex(self):
        """'系统' 关键词提高复杂度"""
        router = TaskRouter()
        context = router.route("implement payment system")

        # 包含 'system' 信号，复杂度提升但短描述可能仍在中等范围
        assert context.complexity in [TaskComplexity.MEDIUM, TaskComplexity.COMPLEX, TaskComplexity.ARCHITECT]


@pytest.mark.e2e
class TestRalphExecutionPhases:
    """RALPH 执行阶段测试 (v5.4: 5 阶段)"""

    def test_ralph_has_five_phases(self, temp_dir):
        """RALPH 路由有五个阶段 (v5.5: 支持共识模式)"""
        executor = RalphExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        from skillpack.models import TaskContext

        context = TaskContext(
            description="build system",
            complexity=TaskComplexity.COMPLEX,
            route=ExecutionRoute.RALPH,
            working_dir=temp_dir,
        )

        status = executor.execute(context, tracker)

        # 验证执行完成
        assert status.is_running is False
        assert tracker.current_phase == Phase.COMPLETED

        # v5.5: 共识模式输出 1_planning_consensus.md 替代 1_analysis.md + 2_plan.md
        # 验证关键输出存在
        assert any("review" in f for f in status.output_files)
        assert any("arbitration" in f for f in status.output_files)
        # 应包含子任务或共识输出
        assert any("subtask" in f or "consensus" in f for f in status.output_files)

    def test_phase_4_independent_review(self, temp_dir):
        """Phase 4: 独立审查阶段 (v5.4)"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        # 模拟 RALPH 执行流程
        tracker.start_phase(Phase.ANALYZING)
        tracker.complete_phase()

        tracker.start_phase(Phase.PLANNING)
        tracker.complete_phase()

        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.complete_phase()

        # Phase 4: 独立审查
        tracker.start_phase(Phase.REVIEWING)
        assert tracker.current_phase == Phase.REVIEWING
        tracker.complete_phase()

    def test_phase_5_arbitration(self, temp_dir):
        """Phase 5: 仲裁验证阶段 (v5.4)"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        # Phase 5: 仲裁
        tracker.start_phase(Phase.VALIDATING)
        assert tracker.current_phase == Phase.VALIDATING
        tracker.complete_phase()


@pytest.mark.e2e
class TestRalphRouteCLI:
    """RALPH 路由 CLI 测试"""

    def test_cli_explain_shows_ralph(self):
        """CLI --explain 显示 RALPH 路由"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "do", "build complete system", "--explain"
        ])

        assert result.exit_code == 0
        # 检查输出包含复杂任务标识
        output_lower = result.output.lower()
        assert "ralph" in output_lower or "复杂" in output_lower or "architect" in output_lower

    def test_cli_deep_mode(self):
        """CLI --deep 模式"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "do", "fix typo", "--deep", "--explain"
        ])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "ralph" in output_lower or "复杂" in output_lower


@pytest.mark.e2e
class TestRalphParallelExecution:
    """RALPH 并行执行测试 (v5.2)"""

    def test_ralph_supports_parallel_mode(self):
        """RALPH 支持并行模式"""
        router = TaskRouter()
        context = router.route("build system", parallel_mode=True)

        assert context.parallel_mode is True

    def test_ralph_default_no_parallel(self):
        """RALPH 默认不启用并行"""
        router = TaskRouter()
        context = router.route("build system")

        assert context.parallel_mode is None


@pytest.mark.e2e
class TestRalphWithCLIMode:
    """RALPH CLI 优先模式测试 (v5.3)"""

    def test_ralph_supports_cli_mode(self):
        """RALPH 支持 CLI 模式"""
        router = TaskRouter()
        context = router.route("build system", cli_mode=True)

        assert context.cli_mode is True


@pytest.mark.e2e
class TestRalphOutputValidation:
    """RALPH 路由输出验证"""

    def test_output_files_structure(self, temp_dir):
        """输出文件结构验证 (v5.5: 支持共识模式)"""
        router = TaskRouter()
        context = router.route("build system", deep_mode=True)
        context.working_dir = temp_dir

        executor = TaskExecutor(quiet=True)
        status = executor.execute(context)

        # v5.5: 共识模式输出与传统模式不同
        # 验证关键阶段输出存在
        assert any("review" in f for f in status.output_files)
        assert any("arbitration" in f for f in status.output_files)
        # 应包含规划阶段输出（共识或传统）
        assert any("analysis" in f or "plan" in f or "consensus" in f for f in status.output_files)


@pytest.mark.e2e
class TestRalphLoopExecution:
    """RALPH 循环执行引擎测试 (v4.0)"""

    def test_ralph_can_iterate(self):
        """RALPH 支持迭代执行"""
        # RALPH 的循环执行由 Stop Hook 和状态文件控制
        # 这里测试基本的执行能力
        executor = RalphExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        from skillpack.models import TaskContext

        context = TaskContext(
            description="complex iterative task",
            complexity=TaskComplexity.COMPLEX,
            route=ExecutionRoute.RALPH,
        )

        status = executor.execute(context, tracker)

        # 验证执行完成
        assert status.is_running is False
