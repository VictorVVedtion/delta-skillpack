"""
交叉验证集成测试

测试 v5.4 独立审查者模式和多模型交叉验证的完整流程。
"""

import pytest

# 导入测试中定义的类
from tests.test_cross_validation import (
    ConfidenceLevel,
    ArbitrationDecision,
    ReviewFinding,
    ModelReviewResult,
    Disagreement,
    CrossValidator,
    Arbitrator,
)


@pytest.mark.integration
class TestCrossValidationWorkflow:
    """交叉验证工作流程集成测试"""

    def test_codex_gemini_cross_validation(self):
        """Codex → Gemini 交叉验证"""
        # 1. Codex 实现结果
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="JWT 认证实现完成",
            findings=[],
            coverage_percentage=95.0,
            passed=True,
        )

        # 2. Gemini 独立审查
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="发现缺少 refresh token",
            findings=[
                ReviewFinding(
                    issue="缺少 refresh token 实现",
                    severity="medium",
                    file_path="src/auth/token.ts",
                    line=0,
                    suggestion="实现 refresh token 端点",
                )
            ],
            coverage_percentage=80.0,
            passed=True,
        )

        # 3. 交叉验证
        validator = CrossValidator()
        is_consistent, disagreements = validator.compare_results(
            codex_result, gemini_result
        )

        # 覆盖率差异 15% 应该产生分歧
        assert is_consistent is False
        assert len(disagreements) >= 1

    def test_full_arbitration_workflow(self):
        """完整仲裁工作流程"""
        # 1. 创建冲突的审查结果
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="所有功能已实现",
            coverage_percentage=95.0,
            passed=True,
        )

        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="部分功能缺失",
            coverage_percentage=70.0,
            passed=False,
        )

        # 2. 检测分歧
        validator = CrossValidator()
        is_consistent, disagreements = validator.compare_results(
            codex_result, gemini_result
        )

        assert is_consistent is False
        assert len(disagreements) >= 1

        # 3. 仲裁
        arbitrator = Arbitrator()
        for disagreement in disagreements:
            decision, reason = arbitrator.arbitrate(disagreement)
            assert decision is not None
            assert reason != ""


@pytest.mark.integration
class TestArbitrationDecisions:
    """仲裁决策集成测试"""

    def test_coverage_disagreement_decision(self):
        """覆盖率分歧决策"""
        arbitrator = Arbitrator()
        disagreement = Disagreement(
            topic="需求覆盖率",
            first_conclusion="95%",
            second_conclusion="70%",
            first_evidence="代码分析",
            second_evidence="需求对照",
        )

        decision, reason = arbitrator.arbitrate(disagreement)

        # 应该采用保守估计 (第二个)
        assert decision == ArbitrationDecision.ACCEPT_SECOND

    def test_decision_with_notebook_evidence(self):
        """带 NotebookLM 证据的决策"""
        arbitrator = Arbitrator()
        disagreement = Disagreement(
            topic="功能实现",
            first_conclusion="已实现",
            second_conclusion="未实现",
            first_evidence="代码存在",
            second_evidence="测试未通过",
        )

        # 提供 NotebookLM 证据
        decision, reason = arbitrator.arbitrate(
            disagreement,
            additional_evidence="[NB] 需求 v2.1: 此功能在新版本中已移除",
        )

        assert decision == ArbitrationDecision.ACCEPT_FIRST


@pytest.mark.integration
class TestCriticalIssueHandling:
    """严重问题处理集成测试"""

    def test_critical_issue_triggers_arbitration(self, model_review_result_factory):
        """严重问题触发仲裁"""
        codex_result = model_review_result_factory(
            model_name="Codex",
            coverage_percentage=95.0,
            passed=True,
        )

        gemini_result = model_review_result_factory(
            model_name="Gemini",
            findings_count=1,
            has_critical=True,
            coverage_percentage=90.0,
            passed=True,
        )

        validator = CrossValidator()
        needs_arbitration = validator.requires_arbitration(
            codex_result, gemini_result
        )

        assert needs_arbitration is True

    def test_multiple_critical_issues(self, model_review_result_factory):
        """多个严重问题"""
        gemini_result = model_review_result_factory(
            model_name="Gemini",
            findings_count=3,
            has_critical=True,
            coverage_percentage=85.0,
            passed=False,
        )

        assert gemini_result.has_critical_issues() is True
        assert len(gemini_result.findings) == 3


