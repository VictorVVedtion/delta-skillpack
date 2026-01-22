"""
PLANNED 路由 E2E 测试

测试 PLANNED 路由的三阶段执行流程。
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from skillpack.cli import cli
from skillpack.models import TaskComplexity, ExecutionRoute
from skillpack.router import TaskRouter
from skillpack.executor import TaskExecutor, PlannedExecutor
from skillpack.ralph.dashboard import SimpleProgressTracker, Phase


@pytest.mark.e2e
class TestPlannedRouteRouting:
    """PLANNED 路由决策测试"""

    def test_medium_task_routes_to_planned(self):
        """中等复杂度任务路由到 PLANNED"""
        router = TaskRouter()
        context = router.route("add user authentication")

        assert context.complexity == TaskComplexity.MEDIUM
        assert context.route == ExecutionRoute.PLANNED

    def test_feature_request_routes_to_planned(self):
        """功能请求路由到 PLANNED"""
        router = TaskRouter()
        context = router.route("implement login validation")

        assert context.route == ExecutionRoute.PLANNED

    def test_score_in_planned_range(self):
        """评分在 PLANNED 范围内 (21-45)"""
        router = TaskRouter()
        context = router.route("add user authentication")

        if context.score_card:
            total = context.score_card.total
            assert 21 <= total <= 45


@pytest.mark.e2e
class TestPlannedExecutionPhases:
    """PLANNED 执行阶段测试"""

    def test_planned_has_three_phases(self, temp_dir):
        """PLANNED 路由有三个阶段 (v5.5: 支持共识模式)"""
        executor = PlannedExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        from skillpack.models import TaskContext

        context = TaskContext(
            description="add feature",
            complexity=TaskComplexity.MEDIUM,
            route=ExecutionRoute.PLANNED,
            working_dir=temp_dir,
        )

        status = executor.execute(context, tracker)

        # 验证执行完成
        assert status.is_running is False
        assert tracker.current_phase == Phase.COMPLETED

        # 验证输出文件 (v5.5: 共识模式输出 1_planning_consensus.md)
        # 旧模式: ["1_plan.md", "2_implementation.md", "3_review.md"]
        # 新模式: ["1_planning_consensus.md", "2_implementation.md", "3_review.md"]
        assert len(status.output_files) >= 3
        # 应包含实现和审查阶段
        assert any("implementation" in f for f in status.output_files)
        assert any("review" in f for f in status.output_files)

    def test_phase_progression(self, temp_dir):
        """阶段进度正确推进"""
        tracker = SimpleProgressTracker("test", "Test", quiet=True)

        # 记录阶段事件
        phases_seen = []

        tracker.start_phase(Phase.PLANNING)
        phases_seen.append(tracker.current_phase)

        tracker.start_phase(Phase.IMPLEMENTING)
        phases_seen.append(tracker.current_phase)

        tracker.start_phase(Phase.REVIEWING)
        phases_seen.append(tracker.current_phase)

        assert Phase.PLANNING in phases_seen
        assert Phase.IMPLEMENTING in phases_seen
        assert Phase.REVIEWING in phases_seen


@pytest.mark.e2e
class TestPlannedRouteCLI:
    """PLANNED 路由 CLI 测试"""

    def test_cli_explain_shows_planned(self):
        """CLI --explain 显示 PLANNED 路由"""
        runner = CliRunner()
        result = runner.invoke(cli, ["do", "add user authentication", "--explain"])

        assert result.exit_code == 0
        # 检查输出包含 PLANNED 或计划执行
        output_lower = result.output.lower()
        assert "planned" in output_lower or "计划" in output_lower

    def test_cli_execute_planned_task(self):
        """CLI 执行 PLANNED 任务"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["do", "add feature", "--quiet"])

            assert result.exit_code == 0


@pytest.mark.e2e
class TestPlannedRouteOutputValidation:
    """PLANNED 路由输出验证"""

    def test_output_files_structure(self, temp_dir):
        """输出文件结构验证 (v5.5: 支持共识模式)"""
        router = TaskRouter()
        context = router.route("add feature")
        context.working_dir = temp_dir

        executor = TaskExecutor(quiet=True)
        status = executor.execute(context)

        # 验证输出文件存在
        # v5.5: 共识模式输出 1_planning_consensus.md
        # 旧模式: ["1_plan.md", "2_implementation.md", "3_review.md"]
        # 新模式: ["1_planning_consensus.md", "2_implementation.md", "3_review.md"]
        assert len(status.output_files) >= 3
        # 验证包含规划阶段输出（共识或传统）
        assert any("plan" in f.lower() or "consensus" in f.lower() for f in status.output_files)
        assert any("implementation" in f for f in status.output_files)
        assert any("review" in f for f in status.output_files)


@pytest.mark.e2e
class TestPlannedWithNotebook:
    """PLANNED 路由与知识库集成测试"""

    def test_notebook_id_passed_through(self):
        """知识库 ID 传递"""
        router = TaskRouter()
        context = router.route("add feature", notebook_id="test-notebook")

        assert context.notebook_id == "test-notebook"
        assert context.route == ExecutionRoute.PLANNED
