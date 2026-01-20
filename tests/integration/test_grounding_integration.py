"""
Grounding 集成测试

测试 Grounding 机制与其他组件的集成。
"""

import pytest

# 导入测试中定义的类
from tests.test_grounding import (
    Evidence,
    GroundingResult,
    GroundingValidator,
)


@pytest.mark.integration
class TestGroundingWithEvidence:
    """Grounding 与证据集成测试"""

    def test_evidence_to_grounding_result(self, evidence_factory):
        """证据添加到 GroundingResult"""
        result = GroundingResult("测试结论")

        # 添加多个证据
        for i in range(3):
            evidence = evidence_factory(
                file_path=f"src/module_{i}.py",
                line=i + 1,
                code=f"def function_{i}():",
            )
            result.add_evidence(evidence)

        assert len(result.code_evidences) == 3
        assert result.confidence == "high"
        assert result.is_grounded() is True

    def test_mixed_evidence_sources(self, evidence_factory):
        """混合证据源"""
        result = GroundingResult("认证功能分析")

        # 添加代码证据
        result.add_evidence(evidence_factory(
            file_path="src/auth/login.ts",
            line=42,
            code="jwt.sign(payload, secret)",
        ))

        # 添加 NotebookLM 引用
        result.add_notebook_reference("[NB] 认证需求: JWT 验证")

        assert len(result.code_evidences) == 1
        assert len(result.notebook_references) == 1
        assert result.is_grounded() is True


@pytest.mark.integration
class TestGroundingValidation:
    """Grounding 验证集成测试"""

    def test_validate_evidence_format_integration(self):
        """证据格式验证集成"""
        validator = GroundingValidator()

        # 从 Evidence 生成的字符串应该通过验证
        evidence = Evidence("src/auth.py", 42, "jwt.verify(token)")
        evidence_str = str(evidence)

        assert validator.validate_evidence_format(evidence_str) is True

    def test_validate_conclusion_with_grounding_result(self):
        """结论验证与 GroundingResult 集成"""
        validator = GroundingValidator()
        result = GroundingResult("基于代码分析，此模块可能处理用户认证。")

        # 验证结论
        is_valid, violations = validator.validate_conclusion(result.conclusion)

        assert is_valid is True
        assert len(violations) == 0


@pytest.mark.integration
class TestGroundingConfidence:
    """Grounding 置信度集成测试"""

    def test_confidence_progression(self, evidence_factory):
        """置信度递进"""
        result = GroundingResult("测试结论")

        # 初始状态
        assert result.confidence == "low"

        # 添加 1 个证据
        result.add_evidence(evidence_factory())
        assert result.confidence == "low"

        # 添加第 2 个证据
        result.add_evidence(evidence_factory(file_path="other.py", line=2))
        assert result.confidence == "medium"

        # 添加第 3 个证据
        result.add_evidence(evidence_factory(file_path="third.py", line=3))
        assert result.confidence == "high"


@pytest.mark.integration
class TestGroundingUncertainty:
    """Grounding 不确定性声明集成测试"""

    def test_uncertainty_with_evidence(self, grounding_result_factory):
        """不确定性与证据共存"""
        result = grounding_result_factory(
            conclusion="分析结论",
            evidence_count=2,
        )

        result.add_uncertainty("未验证边界条件")
        result.add_uncertainty("缺少性能测试数据")

        assert result.is_grounded() is True
        assert len(result.uncertainties) == 2


@pytest.mark.integration
class TestGroundingWorkflow:
    """Grounding 完整工作流程集成测试"""

    def test_full_grounding_workflow(self, evidence_factory):
        """完整 Grounding 工作流程"""
        # 1. 创建结论
        result = GroundingResult("用户认证功能实现正确")

        # 2. 添加代码证据
        result.add_evidence(evidence_factory(
            file_path="src/auth/login.ts",
            line=15,
            code="async function verifyCredentials(username, password)",
            description="凭据验证入口"
        ))
        result.add_evidence(evidence_factory(
            file_path="src/auth/jwt.ts",
            line=42,
            code="jwt.sign({ userId }, process.env.JWT_SECRET)",
            description="JWT 生成"
        ))

        # 3. 添加 NotebookLM 引用
        result.add_notebook_reference("[NB] 需求文档: 支持 JWT 认证")

        # 4. 添加不确定性声明
        result.add_uncertainty("未测试 token 刷新机制")

        # 5. 验证结论
        validator = GroundingValidator()
        is_valid, violations = validator.validate_conclusion(result.conclusion)

        # 验证结果
        assert is_valid is True
        assert result.is_grounded() is True
        assert result.confidence == "high"
        assert len(result.code_evidences) == 2
        assert len(result.notebook_references) == 1
        assert len(result.uncertainties) == 1


@pytest.mark.integration
class TestGroundingWithRouter:
    """Grounding 与 Router 集成测试"""

    def test_grounding_for_routing_decision(self, evidence_factory):
        """为路由决策提供 Grounding"""
        from skillpack.router import TaskRouter

        router = TaskRouter()

        # 模拟对路由决策的 Grounding
        result = GroundingResult("任务应该路由到 RALPH")

        # 添加代码证据
        result.add_evidence(evidence_factory(
            file_path="task_description",
            line=1,
            code="build complete authentication system",
            description="任务描述包含'complete'和'system'信号"
        ))
        result.add_evidence(evidence_factory(
            file_path="router.py",
            line=35,
            code="'complete': 15, 'system': 20",
            description="复杂度信号定义"
        ))

        # 验证 Grounding
        assert result.is_grounded() is True

        # 实际路由
        context = router.route("build complete authentication system")
        # 应该是复杂路由或 UI 路由 (因为包含可能的 UI 信号)
        assert context.route.value in ["RALPH", "ARCHITECT", "UI_FLOW"]
