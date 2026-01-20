"""
数据模型测试

测试 skillpack/models.py 中定义的所有数据模型。
"""

import pytest
from dataclasses import asdict

from skillpack.models import (
    TaskComplexity,
    ExecutionRoute,
    KnowledgeConfig,
    RoutingConfig,
    CheckpointConfig,
    ParallelConfig,
    SkillpackConfig,
    ScoreCard,
    TaskContext,
)


class TestTaskComplexity:
    """TaskComplexity 枚举测试"""

    def test_enum_values(self):
        """验证枚举值定义正确"""
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MEDIUM.value == "medium"
        assert TaskComplexity.COMPLEX.value == "complex"
        assert TaskComplexity.ARCHITECT.value == "architect"
        assert TaskComplexity.UI.value == "ui"

    def test_enum_count(self):
        """验证枚举数量"""
        assert len(TaskComplexity) == 5


class TestExecutionRoute:
    """ExecutionRoute 枚举测试"""

    def test_enum_values(self):
        """验证枚举值定义正确"""
        assert ExecutionRoute.DIRECT.value == "DIRECT"
        assert ExecutionRoute.PLANNED.value == "PLANNED"
        assert ExecutionRoute.RALPH.value == "RALPH"
        assert ExecutionRoute.ARCHITECT.value == "ARCHITECT"
        assert ExecutionRoute.UI_FLOW.value == "UI_FLOW"

    def test_enum_count(self):
        """验证枚举数量"""
        assert len(ExecutionRoute) == 5


class TestKnowledgeConfig:
    """KnowledgeConfig 测试"""

    def test_default_values(self):
        """默认值测试"""
        config = KnowledgeConfig()
        assert config.default_notebook is None
        assert config.auto_query is True

    def test_custom_values(self):
        """自定义值测试"""
        config = KnowledgeConfig(
            default_notebook="my-notebook",
            auto_query=False,
        )
        assert config.default_notebook == "my-notebook"
        assert config.auto_query is False


class TestRoutingConfig:
    """RoutingConfig 测试"""

    def test_default_weights(self):
        """默认权重测试"""
        config = RoutingConfig()
        assert config.weights["scope"] == 25
        assert config.weights["dependency"] == 20
        assert config.weights["technical"] == 20
        assert config.weights["risk"] == 15
        assert config.weights["time"] == 10
        assert config.weights["ui"] == 10

    def test_default_thresholds(self):
        """默认阈值测试"""
        config = RoutingConfig()
        assert config.thresholds["direct"] == 20
        assert config.thresholds["planned"] == 45
        assert config.thresholds["ralph"] == 70

    def test_weights_sum_to_100(self):
        """权重总和应该为 100"""
        config = RoutingConfig()
        total = sum(config.weights.values())
        assert total == 100


class TestCheckpointConfig:
    """CheckpointConfig 测试"""

    def test_default_values(self):
        """默认值测试"""
        config = CheckpointConfig()
        assert config.auto_save is True
        assert config.atomic_writes is True
        assert config.backup_count == 3
        assert config.save_interval_minutes == 5
        assert config.max_history == 10

    def test_custom_values(self):
        """自定义值测试"""
        config = CheckpointConfig(
            auto_save=False,
            atomic_writes=False,
            backup_count=5,
            save_interval_minutes=10,
            max_history=20,
        )
        assert config.auto_save is False
        assert config.atomic_writes is False
        assert config.backup_count == 5
        assert config.save_interval_minutes == 10
        assert config.max_history == 20


class TestParallelConfig:
    """ParallelConfig 测试"""

    def test_default_values(self):
        """默认值测试"""
        config = ParallelConfig()
        assert config.enabled is False
        assert config.max_concurrent_tasks == 3
        assert config.fallback_to_serial_on_failure is True

    def test_custom_values(self):
        """自定义值测试"""
        config = ParallelConfig(
            enabled=True,
            max_concurrent_tasks=5,
            fallback_to_serial_on_failure=False,
        )
        assert config.enabled is True
        assert config.max_concurrent_tasks == 5
        assert config.fallback_to_serial_on_failure is False


class TestSkillpackConfig:
    """SkillpackConfig 测试"""

    def test_default_values(self):
        """默认值测试"""
        config = SkillpackConfig()
        assert config.version == "5.4"
        assert isinstance(config.knowledge, KnowledgeConfig)
        assert isinstance(config.routing, RoutingConfig)
        assert isinstance(config.checkpoint, CheckpointConfig)
        assert isinstance(config.parallel, ParallelConfig)

    def test_nested_config_defaults(self):
        """嵌套配置默认值测试"""
        config = SkillpackConfig()
        # 知识库配置
        assert config.knowledge.default_notebook is None
        assert config.knowledge.auto_query is True
        # 路由配置
        assert config.routing.thresholds["direct"] == 20
        # 检查点配置
        assert config.checkpoint.auto_save is True
        # 并行配置
        assert config.parallel.enabled is False

    def test_custom_nested_config(self):
        """自定义嵌套配置测试"""
        knowledge = KnowledgeConfig(default_notebook="test-nb")
        parallel = ParallelConfig(enabled=True)

        config = SkillpackConfig(
            version="5.5",
            knowledge=knowledge,
            parallel=parallel,
        )

        assert config.version == "5.5"
        assert config.knowledge.default_notebook == "test-nb"
        assert config.parallel.enabled is True


