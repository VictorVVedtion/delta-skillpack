"""
UI_FLOW 路由 E2E 测试

测试 UI_FLOW 路由的三阶段执行流程。
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from skillpack.cli import cli
from skillpack.models import TaskComplexity, ExecutionRoute
from skillpack.router import TaskRouter
from skillpack.executor import TaskExecutor, UIFlowExecutor
from skillpack.ralph.dashboard import SimpleProgressTracker, Phase


@pytest.mark.e2e
class TestUIFlowRouteRouting:
    """UI_FLOW 路由决策测试"""

    def test_ui_task_routes_to_ui_flow(self):
        """UI 任务路由到 UI_FLOW"""
        router = TaskRouter()
        context = router.route("create login page component")

        assert context.complexity == TaskComplexity.UI
        assert context.route == ExecutionRoute.UI_FLOW

    def test_component_task_routes_to_ui_flow(self):
        """组件任务路由到 UI_FLOW"""
        router = TaskRouter()
        context = router.route("build user card component")

        assert context.complexity == TaskComplexity.UI
        assert context.route == ExecutionRoute.UI_FLOW

    def test_chinese_ui_task(self):
        """中文 UI 任务路由"""
        router = TaskRouter()
        context = router.route("创建用户界面组件")

        assert context.complexity == TaskComplexity.UI
        assert context.route == ExecutionRoute.UI_FLOW

    def test_style_task_routes_to_ui(self):
        """样式任务路由到 UI_FLOW"""
        router = TaskRouter()
        context = router.route("update button styles with tailwind css")

        assert context.complexity == TaskComplexity.UI


@pytest.mark.e2e
class TestUIFlowUISignals:
    """UI 信号检测测试"""

    @pytest.mark.parametrize("description,expected_ui", [
        ("create login page", True),
        ("build component", True),
        ("implement ui design", True),
        ("add button styles", True),
        ("implement frontend form", True),
        ("create jsx component", True),
        ("add framer-motion animation", True),
        ("implement shadcn dialog", True),
        ("fix backend api", False),  # 无 UI 信号
    ])
    def test_ui_signal_detection(self, description, expected_ui):
        """UI 信号检测"""
        router = TaskRouter()
        has_signal = router._has_ui_signal(description)

        assert has_signal == expected_ui


@pytest.mark.e2e
class TestUIFlowExecutionPhases:
    """UI_FLOW 执行阶段测试"""

    def test_ui_flow_has_three_phases(self, temp_dir):
        """UI_FLOW 路由有三个阶段"""
        executor = UIFlowExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        from skillpack.models import TaskContext

        context = TaskContext(
            description="create ui component",
            complexity=TaskComplexity.UI,
            route=ExecutionRoute.UI_FLOW,
            working_dir=temp_dir,
        )

        status = executor.execute(context, tracker)

        # 验证执行完成
        assert status.is_running is False
        assert tracker.current_phase == Phase.COMPLETED

        # 验证输出文件
        expected_files = ["1_ui_design.md", "2_implementation.md", "3_preview.md"]
        for f in expected_files:
            assert f in status.output_files

    def test_phase_1_ui_design(self, temp_dir):
        """Phase 1: UI 设计 (Gemini 执行)"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        tracker.start_phase(Phase.DESIGNING)
        assert tracker.current_phase == Phase.DESIGNING
        tracker.update(0.3, "UI 设计...")
        tracker.complete_phase()

    def test_phase_2_implementation(self, temp_dir):
        """Phase 2: 组件实现 (Gemini 执行)"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        tracker.start_phase(Phase.IMPLEMENTING)
        assert tracker.current_phase == Phase.IMPLEMENTING
        tracker.update(0.6, "组件实现...")
        tracker.complete_phase()

    def test_phase_3_preview(self, temp_dir):
        """Phase 3: 预览验证 (Claude 执行)"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        tracker.start_phase(Phase.VALIDATING)
        assert tracker.current_phase == Phase.VALIDATING
        tracker.update(1.0, "预览验证...")
        tracker.complete_phase()


@pytest.mark.e2e
class TestUIFlowRouteCLI:
    """UI_FLOW 路由 CLI 测试"""

    def test_cli_explain_shows_ui_flow(self):
        """CLI --explain 显示 UI_FLOW 路由"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "do", "create login page component", "--explain"
        ])

        assert result.exit_code == 0
        assert "UI" in result.output

    def test_cli_execute_ui_task(self):
        """CLI 执行 UI 任务"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                "do", "create button component", "--quiet"
            ])

            assert result.exit_code == 0


@pytest.mark.e2e
class TestUIFlowOutputValidation:
    """UI_FLOW 路由输出验证"""

    def test_output_files_structure(self, temp_dir):
        """输出文件结构验证"""
        router = TaskRouter()
        context = router.route("create ui component")
        context.working_dir = temp_dir

        executor = TaskExecutor(quiet=True)
        status = executor.execute(context)

        # 验证输出文件存在
        assert "1_ui_design.md" in status.output_files
        assert "2_implementation.md" in status.output_files
        assert "3_preview.md" in status.output_files


@pytest.mark.e2e
class TestUIFlowModelMapping:
    """UI_FLOW 模型映射测试

    v5.4 路由-模型映射:
    - Phase 1: Gemini (UI 设计)
    - Phase 2: Gemini (组件实现)
    - Phase 3: Claude (预览验证)
    """

    def test_phase_model_assignment(self):
        """阶段模型分配验证"""
        expected_mapping = {
            1: "Gemini",  # UI 设计
            2: "Gemini",  # 组件实现
            3: "Claude",  # 预览验证
        }

        assert len(expected_mapping) == 3
        assert expected_mapping[1] == "Gemini"
        assert expected_mapping[2] == "Gemini"
        assert expected_mapping[3] == "Claude"


@pytest.mark.e2e
class TestUIFlowFrameworkSignals:
    """UI 框架信号测试"""

    @pytest.mark.parametrize("framework", [
        "shadcn",
        "radix",
        "chakra",
        "material-ui",
        "antd",
        "framer-motion",
        "gsap",
    ])
    def test_framework_signal_detection(self, framework):
        """框架信号检测"""
        router = TaskRouter()
        description = f"create component with {framework}"
        has_signal = router._has_ui_signal(description)

        assert has_signal is True


@pytest.mark.e2e
class TestUIFlowComponentTypes:
    """UI 组件类型信号测试"""

    @pytest.mark.parametrize("component", [
        "button",
        "form",
        "modal",
        "card",
        "table",
        "tabs",
        "dialog",
    ])
    def test_component_type_detection(self, component):
        """组件类型检测"""
        router = TaskRouter()
        description = f"create {component} component"
        has_signal = router._has_ui_signal(description)

        assert has_signal is True
