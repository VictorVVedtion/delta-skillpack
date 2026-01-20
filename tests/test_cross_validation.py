"""
交叉验证机制测试

测试 v5.4 的独立审查者模式和多模型交叉验证。
"""

import pytest
from enum import Enum
from dataclasses import dataclass, field


class ConfidenceLevel(Enum):
    """置信度等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ArbitrationDecision(Enum):
    """仲裁决定"""
    ACCEPT_FIRST = "accept_first"
    ACCEPT_SECOND = "accept_second"
    MERGE = "merge"
    REQUIRE_RECHECK = "require_recheck"


@dataclass
class ReviewFinding:
    """审查发现"""
    issue: str
    severity: str  # high, medium, low
    file_path: str
    line: int
    suggestion: str
    
    def is_critical(self) -> bool:
        return self.severity == "high"


@dataclass
class ModelReviewResult:
    """模型审查结果"""
    model_name: str
    conclusion: str
    findings: list[ReviewFinding] = field(default_factory=list)
    coverage_percentage: float = 0.0
    passed: bool = False
    
    def has_critical_issues(self) -> bool:
        return any(f.is_critical() for f in self.findings)


@dataclass  
class Disagreement:
    """分歧记录"""
    topic: str
    first_conclusion: str
    second_conclusion: str
    first_evidence: str
    second_evidence: str


class CrossValidator:
    """交叉验证器"""
    
    def __init__(self):
        self.disagreements: list[Disagreement] = []
    
    def compare_results(
        self, 
        codex_result: ModelReviewResult, 
        gemini_result: ModelReviewResult
    ) -> tuple[bool, list[Disagreement]]:
        """比较两个模型的审查结果"""
        self.disagreements = []
        
        # 检查通过状态是否一致
        if codex_result.passed != gemini_result.passed:
            self.disagreements.append(Disagreement(
                topic="审查通过状态",
                first_conclusion=f"Codex: {'通过' if codex_result.passed else '未通过'}",
                second_conclusion=f"Gemini: {'通过' if gemini_result.passed else '未通过'}",
                first_evidence=codex_result.conclusion,
                second_evidence=gemini_result.conclusion
            ))
        
        # 检查覆盖率差异
        coverage_diff = abs(codex_result.coverage_percentage - gemini_result.coverage_percentage)
        if coverage_diff > 10:  # 差异超过10%
            self.disagreements.append(Disagreement(
                topic="需求覆盖率",
                first_conclusion=f"Codex: {codex_result.coverage_percentage}%",
                second_conclusion=f"Gemini: {gemini_result.coverage_percentage}%",
                first_evidence="基于代码静态分析",
                second_evidence="基于需求文档对照"
            ))
        
        is_consistent = len(self.disagreements) == 0
        return is_consistent, self.disagreements
    
    def requires_arbitration(
        self, 
        codex_result: ModelReviewResult, 
        gemini_result: ModelReviewResult
    ) -> bool:
        """判断是否需要仲裁"""
        is_consistent, _ = self.compare_results(codex_result, gemini_result)
        
        if not is_consistent:
            return True
        
        # 发现严重问题需要仲裁
        if gemini_result.has_critical_issues():
            return True
        
        # 覆盖率低于80%需要仲裁
        if gemini_result.coverage_percentage < 80:
            return True
        
        return False


class Arbitrator:
    """仲裁者"""
    
    def arbitrate(
        self, 
        disagreement: Disagreement,
        additional_evidence: str = ""
    ) -> tuple[ArbitrationDecision, str]:
        """仲裁分歧"""
        # 简化的仲裁逻辑，实际中由 Claude 执行
        if "覆盖率" in disagreement.topic:
            # 覆盖率分歧，采用保守估计
            return ArbitrationDecision.ACCEPT_SECOND, "采用较低的覆盖率估计，更保守"
        
        if additional_evidence:
            # 有额外证据时，验证后决定
            return ArbitrationDecision.ACCEPT_FIRST, f"基于额外证据: {additional_evidence}"
        
        # 默认需要重新检查
        return ArbitrationDecision.REQUIRE_RECHECK, "证据不足，需要重新审查"


class TestReviewFinding:
    """测试 ReviewFinding"""
    
    def test_critical_issue(self):
        """高严重性问题应该被标记为关键"""
        finding = ReviewFinding(
            issue="SQL 注入漏洞",
            severity="high",
            file_path="src/db.py",
            line=42,
            suggestion="使用参数化查询"
        )
        assert finding.is_critical() is True
    
    def test_non_critical_issue(self):
        """低严重性问题不是关键问题"""
        finding = ReviewFinding(
            issue="变量命名不规范",
            severity="low",
            file_path="src/utils.py",
            line=10,
            suggestion="使用 snake_case"
        )
        assert finding.is_critical() is False


class TestModelReviewResult:
    """测试 ModelReviewResult"""
    
    def test_has_no_critical_issues(self):
        """无高严重性问题时返回False"""
        result = ModelReviewResult(
            model_name="Codex",
            conclusion="代码质量良好",
            findings=[
                ReviewFinding("小问题", "low", "test.py", 1, "建议")
            ],
            coverage_percentage=95.0,
            passed=True
        )
        assert result.has_critical_issues() is False
    
    def test_has_critical_issues(self):
        """有高严重性问题时返回True"""
        result = ModelReviewResult(
            model_name="Gemini",
            conclusion="发现安全问题",
            findings=[
                ReviewFinding("安全漏洞", "high", "auth.py", 10, "修复")
            ],
            coverage_percentage=80.0,
            passed=False
        )
        assert result.has_critical_issues() is True


class TestCrossValidator:
    """测试 CrossValidator"""
    
    def test_consistent_results(self):
        """一致的结果不应该产生分歧"""
        validator = CrossValidator()
        
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="实现符合需求",
            coverage_percentage=90.0,
            passed=True
        )
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="需求覆盖完整",
            coverage_percentage=88.0,
            passed=True
        )
        
        is_consistent, disagreements = validator.compare_results(codex_result, gemini_result)
        assert is_consistent is True
        assert len(disagreements) == 0
    
    def test_inconsistent_pass_status(self):
        """通过状态不一致应该产生分歧"""
        validator = CrossValidator()
        
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="实现完成",
            passed=True
        )
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="存在问题",
            passed=False
        )
        
        is_consistent, disagreements = validator.compare_results(codex_result, gemini_result)
        assert is_consistent is False
        assert len(disagreements) == 1
        assert disagreements[0].topic == "审查通过状态"
    
    def test_significant_coverage_difference(self):
        """覆盖率差异超过10%应该产生分歧"""
        validator = CrossValidator()
        
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="覆盖完整",
            coverage_percentage=95.0,
            passed=True
        )
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="覆盖不足",
            coverage_percentage=75.0,
            passed=True
        )
        
        is_consistent, disagreements = validator.compare_results(codex_result, gemini_result)
        assert is_consistent is False
        assert any(d.topic == "需求覆盖率" for d in disagreements)
    
    def test_requires_arbitration_on_disagreement(self):
        """有分歧时应该需要仲裁"""
        validator = CrossValidator()
        
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="通过",
            passed=True
        )
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="不通过",
            passed=False
        )
        
        assert validator.requires_arbitration(codex_result, gemini_result) is True
    
    def test_requires_arbitration_on_critical_issues(self):
        """有严重问题时应该需要仲裁"""
        validator = CrossValidator()
        
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="通过",
            coverage_percentage=90.0,
            passed=True
        )
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="发现问题",
            findings=[
                ReviewFinding("安全问题", "high", "auth.py", 1, "修复")
            ],
            coverage_percentage=90.0,
            passed=True  # 即使通过，有严重问题也需仲裁
        )
        
        assert validator.requires_arbitration(codex_result, gemini_result) is True
    
    def test_requires_arbitration_on_low_coverage(self):
        """覆盖率低于80%应该需要仲裁"""
        validator = CrossValidator()
        
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="通过",
            coverage_percentage=90.0,
            passed=True
        )
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="覆盖不足",
            coverage_percentage=75.0,
            passed=True
        )
        
        assert validator.requires_arbitration(codex_result, gemini_result) is True


class TestArbitrator:
    """测试 Arbitrator"""
    
    def test_coverage_disagreement_takes_conservative(self):
        """覆盖率分歧应该采用保守估计"""
        arbitrator = Arbitrator()
        disagreement = Disagreement(
            topic="需求覆盖率",
            first_conclusion="Codex: 95%",
            second_conclusion="Gemini: 75%",
            first_evidence="代码分析",
            second_evidence="需求对照"
        )
        
        decision, reason = arbitrator.arbitrate(disagreement)
        assert decision == ArbitrationDecision.ACCEPT_SECOND
    
    def test_with_additional_evidence(self):
        """有额外证据应该据此决定"""
        arbitrator = Arbitrator()
        disagreement = Disagreement(
            topic="功能实现",
            first_conclusion="已实现",
            second_conclusion="未实现",
            first_evidence="代码",
            second_evidence="需求"
        )
        
        decision, reason = arbitrator.arbitrate(
            disagreement,
            additional_evidence="NotebookLM 确认需求 v2.1 更新"
        )
        assert decision == ArbitrationDecision.ACCEPT_FIRST
    
    def test_without_sufficient_evidence(self):
        """证据不足应该要求重新检查"""
        arbitrator = Arbitrator()
        disagreement = Disagreement(
            topic="代码质量",
            first_conclusion="良好",
            second_conclusion="待改进",
            first_evidence="代码",
            second_evidence="标准"
        )
        
        decision, reason = arbitrator.arbitrate(disagreement)
        assert decision == ArbitrationDecision.REQUIRE_RECHECK


class TestCrossValidationIntegration:
    """交叉验证集成测试"""
    
    def test_full_cross_validation_workflow(self):
        """测试完整的交叉验证工作流程"""
        # 1. 模拟 Codex 实现结果
        codex_result = ModelReviewResult(
            model_name="Codex",
            conclusion="JWT 认证实现完成，token 有效期 24 小时",
            findings=[],
            coverage_percentage=95.0,
            passed=True
        )
        
        # 2. 模拟 Gemini 独立审查结果
        gemini_result = ModelReviewResult(
            model_name="Gemini",
            conclusion="需求覆盖率 75%，缺少 refresh token 实现",
            findings=[
                ReviewFinding(
                    issue="缺少 refresh token 机制",
                    severity="medium",
                    file_path="src/auth/token.ts",
                    line=0,
                    suggestion="实现 refresh token 端点"
                )
            ],
            coverage_percentage=75.0,
            passed=False
        )
        
        # 3. 交叉验证
        validator = CrossValidator()
        is_consistent, disagreements = validator.compare_results(codex_result, gemini_result)
        
        assert is_consistent is False
        assert validator.requires_arbitration(codex_result, gemini_result) is True
        
        # 4. 仲裁
        arbitrator = Arbitrator()
        for disagreement in disagreements:
            decision, reason = arbitrator.arbitrate(disagreement)
            assert decision is not None
            assert reason != ""