class TestScoreCard:
    """ScoreCard 测试"""

    def test_default_values(self):
        """默认值测试 - 所有维度默认为 0"""
        score = ScoreCard()
        assert score.scope == 0
        assert score.dependency == 0
        assert score.technical == 0
        assert score.risk == 0
        assert score.time == 0
        assert score.ui == 0

    def test_total_calculation(self):
        """总分计算测试"""
        score = ScoreCard(
            scope=10,
            dependency=8,
            technical=6,
            risk=4,
            time=2,
            ui=5,
        )
        assert score.total == 35

    def test_total_max_values(self):
        """最大值总分测试"""
        score = ScoreCard(
            scope=25,
            dependency=20,
            technical=20,
            risk=15,
            time=10,
            ui=10,
        )
        assert score.total == 100

    def test_total_zero_values(self):
        """零值总分测试"""
        score = ScoreCard()
        assert score.total == 0

    def test_total_is_property(self):
        """total 是只读属性"""
        score = ScoreCard(scope=10)
        assert score.total == 10

        # 修改 scope 后 total 应该更新
        score.scope = 20
        assert score.total == 20


class TestScoreCardBoundaries:
    """ScoreCard 边界值测试"""

    @pytest.mark.parametrize("scope", [0, 1, 12, 24, 25])
    def test_scope_boundary(self, scope):
        """scope 边界值 (0-25)"""
        score = ScoreCard(scope=scope)
        assert score.scope == scope

    @pytest.mark.parametrize("dependency", [0, 1, 10, 19, 20])
    def test_dependency_boundary(self, dependency):
        """dependency 边界值 (0-20)"""
        score = ScoreCard(dependency=dependency)
        assert score.dependency == dependency

    @pytest.mark.parametrize("technical", [0, 1, 10, 19, 20])
    def test_technical_boundary(self, technical):
        """technical 边界值 (0-20)"""
        score = ScoreCard(technical=technical)
        assert score.technical == technical

    @pytest.mark.parametrize("risk", [0, 1, 7, 14, 15])
    def test_risk_boundary(self, risk):
        """risk 边界值 (0-15)"""
        score = ScoreCard(risk=risk)
        assert score.risk == risk

    @pytest.mark.parametrize("time", [0, 1, 5, 9, 10])
    def test_time_boundary(self, time):
        """time 边界值 (0-10)"""
        score = ScoreCard(time=time)
        assert score.time == time

    @pytest.mark.parametrize("ui", [0, 1, 5, 9, 10])
    def test_ui_boundary(self, ui):
        """ui 边界值 (0-10)"""
        score = ScoreCard(ui=ui)
        assert score.ui == ui


class TestTaskContext:
    """TaskContext 测试"""

    def test_minimal_creation(self):
        """最小必需参数创建"""
        context = TaskContext(
            description="Test task",
            complexity=TaskComplexity.SIMPLE,
            route=ExecutionRoute.DIRECT,
        )
        assert context.description == "Test task"
        assert context.complexity == TaskComplexity.SIMPLE
        assert context.route == ExecutionRoute.DIRECT

    def test_default_optional_values(self):
        """可选参数默认值测试"""
        context = TaskContext(
            description="Test",
            complexity=TaskComplexity.MEDIUM,
            route=ExecutionRoute.PLANNED,
        )
        assert context.working_dir is None
        assert context.notebook_id is None
        assert context.score_card is None
        assert context.quick_mode is False
        assert context.deep_mode is False
        assert context.parallel_mode is None
        assert context.cli_mode is False

    def test_full_creation(self):
        """完整参数创建测试"""
        from pathlib import Path

        score = ScoreCard(scope=15, dependency=10)
        context = TaskContext(
            description="Complex task",
            complexity=TaskComplexity.COMPLEX,
            route=ExecutionRoute.RALPH,
            working_dir=Path("/tmp/test"),
            notebook_id="test-nb",
            score_card=score,
            quick_mode=False,
            deep_mode=True,
            parallel_mode=True,
            cli_mode=True,
        )

        assert context.description == "Complex task"
        assert context.complexity == TaskComplexity.COMPLEX
        assert context.route == ExecutionRoute.RALPH
        assert context.working_dir == Path("/tmp/test")
        assert context.notebook_id == "test-nb"
        assert context.score_card.total == 25
        assert context.deep_mode is True
        assert context.parallel_mode is True
        assert context.cli_mode is True


class TestTaskContextWithFactory:
    """使用 factory fixture 的 TaskContext 测试"""

    def test_factory_default_values(self, task_context_factory):
        """工厂默认值测试"""
        context = task_context_factory()
        assert context.description == "Test task"
        assert context.complexity == TaskComplexity.MEDIUM
        assert context.route == ExecutionRoute.PLANNED

    def test_factory_custom_values(self, task_context_factory):
        """工厂自定义值测试"""
        context = task_context_factory(
            description="Custom task",
            complexity=TaskComplexity.ARCHITECT,
            route=ExecutionRoute.ARCHITECT,
            notebook_id="custom-nb",
        )
        assert context.description == "Custom task"
        assert context.complexity == TaskComplexity.ARCHITECT
        assert context.route == ExecutionRoute.ARCHITECT
        assert context.notebook_id == "custom-nb"


class TestScoreCardFactory:
    """ScoreCard 工厂 fixture 测试"""

    def test_factory_total_exact(self, score_card_factory):
        """工厂创建指定总分的 ScoreCard"""
        for target_total in [0, 20, 45, 70, 100]:
            score = score_card_factory(target_total)
            # 允许 +/- 1 的误差（由于整数除法）
            assert abs(score.total - target_total) <= 2

    def test_factory_respects_max_limits(self, score_card_factory):
        """工厂创建的 ScoreCard 各维度不超过最大值"""
        score = score_card_factory(100)
        assert score.scope <= 25
        assert score.dependency <= 20
        assert score.technical <= 20
        assert score.risk <= 15
        assert score.time <= 10
        assert score.ui <= 10
