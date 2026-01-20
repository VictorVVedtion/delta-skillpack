"""
Grounding 机制测试

测试 v5.4 的 Grounding 机制，确保每个分析结论都有代码证据支撑。
"""

import pytest
from pathlib import Path


class Evidence:
    """代码证据类"""
    
    def __init__(self, file_path: str, line: int, code: str, description: str = ""):
        self.file_path = file_path
        self.line = line
        self.code = code
        self.description = description
    
    def __str__(self) -> str:
        return f"`{self.file_path}:{self.line}` - `{self.code}`"
    
    def is_valid(self) -> bool:
        """验证证据是否有效"""
        return bool(
            self.file_path and 
            self.line > 0 and 
            self.code and 
            not self._is_comment_only()
        )
    
    def _is_comment_only(self) -> bool:
        """检查是否只是注释"""
        stripped = self.code.strip()
        return stripped.startswith('#') or stripped.startswith('//')


class GroundingResult:
    """Grounding 分析结果"""
    
    def __init__(self, conclusion: str):
        self.conclusion = conclusion
        self.code_evidences: list[Evidence] = []
        self.notebook_references: list[str] = []
        self.confidence: str = "low"  # low, medium, high
        self.uncertainties: list[str] = []
    
    def add_evidence(self, evidence: Evidence) -> None:
        if evidence.is_valid():
            self.code_evidences.append(evidence)
            self._update_confidence()
    
    def add_notebook_reference(self, reference: str) -> None:
        self.notebook_references.append(reference)
        self._update_confidence()
    
    def add_uncertainty(self, uncertainty: str) -> None:
        self.uncertainties.append(uncertainty)
    
    def _update_confidence(self) -> None:
        """根据证据数量更新置信度"""
        total_sources = len(self.code_evidences) + len(self.notebook_references)
        if total_sources >= 3:
            self.confidence = "high"
        elif total_sources >= 2:
            self.confidence = "medium"
        else:
            self.confidence = "low"
    
    def is_grounded(self) -> bool:
        """检查结论是否有足够的 grounding"""
        return len(self.code_evidences) >= 2 or (
            len(self.code_evidences) >= 1 and len(self.notebook_references) >= 1
        )


class GroundingValidator:
    """Grounding 验证器"""
    
    PROHIBITED_PATTERNS = [
        "根据文件名",
        "从目录结构看",
        "函数名表明",
        "覆盖率达到 100%",
        "完全符合",
        "一定是",
        "肯定是",
    ]
    
    def validate_conclusion(self, text: str) -> tuple[bool, list[str]]:
        """验证结论是否使用了禁止的模式"""
        violations = []
        for pattern in self.PROHIBITED_PATTERNS:
            if pattern in text:
                violations.append(f"使用了禁止的表述: '{pattern}'")
        return len(violations) == 0, violations
    
    def validate_evidence_format(self, evidence_text: str) -> bool:
        """验证证据格式是否正确: `file:line` - `code`"""
        import re
        pattern = r'`[^`]+:\d+`\s*-\s*`[^`]+`'
        return bool(re.search(pattern, evidence_text))


class TestEvidenceClass:
    """测试 Evidence 类"""
    
    def test_valid_evidence(self):
        """有效证据应该通过验证"""
        evidence = Evidence(
            file_path="src/auth/login.ts",
            line=42,
            code="const token = jwt.sign(payload, secret)",
            description="JWT 生成"
        )
        assert evidence.is_valid() is True
    
    def test_invalid_evidence_no_path(self):
        """无路径的证据应该无效"""
        evidence = Evidence(file_path="", line=42, code="some code")
        assert evidence.is_valid() is False
    
    def test_invalid_evidence_zero_line(self):
        """行号为0的证据应该无效"""
        evidence = Evidence(file_path="test.py", line=0, code="some code")
        assert evidence.is_valid() is False
    
    def test_invalid_evidence_comment_only(self):
        """纯注释的证据应该无效"""
        evidence = Evidence(file_path="test.py", line=10, code="# this is a comment")
        assert evidence.is_valid() is False
    
    def test_evidence_string_format(self):
        """证据字符串格式应该正确"""
        evidence = Evidence(file_path="test.py", line=10, code="print('hello')")
        expected = "`test.py:10` - `print('hello')`"
        assert str(evidence) == expected


