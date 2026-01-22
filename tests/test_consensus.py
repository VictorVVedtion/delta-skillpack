"""
测试多模型规划共识模块 (v5.5)
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from skillpack.consensus import (
    ConsensusStatus,
    ApproachType,
    DivergenceLevel,
    Subtask,
    PlanProposal,
    Divergence,
    ArbitrationDecision,
    PlanningConsensus,
    PlanningPromptBuilder,
    ProposalParser,
    ConsensusAnalyzer,
    ConsensusOrchestrator,
    format_consensus_markdown
)
from skillpack.models import SkillpackConfig, ConsensusConfig


class TestSubtask:
    """测试 Subtask 数据类"""

    def test_create_subtask(self):
        task = Subtask(
            id="task-1",
            description="实现用户登录功能",
            priority=1,
            estimated_effort="medium"
        )
        assert task.id == "task-1"
        assert task.priority == 1
        assert task.estimated_effort == "medium"

    def test_subtask_to_dict(self):
        task = Subtask(
            id="task-1",
            description="实现用户登录功能",
            priority=1,
            dependencies=["task-0"],
            files=["src/auth.ts"]
        )
        d = task.to_dict()
        assert d["id"] == "task-1"
        assert d["dependencies"] == ["task-0"]
        assert d["files"] == ["src/auth.ts"]


class TestPlanProposal:
    """测试 PlanProposal 数据类"""

    def test_create_proposal(self):
        proposal = PlanProposal(
            model="codex",
            summary="实现用户认证系统",
            subtasks=[
                Subtask(id="task-1", description="设计数据库模型"),
                Subtask(id="task-2", description="实现 API 端点"),
            ],
            approach=ApproachType.BALANCED,
            rationale="平衡安全性和开发效率",
            confidence=0.85
        )
        assert proposal.model == "codex"
        assert len(proposal.subtasks) == 2
        assert proposal.confidence == 0.85

    def test_proposal_to_dict(self):
        proposal = PlanProposal(
            model="claude",
            summary="测试方案",
            subtasks=[Subtask(id="task-1", description="任务1")],
            approach=ApproachType.CONSERVATIVE,
            rationale="保守策略",
            risks=["风险1"],
            confidence=0.9
        )
        d = proposal.to_dict()
        assert d["model"] == "claude"
        assert d["approach"] == "conservative"
        assert len(d["subtasks"]) == 1


class TestProposalParser:
    """测试提案解析器"""

    def test_parse_valid_json(self):
        """测试解析有效的 JSON 输出"""
        output = '''```json
{
    "summary": "实现用户认证",
    "approach": "balanced",
    "subtasks": [
        {"id": "task-1", "description": "设计数据库", "priority": 1}
    ],
    "risks": ["安全风险"],
    "rationale": "平衡方案",
    "confidence": 0.85
}
```'''
        proposal = ProposalParser.parse(output, "codex")
        assert proposal.model == "codex"
        assert proposal.summary == "实现用户认证"
        assert proposal.approach == ApproachType.BALANCED
        assert len(proposal.subtasks) == 1
        assert proposal.parse_success is True

    def test_parse_json_without_markdown(self):
        """测试解析没有 markdown 包装的 JSON"""
        output = '''{
    "summary": "直接 JSON",
    "approach": "aggressive",
    "subtasks": [
        {"id": "task-1", "description": "快速实现"}
    ],
    "rationale": "激进策略",
    "confidence": 0.7
}'''
        proposal = ProposalParser.parse(output, "codex")
        assert proposal.summary == "直接 JSON"
        assert proposal.approach == ApproachType.AGGRESSIVE
        assert proposal.parse_success is True

    def test_parse_fallback_numbered_list(self):
        """测试 fallback 解析（编号列表）"""
        output = '''我的实施方案如下：

1. 设计数据库模型
2. 实现 API 端点
3. 添加测试用例
4. 部署到生产环境

这个方案风险较低。'''
        proposal = ProposalParser.parse(output, "claude")
        assert proposal.model == "claude"
        assert len(proposal.subtasks) >= 4
        assert proposal.parse_success is False  # fallback 模式
        assert proposal.confidence == 0.5  # fallback 置信度

    def test_parse_fallback_bullet_list(self):
        """测试 fallback 解析（项目符号列表）"""
        output = '''实施步骤：
- 分析需求
- 设计架构
- 编写代码
- 测试验证'''
        proposal = ProposalParser.parse(output, "codex")
        assert len(proposal.subtasks) >= 4
        assert proposal.parse_success is False


class TestConsensusAnalyzer:
    """测试共识分析器"""

    @pytest.fixture
    def analyzer(self):
        config = SkillpackConfig()
        return ConsensusAnalyzer(config)

    @pytest.fixture
    def claude_proposal(self):
        return PlanProposal(
            model="claude",
            summary="保守的实现方案",
            subtasks=[
                Subtask(id="task-1", description="设计数据库模型", priority=1),
                Subtask(id="task-2", description="实现 API 端点", priority=2),
                Subtask(id="task-3", description="添加单元测试", priority=3),
            ],
            approach=ApproachType.CONSERVATIVE,
            rationale="优先保证稳定性",
            risks=["性能可能不够优化"],
            confidence=0.85
        )

    @pytest.fixture
    def codex_proposal(self):
        return PlanProposal(
            model="codex",
            summary="平衡的实现方案",
            subtasks=[
                Subtask(id="task-1", description="设计数据库模型", priority=1),
                Subtask(id="task-2", description="实现 API 端点", priority=2),
                Subtask(id="task-3", description="性能优化", priority=3),
            ],
            approach=ApproachType.BALANCED,
            rationale="平衡性能和稳定性",
            risks=["开发周期可能延长"],
            confidence=0.8
        )

    def test_analyze_partial_agreement(self, analyzer, claude_proposal, codex_proposal):
        """测试部分一致的情况"""
        consensus = analyzer.analyze(claude_proposal, codex_proposal)

        # 由于方案类型和风险评估不同，可能返回 DISAGREEMENT
        assert consensus.status in [
            ConsensusStatus.PARTIAL_AGREEMENT,
            ConsensusStatus.FULL_AGREEMENT,
            ConsensusStatus.DISAGREEMENT  # 多个 MAJOR 分歧会触发
        ]
        assert consensus.claude_proposal == claude_proposal
        assert consensus.codex_proposal == codex_proposal
        assert len(consensus.final_subtasks) > 0

    def test_analyze_approach_divergence(self, analyzer, claude_proposal, codex_proposal):
        """测试方案类型分歧"""
        consensus = analyzer.analyze(claude_proposal, codex_proposal)

        # 应该检测到方案类型分歧
        approach_divergences = [
            d for d in consensus.divergences
            if d.aspect == "approach"
        ]
        assert len(approach_divergences) >= 1

    def test_analyze_full_agreement(self, analyzer):
        """测试完全一致的情况"""
        # 创建两个几乎相同的方案
        proposal1 = PlanProposal(
            model="claude",
            summary="相同方案",
            subtasks=[Subtask(id="task-1", description="实现功能A")],
            approach=ApproachType.BALANCED,
            rationale="相同理由",
            confidence=0.9
        )
        proposal2 = PlanProposal(
            model="codex",
            summary="相同方案",
            subtasks=[Subtask(id="task-1", description="实现功能A")],
            approach=ApproachType.BALANCED,
            rationale="相同理由",
            confidence=0.9
        )

        consensus = analyzer.analyze(proposal1, proposal2)
        assert consensus.status == ConsensusStatus.FULL_AGREEMENT

    def test_merge_subtasks(self, analyzer, claude_proposal, codex_proposal):
        """测试子任务合并"""
        consensus = analyzer.analyze(claude_proposal, codex_proposal)

        # 合并后的子任务应该包含两个方案的内容
        descriptions = [t.description for t in consensus.final_subtasks]
        assert any("数据库" in d for d in descriptions)
        assert any("API" in d for d in descriptions)

    def test_consensus_confidence(self, analyzer, claude_proposal, codex_proposal):
        """测试共识置信度计算"""
        consensus = analyzer.analyze(claude_proposal, codex_proposal)

        # 置信度应该在 0.3 到 1.0 之间
        assert 0.3 <= consensus.consensus_confidence <= 1.0


class TestPlanningConsensus:
    """测试 PlanningConsensus"""

    def test_to_implementation_prompt(self):
        """测试生成实现 prompt"""
        consensus = PlanningConsensus(
            status=ConsensusStatus.PARTIAL_AGREEMENT,
            claude_proposal=None,
            codex_proposal=None,
            divergences=[],
            final_subtasks=[
                Subtask(id="task-1", description="实现登录功能", priority=1),
                Subtask(id="task-2", description="添加测试", priority=2),
            ],
            consensus_confidence=0.85,
            total_planning_time_ms=5000
        )

        prompt = consensus.to_implementation_prompt()
        assert "规划共识" in prompt
        assert "实现登录功能" in prompt
        assert "85%" in prompt

    def test_to_dict(self):
        """测试序列化为字典"""
        consensus = PlanningConsensus(
            status=ConsensusStatus.FULL_AGREEMENT,
            claude_proposal=None,
            codex_proposal=None,
            divergences=[],
            final_subtasks=[],
            consensus_confidence=0.9
        )

        d = consensus.to_dict()
        assert d["status"] == "full_agreement"
        assert d["consensus_confidence"] == 0.9


class TestPlanningPromptBuilder:
    """测试规划 prompt 构建器"""

    def test_build_claude_prompt(self):
        """测试构建 Claude 规划 prompt"""
        prompt = PlanningPromptBuilder.build_claude_prompt("实现用户认证系统")
        assert "实现用户认证系统" in prompt
        assert "JSON" in prompt
        assert "subtasks" in prompt

    def test_build_codex_prompt(self):
        """测试构建 Codex 规划 prompt"""
        prompt = PlanningPromptBuilder.build_codex_prompt("Implement user auth")
        assert "Implement user auth" in prompt
        assert "JSON" in prompt
        assert "subtasks" in prompt

    def test_build_with_context(self):
        """测试带上下文的 prompt"""
        prompt = PlanningPromptBuilder.build_claude_prompt(
            "实现功能",
            context="工作目录: /project"
        )
        assert "工作目录" in prompt


class TestFormatConsensusMarkdown:
    """测试 Markdown 格式化"""

    def test_format_basic_consensus(self):
        """测试基本共识报告格式化"""
        consensus = PlanningConsensus(
            status=ConsensusStatus.PARTIAL_AGREEMENT,
            claude_proposal=PlanProposal(
                model="claude",
                summary="Claude 方案",
                subtasks=[Subtask(id="t1", description="任务1")],
                approach=ApproachType.CONSERVATIVE,
                rationale="理由",
                confidence=0.8
            ),
            codex_proposal=PlanProposal(
                model="codex",
                summary="Codex 方案",
                subtasks=[Subtask(id="t1", description="任务1")],
                approach=ApproachType.BALANCED,
                rationale="理由",
                confidence=0.85
            ),
            divergences=[
                Divergence(
                    aspect="approach",
                    level=DivergenceLevel.MAJOR,
                    claude_position="conservative",
                    codex_position="balanced",
                    description="方案类型不同"
                )
            ],
            final_subtasks=[Subtask(id="t1", description="最终任务1")],
            consensus_confidence=0.82,
            total_planning_time_ms=3000
        )

        md = format_consensus_markdown(consensus)
        assert "# 规划共识报告" in md
        assert "Claude 方案" in md
        assert "Codex 方案" in md
        assert "分歧分析" in md
        assert "最终执行计划" in md


class TestConsensusOrchestrator:
    """测试共识编排器"""

    @pytest.fixture
    def mock_dispatcher(self):
        """创建 mock 调度器"""
        dispatcher = Mock()

        # Mock Codex 规划调用
        mock_result = Mock()
        mock_result.success = True
        mock_result.output = json.dumps({
            "summary": "Codex 的实现方案",
            "approach": "balanced",
            "subtasks": [
                {"id": "task-1", "description": "实现核心功能", "priority": 1}
            ],
            "risks": ["时间风险"],
            "rationale": "平衡效率和质量",
            "confidence": 0.85
        })
        mock_result.duration_ms = 5000

        dispatcher.call_codex_for_planning.return_value = mock_result
        return dispatcher

    def test_orchestrate_without_claude_callback(self, mock_dispatcher):
        """测试没有 Claude 回调时的编排"""
        config = SkillpackConfig()
        orchestrator = ConsensusOrchestrator(mock_dispatcher, config)

        consensus = orchestrator.orchestrate(
            task="实现用户认证功能",
            context=None,
            claude_callback=None
        )

        assert consensus is not None
        assert consensus.codex_proposal is not None
        assert mock_dispatcher.call_codex_for_planning.called

    def test_orchestrate_with_claude_callback(self, mock_dispatcher):
        """测试有 Claude 回调时的编排"""
        config = SkillpackConfig()
        orchestrator = ConsensusOrchestrator(mock_dispatcher, config)

        def claude_callback(prompt):
            return json.dumps({
                "summary": "Claude 的实现方案",
                "approach": "conservative",
                "subtasks": [
                    {"id": "task-1", "description": "安全实现", "priority": 1}
                ],
                "rationale": "保守策略",
                "confidence": 0.9
            })

        consensus = orchestrator.orchestrate(
            task="实现用户认证功能",
            context=None,
            claude_callback=claude_callback
        )

        assert consensus is not None
        assert consensus.claude_proposal is not None
        assert consensus.codex_proposal is not None

    def test_orchestrate_codex_timeout(self, mock_dispatcher):
        """测试 Codex 超时的情况"""
        from concurrent.futures import TimeoutError

        mock_dispatcher.call_codex_for_planning.side_effect = TimeoutError()

        config = SkillpackConfig()
        orchestrator = ConsensusOrchestrator(mock_dispatcher, config)
        orchestrator._planning_timeout = 0.1

        consensus = orchestrator.orchestrate(
            task="实现功能",
            context=None,
            claude_callback=None
        )

        # Codex 超时会创建 fallback 提案，与 Claude 占位提案进行共识分析
        # 因此不会是 SINGLE_MODEL，而是根据分析结果确定
        assert consensus.codex_proposal is not None
        assert consensus.codex_proposal.parse_success is False  # fallback 提案
        # 置信度应该较低（因为一方失败）
        assert consensus.consensus_confidence <= 0.5


class TestConsensusConfig:
    """测试共识配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = ConsensusConfig()
        assert config.enabled is True
        assert config.parallel_planning is True
        assert config.arbitration_threshold == 0.7
        assert "PLANNED" in config.covered_routes
        assert "RALPH" in config.covered_routes
        assert "ARCHITECT" in config.covered_routes

    def test_custom_config(self):
        """测试自定义配置"""
        config = ConsensusConfig(
            enabled=False,
            parallel_planning=False,
            arbitration_threshold=0.5,
            planning_timeout_seconds=60
        )
        assert config.enabled is False
        assert config.planning_timeout_seconds == 60


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def full_config(self):
        """完整配置"""
        return SkillpackConfig()

    def test_full_consensus_flow(self, full_config):
        """测试完整共识流程"""
        # 创建两个方案
        claude_proposal = PlanProposal(
            model="claude",
            summary="Claude 的保守方案",
            subtasks=[
                Subtask(id="t1", description="安全实现登录", priority=1),
                Subtask(id="t2", description="添加完整测试", priority=2),
            ],
            approach=ApproachType.CONSERVATIVE,
            rationale="优先安全性",
            risks=["性能可能受影响"],
            confidence=0.85
        )

        codex_proposal = PlanProposal(
            model="codex",
            summary="Codex 的平衡方案",
            subtasks=[
                Subtask(id="t1", description="实现登录功能", priority=1),
                Subtask(id="t2", description="性能优化", priority=2),
            ],
            approach=ApproachType.BALANCED,
            rationale="平衡各方面",
            risks=["测试覆盖可能不足"],
            confidence=0.8
        )

        # 分析共识
        analyzer = ConsensusAnalyzer(full_config)
        consensus = analyzer.analyze(claude_proposal, codex_proposal)

        # 验证结果
        assert consensus.status in [
            ConsensusStatus.PARTIAL_AGREEMENT,
            ConsensusStatus.DISAGREEMENT
        ]
        assert len(consensus.final_subtasks) > 0
        assert 0.3 <= consensus.consensus_confidence <= 1.0

        # 生成报告
        md = format_consensus_markdown(consensus)
        assert len(md) > 100

        # 生成实现 prompt
        impl_prompt = consensus.to_implementation_prompt()
        assert "规划共识" in impl_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