@pytest.mark.integration
class TestCrossValidationWithGrounding:
    """交叉验证与 Grounding 集成测试"""

    def test_grounding_supports_arbitration(self, evidence_factory):
        """Grounding 支持仲裁决策"""
        from tests.test_grounding import GroundingResult

        # 创建支持决策的 Grounding
        result = GroundingResult("Codex 实现正确")

        result.add_evidence(evidence_factory(
            file_path="src/auth/login.ts",
            line=42,
            code="jwt.verify(token, secret)",
        ))
        result.add_evidence(evidence_factory(
            file_path="src/auth/login.ts",
            line=55,
            code="return { userId, role }",
        ))

        # Grounding 可以作为仲裁证据
        assert result.is_grounded() is True
        assert result.confidence == "medium"


@pytest.mark.integration
class TestRALPHCrossValidation:
    """RALPH 路由交叉验证集成测试"""

    def test_ralph_phase_4_review(self, model_review_result_factory):
        """RALPH Phase 4: 独立审查"""
        # Phase 3: Codex 实现
        codex_result = model_review_result_factory(
            model_name="Codex",
            conclusion="实现完成",
            coverage_percentage=90.0,
            passed=True,
        )

        # Phase 4: Gemini 独立审查
        gemini_result = model_review_result_factory(
            model_name="Gemini",
            conclusion="审查通过",
            coverage_percentage=88.0,
            passed=True,
        )

        validator = CrossValidator()
        is_consistent, _ = validator.compare_results(codex_result, gemini_result)

        # 结果一致，无需仲裁
        assert is_consistent is True

    def test_ralph_phase_5_arbitration(self, model_review_result_factory):
        """RALPH Phase 5: 仲裁验证"""
        # 创建需要仲裁的场景
        codex_result = model_review_result_factory(
            model_name="Codex",
            passed=True,
        )

        gemini_result = model_review_result_factory(
            model_name="Gemini",
            coverage_percentage=75.0,  # 低于 80%
            passed=True,
        )

        validator = CrossValidator()
        needs_arbitration = validator.requires_arbitration(
            codex_result, gemini_result
        )

        # 需要 Claude 仲裁
        assert needs_arbitration is True


@pytest.mark.integration
class TestARCHITECTCrossValidation:
    """ARCHITECT 路由交叉验证集成测试"""

    def test_architect_phase_5_review(self, model_review_result_factory):
        """ARCHITECT Phase 5: Gemini 独立审查"""
        # Phase 4: Codex 分阶段实施
        codex_result = model_review_result_factory(
            model_name="Codex",
            conclusion="架构实施完成",
            coverage_percentage=92.0,
            passed=True,
        )

        # Phase 5: Gemini 独立审查
        gemini_result = model_review_result_factory(
            model_name="Gemini",
            conclusion="架构符合设计",
            coverage_percentage=90.0,
            passed=True,
        )

        validator = CrossValidator()
        is_consistent, _ = validator.compare_results(codex_result, gemini_result)

        assert is_consistent is True

    def test_architect_phase_6_arbitration(self):
        """ARCHITECT Phase 6: Claude 仲裁验证"""
        # 模拟 Claude 仲裁
        arbitrator = Arbitrator()
        disagreement = Disagreement(
            topic="架构一致性",
            first_conclusion="完全符合设计",
            second_conclusion="部分偏离",
            first_evidence="代码结构分析",
            second_evidence="设计文档对照",
        )

        decision, reason = arbitrator.arbitrate(disagreement)

        # 应该要求重新检查
        assert decision == ArbitrationDecision.REQUIRE_RECHECK


@pytest.mark.integration
class TestCrossValidationEdgeCases:
    """交叉验证边界情况测试"""

    def test_both_models_fail(self, model_review_result_factory):
        """两个模型都失败"""
        codex_result = model_review_result_factory(
            model_name="Codex",
            passed=False,
        )

        gemini_result = model_review_result_factory(
            model_name="Gemini",
            passed=False,
        )

        validator = CrossValidator()
        is_consistent, _ = validator.compare_results(codex_result, gemini_result)

        # 一致失败
        assert is_consistent is True

    def test_zero_coverage(self, model_review_result_factory):
        """零覆盖率"""
        gemini_result = model_review_result_factory(
            model_name="Gemini",
            coverage_percentage=0.0,
            passed=False,
        )

        validator = CrossValidator()
        needs_arbitration = validator.requires_arbitration(
            model_review_result_factory(passed=True),
            gemini_result,
        )

        assert needs_arbitration is True
