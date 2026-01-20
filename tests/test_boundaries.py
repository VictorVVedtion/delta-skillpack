"""
边界值测试

测试所有关键阈值和边界条件，确保路由决策在边界处正确行为。
"""

import pytest

from skillpack.models import (
    TaskComplexity,
    ExecutionRoute,
    ScoreCard,
    SkillpackConfig,
    RoutingConfig,
)
from skillpack.router import TaskRouter


# =============================================================================
# 评分阈值边界测试
# =============================================================================

class TestScoreThresholdBoundaries:
    """评分阈值边界测试

    阈值定义:
    - DIRECT: 0-20
    - PLANNED: 21-45
    - RALPH: 46-70
    - ARCHITECT: 71-100
    """

    @pytest.fixture
    def router(self):
        return TaskRouter()

    # -------------------------------------------------------------------------
    # DIRECT 阈值边界 (<=20)
    # -------------------------------------------------------------------------

    @pytest.mark.boundary
    @pytest.mark.parametrize("total,expected_route", [
        (0, ExecutionRoute.DIRECT),      # 最小值
        (19, ExecutionRoute.DIRECT),     # 阈值 -1
        (20, ExecutionRoute.DIRECT),     # 阈值边界
        (21, ExecutionRoute.PLANNED),    # 阈值 +1
    ])
    def test_direct_threshold(self, score_card_factory, total, expected_route):
        """DIRECT 阈值 20 边界测试"""
        config = SkillpackConfig()
        router = TaskRouter(config)

        # 通过 _determine_route 直接测试阈值逻辑
        complexity, route = router._determine_route(total, "test task")

        assert route == expected_route

    # -------------------------------------------------------------------------
    # PLANNED 阈值边界 (21-45)
    # -------------------------------------------------------------------------

    @pytest.mark.boundary
    @pytest.mark.parametrize("total,expected_route", [
        (44, ExecutionRoute.PLANNED),    # 阈值 -1
        (45, ExecutionRoute.PLANNED),    # 阈值边界
        (46, ExecutionRoute.RALPH),      # 阈值 +1
    ])
    def test_planned_threshold(self, score_card_factory, total, expected_route):
        """PLANNED 阈值 45 边界测试"""
        config = SkillpackConfig()
        router = TaskRouter(config)

        complexity, route = router._determine_route(total, "test task")
        assert route == expected_route

    # -------------------------------------------------------------------------
    # RALPH 阈值边界 (46-70)
    # -------------------------------------------------------------------------

    @pytest.mark.boundary
    @pytest.mark.parametrize("total,expected_route", [
        (69, ExecutionRoute.RALPH),      # 阈值 -1
        (70, ExecutionRoute.RALPH),      # 阈值边界
        (71, ExecutionRoute.ARCHITECT),  # 阈值 +1
        (100, ExecutionRoute.ARCHITECT), # 最大值
    ])
    def test_ralph_threshold(self, score_card_factory, total, expected_route):
        """RALPH 阈值 70 边界测试"""
        config = SkillpackConfig()
        router = TaskRouter(config)

        complexity, route = router._determine_route(total, "test task")
        assert route == expected_route


# =============================================================================
# UI 触发条件边界测试
# =============================================================================

class TestUITriggerBoundaries:
    """UI 路由触发条件边界测试

    UI 路由触发条件:
    1. 包含 UI 信号
    2. UI 分数 >= 2
    """

    @pytest.mark.boundary
    @pytest.mark.parametrize("ui_score,expected_ui_route", [
        (0, False),   # 无 UI 分数
        (1, False),   # 低于阈值
        (2, True),    # 阈值边界
        (3, True),    # 高于阈值
        (10, True),   # 最大值
    ])
    def test_ui_score_threshold(self, ui_score, expected_ui_route):
        """UI 分数阈值 2 边界测试"""
        router = TaskRouter()

        # 构造包含 UI 信号的描述
        description = "create login page component"

        # 计算评分
        score_card = router._calculate_score(description)

        # 手动调整 UI 分数
        score_card.ui = ui_score

        # 检查 UI 路由条件
        has_ui_signal = router._has_ui_signal(description)
        should_route_to_ui = has_ui_signal and score_card.ui >= 2

        assert should_route_to_ui == expected_ui_route

    @pytest.mark.boundary
    @pytest.mark.parametrize("description,expected_has_signal", [
        ("fix bug in auth", False),                     # 无 UI 信号
        ("create component", True),                     # 单个 UI 信号
        ("create login page component", True),          # 多个 UI 信号
        ("implement ui with framer-motion", True),      # 多个 UI 信号
        ("fix CSS style in button", True),              # CSS 信号
    ])
    def test_ui_signal_detection(self, description, expected_has_signal):
        """UI 信号检测边界测试"""
        router = TaskRouter()
        has_signal = router._has_ui_signal(description)
        assert has_signal == expected_has_signal