class TestGroundingResult:
    """测试 GroundingResult 类"""
    
    def test_confidence_low_with_one_evidence(self):
        """单条证据应该是低置信度"""
        result = GroundingResult("测试结论")
        result.add_evidence(Evidence("test.py", 1, "code"))
        assert result.confidence == "low"
    
    def test_confidence_medium_with_two_evidences(self):
        """两条证据应该是中置信度"""
        result = GroundingResult("测试结论")
        result.add_evidence(Evidence("test.py", 1, "code1"))
        result.add_evidence(Evidence("test.py", 2, "code2"))
        assert result.confidence == "medium"
    
    def test_confidence_high_with_three_evidences(self):
        """三条证据应该是高置信度"""
        result = GroundingResult("测试结论")
        result.add_evidence(Evidence("test.py", 1, "code1"))
        result.add_evidence(Evidence("test.py", 2, "code2"))
        result.add_evidence(Evidence("test.py", 3, "code3"))
        assert result.confidence == "high"
    
    def test_is_grounded_with_two_code_evidences(self):
        """两条代码证据应该满足 grounding"""
        result = GroundingResult("测试结论")
        result.add_evidence(Evidence("test.py", 1, "code1"))
        result.add_evidence(Evidence("test.py", 2, "code2"))
        assert result.is_grounded() is True
    
    def test_is_grounded_with_code_and_notebook(self):
        """一条代码证据加一条 NotebookLM 引用应该满足 grounding"""
        result = GroundingResult("测试结论")
        result.add_evidence(Evidence("test.py", 1, "code1"))
        result.add_notebook_reference("[NB] 需求文档: 功能描述")
        assert result.is_grounded() is True
    
    def test_not_grounded_with_single_evidence(self):
        """单条证据不满足 grounding"""
        result = GroundingResult("测试结论")
        result.add_evidence(Evidence("test.py", 1, "code1"))
        assert result.is_grounded() is False


class TestGroundingValidator:
    """测试 GroundingValidator"""
    
    def test_valid_conclusion(self):
        """合规的结论应该通过验证"""
        validator = GroundingValidator()
        conclusion = "基于代码分析，此函数可能处理用户认证。"
        is_valid, violations = validator.validate_conclusion(conclusion)
        assert is_valid is True
        assert len(violations) == 0
    
    def test_invalid_conclusion_filename_based(self):
        """基于文件名的结论应该被拒绝"""
        validator = GroundingValidator()
        conclusion = "根据文件名 test_e2e.py，这是一个 E2E 测试。"
        is_valid, violations = validator.validate_conclusion(conclusion)
        assert is_valid is False
        assert len(violations) == 1
    
    def test_invalid_conclusion_absolute_claim(self):
        """绝对表述的结论应该被拒绝"""
        validator = GroundingValidator()
        conclusion = "覆盖率达到 100%，完全符合要求。"
        is_valid, violations = validator.validate_conclusion(conclusion)
        assert is_valid is False
        assert len(violations) == 2
    
    def test_valid_evidence_format(self):
        """正确格式的证据应该通过验证"""
        validator = GroundingValidator()
        evidence_text = "`src/auth/login.ts:42` - `const token = jwt.sign()`"
        assert validator.validate_evidence_format(evidence_text) is True
    
    def test_invalid_evidence_format(self):
        """错误格式的证据应该被拒绝"""
        validator = GroundingValidator()
        evidence_text = "login.ts 第42行有 jwt.sign()"
        assert validator.validate_evidence_format(evidence_text) is False


class TestGroundingIntegration:
    """Grounding 集成测试"""
    
    def test_complete_grounding_workflow(self):
        """测试完整的 Grounding 工作流程"""
        # 创建分析结果
        result = GroundingResult("用户认证功能满足 JWT 验证需求")
        
        # 添加代码证据
        result.add_evidence(Evidence(
            file_path="src/auth/login.ts",
            line=15,
            code="async function verifyCredentials()",
            description="凭据验证函数"
        ))
        result.add_evidence(Evidence(
            file_path="src/auth/login.ts",
            line=42,
            code="jwt.sign(payload, SECRET, { expiresIn: '24h' })",
            description="JWT 生成"
        ))
        
        # 添加 NotebookLM 引用
        result.add_notebook_reference("[NB] 用户认证需求: \"支持 JWT 验证，token 有效期 24 小时\"")
        
        # 添加不确定性声明
        result.add_uncertainty("未验证 refresh token 机制")
        
        # 验证
        assert result.is_grounded() is True
        assert result.confidence == "high"
        assert len(result.code_evidences) == 2
        assert len(result.notebook_references) == 1
        assert len(result.uncertainties) == 1
