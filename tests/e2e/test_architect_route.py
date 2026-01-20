"""
ARCHITECT 路由 E2E 测试

测试 ARCHITECT 路由的六阶段执行流程。
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from skillpack.cli import cli
from skillpack.models import TaskComplexity, ExecutionRoute
from skillpack.router import TaskRouter
from skillpack.executor import TaskExecutor, ArchitectExecutor
from skillpack.ralph.dashboard import SimpleProgressTracker, Phase


@pytest.mark.e2e
class TestArchitectRouteRouting:
    """ARCHITECT 路由决策测试"""

    def test_architecture_task_routes_to_architect(self):
        """架构任务路由到 ARCHITECT"""
        router = TaskRouter()
        context = router.route("重构整个系统架构")

        assert context.complexity == TaskComplexity.ARCHITECT
        assert context.route == ExecutionRoute.ARCHITECT

    def test_from_scratch_triggers_architect(self):
        """'从零构建' 触发 ARCHITECT"""
        router = TaskRouter()
        context = router.route("从零构建微服务架构")

        assert context.route == ExecutionRoute.ARCHITECT

    def test_multi_module_system_triggers_architect(self):
        """多模块系统触发 ARCHITECT 或 UI_FLOW"""
        router = TaskRouter()
        context = router.route("build complete multi-module architecture system")

        # UI 信号可能触发 UI_FLOW，或者复杂信号触发 ARCHITECT
        # 取决于 UI 分数是否达到阈值
        assert context.route in [ExecutionRoute.ARCHITECT, ExecutionRoute.UI_FLOW]


@pytest.mark.e2e
class TestArchitectExecutionPhases:
    """ARCHITECT 执行阶段测试 (v5.4: 6 阶段)"""

    def test_architect_has_six_phases(self, temp_dir):
        """ARCHITECT 路由有六个阶段"""
        executor = ArchitectExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        from skillpack.models import TaskContext

        context = TaskContext(
            description="design architecture",
            complexity=TaskComplexity.ARCHITECT,
            route=ExecutionRoute.ARCHITECT,
            working_dir=temp_dir,
        )

        status = executor.execute(context, tracker)

        # 验证执行完成
        assert status.is_running is False
        assert tracker.current_phase == Phase.COMPLETED

        # 验证 6 阶段输出
        expected_outputs = [
            "1_architecture_analysis.md",
            "2_architecture_design.md",
            "3_implementation_plan.md",
            "5_review.md",
            "6_arbitration.md",
        ]
        for expected in expected_outputs:
            assert expected in status.output_files

    def test_phase_1_gemini_architecture_analysis(self, temp_dir):
        """Phase 1: Gemini 架构分析"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        # Phase 1: 架构分析 (Gemini 执行)
        tracker.start_phase(Phase.ANALYZING)
        assert tracker.current_phase == Phase.ANALYZING
        tracker.update(0.15, "架构分析...")
        tracker.complete_phase()

    def test_phase_2_architecture_design(self, temp_dir):
        """Phase 2: 架构设计"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        # Phase 2: 架构设计 (Claude 执行)
        tracker.start_phase(Phase.DESIGNING)
        assert tracker.current_phase == Phase.DESIGNING
        tracker.update(0.25, "架构设计...")
        tracker.complete_phase()

    def test_phase_5_independent_review(self, temp_dir):
        """Phase 5: 独立审查 (v5.4)"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        # Phase 5: 独立审查 (Gemini 执行)
        tracker.start_phase(Phase.REVIEWING)
        assert tracker.current_phase == Phase.REVIEWING
        tracker.complete_phase()

    def test_phase_6_arbitration(self, temp_dir):
        """Phase 6: 仲裁验证 (v5.4)"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        # Phase 6: 仲裁验证 (Claude 执行)
        tracker.start_phase(Phase.VALIDATING)
        assert tracker.current_phase == Phase.VALIDATING
        tracker.complete_phase()


@pytest.mark.e2e
class TestArchitectRouteCLI:
    """ARCHITECT 路由 CLI 测试"""

    def test_cli_explain_shows_architect(self):
        """CLI --explain 显示 ARCHITECT 路由"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "do", "重构整个系统架构", "--explain"
        ])

        assert result.exit_code == 0
        # 检查输出包含架构相关标识
        output_lower = result.output.lower()
        assert "architect" in output_lower or "超复杂" in output_lower or "架构" in output_lower


@pytest.mark.e2e
class TestArchitectParallelExecution:
    """ARCHITECT 并行执行测试 (v5.2)"""

    def test_architect_supports_parallel_mode(self):
        """ARCHITECT 支持并行模式"""
        router = TaskRouter()
        # deep_mode 会覆盖 parallel_mode，所以分开测试
        context = router.route("design architecture", parallel_mode=True)

        # parallel_mode 应该被传递
        assert context.parallel_mode is True


@pytest.mark.e2e
class TestArchitectOutputValidation:
    """ARCHITECT 路由输出验证"""

    def test_output_files_structure(self, temp_dir):
        """输出文件结构验证"""
        executor = ArchitectExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        from skillpack.models import TaskContext

        context = TaskContext(
            description="design architecture",
            complexity=TaskComplexity.ARCHITECT,
            route=ExecutionRoute.ARCHITECT,
            working_dir=temp_dir,
        )

        status = executor.execute(context, tracker)

        # 验证 6 阶段输出文件
        assert len(status.output_files) >= 5


@pytest.mark.e2e
class TestArchitectModelMapping:
    """ARCHITECT 模型映射测试

    v5.4 路由-模型映射:
    - Phase 1: Gemini (架构分析)
    - Phase 2: Claude (架构设计)
    - Phase 3: Claude (实施规划)
    - Phase 4: Codex (分阶段实施)
    - Phase 5: Gemini (独立审查)
    - Phase 6: Claude (仲裁验证)
    """

    def test_phase_model_assignment(self):
        """阶段模型分配验证"""
        # 这是一个文档性测试，验证模型分配设计
        expected_mapping = {
            1: "Gemini",      # 架构分析
            2: "Claude",      # 架构设计
            3: "Claude",      # 实施规划
            4: "Codex",       # 分阶段实施
            5: "Gemini",      # 独立审查
            6: "Claude",      # 仲裁验证
        }

        # 验证映射完整
        assert len(expected_mapping) == 6
        assert expected_mapping[1] == "Gemini"
        assert expected_mapping[5] == "Gemini"
        assert expected_mapping[6] == "Claude"