# =============================================================================
# 复杂度信号边界测试
# =============================================================================

class TestComplexitySignalBoundaries:
    """复杂度信号影响边界测试"""

    @pytest.mark.boundary
    def test_simple_signal_accumulation(self):
        """简单信号累积效果测试"""
        router = TaskRouter()

        # 无简单信号
        score_no_signal = router._calculate_score("implement feature")

        # 单个简单信号
        score_one_signal = router._calculate_score("fix typo in feature")

        # 多个简单信号
        score_multi_signal = router._calculate_score("fix typo in readme docs")

        # 简单信号应该降低分数
        assert score_one_signal.total <= score_no_signal.total
        assert score_multi_signal.total <= score_one_signal.total

    @pytest.mark.boundary
    def test_complex_signal_accumulation(self):
        """复杂信号累积效果测试"""
        router = TaskRouter()

        # 无复杂信号
        score_no_signal = router._calculate_score("implement feature")

        # 单个复杂信号
        score_one_signal = router._calculate_score("implement system feature")

        # 多个复杂信号
        score_multi_signal = router._calculate_score("build complete multi-module system architecture")

        # 复杂信号应该提高分数
        assert score_one_signal.total >= score_no_signal.total
        assert score_multi_signal.total >= score_one_signal.total


# =============================================================================
# 置信度边界测试
# =============================================================================

class TestConfidenceBoundaries:
    """置信度阈值边界测试

    置信度规则:
    - low: 0-1 个证据源
    - medium: 2 个证据源
    - high: 3+ 个证据源
    """

    @pytest.mark.boundary
    @pytest.mark.parametrize("evidence_count,notebook_count,expected_confidence", [
        (0, 0, "low"),      # 无证据
        (1, 0, "low"),      # 单个代码证据
        (0, 1, "low"),      # 单个 notebook 引用
        (1, 1, "medium"),   # 1+1=2 证据
        (2, 0, "medium"),   # 2 个代码证据
        (0, 2, "medium"),   # 2 个 notebook 引用
        (2, 1, "high"),     # 2+1=3 证据
        (3, 0, "high"),     # 3 个代码证据
        (0, 3, "high"),     # 3 个 notebook 引用
        (5, 5, "high"),     # 大量证据
    ])
    def test_confidence_thresholds(
        self,
        grounding_result_factory,
        evidence_count,
        notebook_count,
        expected_confidence
    ):
        """置信度阈值边界测试"""
        result = grounding_result_factory(
            conclusion="测试结论",
            evidence_count=evidence_count,
            notebook_ref_count=notebook_count,
        )
        assert result.confidence == expected_confidence


# =============================================================================
# 覆盖率边界测试
# =============================================================================

class TestCoverageBoundaries:
    """覆盖率阈值边界测试

    覆盖率规则:
    - 低于 80%: 需要仲裁
    - 80% 及以上: 通过
    """

    @pytest.mark.boundary
    @pytest.mark.parametrize("coverage,requires_arbitration", [
        (79.0, True),   # 低于阈值
        (79.9, True),   # 略低于阈值
        (80.0, True),   # 阈值边界 - 覆盖率差异超过10%也触发
        (80.1, True),   # 略高于阈值 - 覆盖率差异超过10%也触发
        (84.9, True),   # 覆盖率差异超过10%且<80%
        (85.0, False),  # 覆盖率差异刚好10%不触发 (> 10 才触发)
        (86.0, False),  # 覆盖率差异小于10%且>=80%
        (100.0, False), # 最大值
    ])
    def test_coverage_arbitration_threshold(
        self,
        model_review_result_factory,
        coverage,
        requires_arbitration
    ):
        """覆盖率 80% 和差异 10% 仲裁阈值边界测试"""
        from tests.test_cross_validation import CrossValidator

        validator = CrossValidator()

        codex_result = model_review_result_factory(
            model_name="Codex",
            coverage_percentage=95.0,
            passed=True,
        )
        gemini_result = model_review_result_factory(
            model_name="Gemini",
            coverage_percentage=coverage,
            passed=True,
        )

        needs_arbitration = validator.requires_arbitration(codex_result, gemini_result)
        assert needs_arbitration == requires_arbitration


# =============================================================================
# Grounding 边界测试
# =============================================================================

class TestGroundingBoundaries:
    """Grounding 要求边界测试

    Grounding 规则:
    - 至少 2 个代码证据，或
    - 1 个代码证据 + 1 个 notebook 引用
    """

    @pytest.mark.boundary
    @pytest.mark.parametrize("evidence_count,notebook_count,is_grounded", [
        (0, 0, False),  # 无证据
        (1, 0, False),  # 单个代码证据
        (0, 1, False),  # 单个 notebook 引用
        (0, 2, False),  # 两个 notebook 引用 (不满足)
        (1, 1, True),   # 1 代码 + 1 notebook
        (2, 0, True),   # 2 个代码证据
        (2, 1, True),   # 2 代码 + 1 notebook
        (3, 0, True),   # 3 个代码证据
    ])
    def test_grounding_requirements(
        self,
        grounding_result_factory,
        evidence_count,
        notebook_count,
        is_grounded
    ):
        """Grounding 要求边界测试"""
        result = grounding_result_factory(
            conclusion="测试结论",
            evidence_count=evidence_count,
            notebook_ref_count=notebook_count,
        )
        assert result.is_grounded() == is_grounded


# =============================================================================
# 自定义阈值边界测试
# =============================================================================

class TestCustomThresholdBoundaries:
    """自定义阈值配置边界测试"""

    @pytest.mark.boundary
    def test_custom_direct_threshold(self, router_with_config):
        """自定义 DIRECT 阈值测试"""
        # 设置 DIRECT 阈值为 30
        router = router_with_config(
            thresholds={"direct": 30, "planned": 60, "ralph": 80}
        )

        # 25 分应该是 DIRECT (在新阈值下)
        complexity, route = router._determine_route(25, "test")
        assert route == ExecutionRoute.DIRECT

        # 35 分应该是 PLANNED
        complexity, route = router._determine_route(35, "test")
        assert route == ExecutionRoute.PLANNED

    @pytest.mark.boundary
    def test_extreme_thresholds(self, router_with_config):
        """极端阈值配置测试"""
        # 设置极端阈值
        router = router_with_config(
            thresholds={"direct": 0, "planned": 50, "ralph": 99}
        )

        # 0 分 -> DIRECT (边界)
        complexity, route = router._determine_route(0, "test")
        assert route == ExecutionRoute.DIRECT

        # 1 分 -> PLANNED
        complexity, route = router._determine_route(1, "test")
        assert route == ExecutionRoute.PLANNED

        # 99 分 -> RALPH
        complexity, route = router._determine_route(99, "test")
        assert route == ExecutionRoute.RALPH

        # 100 分 -> ARCHITECT
        complexity, route = router._determine_route(100, "test")
        assert route == ExecutionRoute.ARCHITECT


# =============================================================================
# 描述长度边界测试
# =============================================================================

class TestDescriptionLengthBoundaries:
    """描述长度对评分的影响边界测试"""

    @pytest.mark.boundary
    @pytest.mark.parametrize("word_count,min_expected_scope", [
        (1, 5),    # 单词: base + 1*2 = 7
        (5, 5),    # 五词
        (10, 5),   # 十词
        (15, 25),  # 十五词 (可能达到上限)
    ])
    def test_description_length_impact(self, word_count, min_expected_scope):
        """描述长度对 scope 分数的影响"""
        router = TaskRouter()

        # 构造指定长度的描述
        description = " ".join(["word"] * word_count)
        score = router._calculate_score(description)

        # scope 应该与词数相关，但有上限
        assert score.scope >= min_expected_scope
        assert score.scope <= 25


# =============================================================================
# 进度追踪器边界测试
# =============================================================================

class TestProgressTrackerBoundaries:
    """进度追踪器边界测试"""

    @pytest.mark.boundary
    @pytest.mark.parametrize("progress", [0.0, 0.001, 0.5, 0.999, 1.0])
    def test_progress_boundary_values(self, tracker_factory, progress):
        """进度值边界测试 (0.0-1.0)"""
        from skillpack.ralph.dashboard import Phase

        tracker = tracker_factory()
        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.update(progress, "test")

        assert tracker.current_progress == progress

    @pytest.mark.boundary
    def test_multiple_phase_transitions(self, tracker_factory):
        """多阶段转换边界测试"""
        from skillpack.ralph.dashboard import Phase

        tracker = tracker_factory()

        phases = [
            Phase.ANALYZING,
            Phase.PLANNING,
            Phase.IMPLEMENTING,
            Phase.REVIEWING,
            Phase.VALIDATING,
        ]

        for phase in phases:
            tracker.start_phase(phase)
            assert tracker.current_phase == phase
            tracker.update(0.5, "halfway")
            tracker.complete_phase()
            assert tracker.current_progress == 1.0

        tracker.complete()
        assert tracker.current_phase == Phase.COMPLETED
