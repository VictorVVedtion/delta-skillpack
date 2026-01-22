"""
多模型规划共识模块 (v5.5)

在规划阶段引入 Codex/ChatGPT 打破 Claude 的"一言堂"，形成多模型共识后再执行。

架构:
    Claude 方案 A ─┬─→ 共识分析 ─→ 仲裁（如有分歧）─→ 实现
    Codex 方案 B ─┘
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple

from .models import SkillpackConfig, TaskContext


class ConsensusStatus(Enum):
    """共识状态"""
    FULL_AGREEMENT = "full_agreement"      # 完全一致
    PARTIAL_AGREEMENT = "partial_agreement"  # 部分一致
    DISAGREEMENT = "disagreement"          # 存在分歧
    SINGLE_MODEL = "single_model"          # 单模型（另一方超时/失败）


class ApproachType(Enum):
    """方案类型"""
    CONSERVATIVE = "conservative"    # 保守方案：低风险，增量变更
    BALANCED = "balanced"            # 平衡方案：风险与效率平衡
    AGGRESSIVE = "aggressive"        # 激进方案：高效率，可能有风险


class DivergenceLevel(Enum):
    """分歧级别"""
    CRITICAL = "critical"     # 关键分歧：架构、安全相关
    MAJOR = "major"           # 重大分歧：方案选择不同
    MINOR = "minor"           # 轻微分歧：细节差异
    NEGLIGIBLE = "negligible" # 可忽略：表述差异


@dataclass
class Subtask:
    """子任务"""
    id: str
    description: str
    priority: int = 1  # 1=最高
    estimated_effort: str = "medium"  # low, medium, high
    dependencies: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
            "dependencies": self.dependencies,
            "files": self.files
        }


@dataclass
class PlanProposal:
    """单个模型的规划提案"""
    model: str                           # claude, codex
    summary: str                         # 方案摘要
    subtasks: List[Subtask]              # 子任务列表
    approach: ApproachType               # 方案类型
    rationale: str                       # 理由/依据
    risks: List[str] = field(default_factory=list)  # 风险列表
    estimated_total_effort: str = "medium"  # 总体工作量估算
    confidence: float = 0.8              # 置信度 0-1
    raw_output: str = ""                 # 原始输出
    parse_success: bool = True           # 解析是否成功
    generation_time_ms: int = 0          # 生成耗时

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "summary": self.summary,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "approach": self.approach.value,
            "rationale": self.rationale,
            "risks": self.risks,
            "estimated_total_effort": self.estimated_total_effort,
            "confidence": self.confidence,
            "parse_success": self.parse_success,
            "generation_time_ms": self.generation_time_ms
        }


@dataclass
class Divergence:
    """分歧点"""
    aspect: str                  # 分歧方面：architecture, approach, subtasks, risks
    level: DivergenceLevel       # 分歧级别
    claude_position: str         # Claude 的立场
    codex_position: str          # Codex 的立场
    description: str             # 分歧描述
    resolution_suggestion: str = ""  # 解决建议

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aspect": self.aspect,
            "level": self.level.value,
            "claude_position": self.claude_position,
            "codex_position": self.codex_position,
            "description": self.description,
            "resolution_suggestion": self.resolution_suggestion
        }


@dataclass
class ArbitrationDecision:
    """仲裁决策"""
    accepted_approach: str       # claude, codex, merged
    reasoning: str               # 决策理由
    resolved_divergences: List[Dict[str, Any]] = field(default_factory=list)
    modifications: List[str] = field(default_factory=list)
    confidence: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted_approach": self.accepted_approach,
            "reasoning": self.reasoning,
            "resolved_divergences": self.resolved_divergences,
            "modifications": self.modifications,
            "confidence": self.confidence
        }


@dataclass
class PlanningConsensus:
    """规划共识"""
    status: ConsensusStatus
    claude_proposal: Optional[PlanProposal]
    codex_proposal: Optional[PlanProposal]
    divergences: List[Divergence]
    final_subtasks: List[Subtask]
    arbitration: Optional[ArbitrationDecision] = None
    consensus_confidence: float = 0.8
    total_planning_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "claude_proposal": self.claude_proposal.to_dict() if self.claude_proposal else None,
            "codex_proposal": self.codex_proposal.to_dict() if self.codex_proposal else None,
            "divergences": [d.to_dict() for d in self.divergences],
            "final_subtasks": [s.to_dict() for s in self.final_subtasks],
            "arbitration": self.arbitration.to_dict() if self.arbitration else None,
            "consensus_confidence": self.consensus_confidence,
            "total_planning_time_ms": self.total_planning_time_ms
        }

    def to_implementation_prompt(self) -> str:
        """生成传递给实现阶段的 prompt"""
        subtasks_text = "\n".join([
            f"{i+1}. [{s.priority}级] {s.description} (工作量: {s.estimated_effort})"
            for i, s in enumerate(self.final_subtasks)
        ])

        consensus_info = f"""## 规划共识 (v5.5)

### 共识状态
- 状态: {self.status.value}
- 置信度: {self.consensus_confidence:.0%}
- 规划耗时: {self.total_planning_time_ms}ms

### 最终子任务列表
{subtasks_text}
"""

        if self.arbitration:
            consensus_info += f"""
### 仲裁决策
- 采纳方案: {self.arbitration.accepted_approach}
- 决策理由: {self.arbitration.reasoning}
"""

        if self.divergences:
            divergence_text = "\n".join([
                f"- [{d.level.value}] {d.aspect}: {d.description}"
                for d in self.divergences[:5]  # 最多显示5个
            ])
            consensus_info += f"""
### 分歧点（已解决）
{divergence_text}
"""

        return consensus_info


class PlanningPromptBuilder:
    """规划 prompt 构建器"""

    CLAUDE_PLANNING_TEMPLATE = """作为资深软件架构师，为以下任务设计详细的实施方案。

## 任务描述
{task}

## 要求
1. **方案摘要**: 简明扼要地描述你的实施思路
2. **子任务分解**: 将任务拆分为可执行的子任务（3-8个）
3. **风险评估**: 识别潜在风险和挑战
4. **方案类型**: 判断你的方案是保守型、平衡型还是激进型

## 输出格式（JSON）
```json
{{
    "summary": "方案摘要...",
    "approach": "conservative|balanced|aggressive",
    "subtasks": [
        {{
            "id": "task-1",
            "description": "子任务描述",
            "priority": 1,
            "estimated_effort": "low|medium|high",
            "dependencies": [],
            "files": ["相关文件路径"]
        }}
    ],
    "risks": ["风险1", "风险2"],
    "rationale": "选择这个方案的理由...",
    "confidence": 0.85
}}
```

注意：
- 只做规划，不要编写实际代码
- 子任务要具体可执行
- 考虑依赖关系和执行顺序
"""

    CODEX_PLANNING_TEMPLATE = """You are a senior software architect. Design an implementation plan for the following task.

## Task
{task}

## Requirements
1. **Summary**: Briefly describe your implementation approach
2. **Subtask Breakdown**: Split into executable subtasks (3-8 items)
3. **Risk Assessment**: Identify potential risks
4. **Approach Type**: Classify as conservative, balanced, or aggressive

## Output Format (JSON)
```json
{{
    "summary": "Plan summary...",
    "approach": "conservative|balanced|aggressive",
    "subtasks": [
        {{
            "id": "task-1",
            "description": "Subtask description",
            "priority": 1,
            "estimated_effort": "low|medium|high",
            "dependencies": [],
            "files": ["related/file/path"]
        }}
    ],
    "risks": ["Risk 1", "Risk 2"],
    "rationale": "Reasoning for this approach...",
    "confidence": 0.85
}}
```

Note:
- Planning only, no actual code
- Make subtasks specific and executable
- Consider dependencies and execution order
"""

    @classmethod
    def build_claude_prompt(cls, task: str, context: Optional[str] = None) -> str:
        """构建 Claude 规划 prompt"""
        prompt = cls.CLAUDE_PLANNING_TEMPLATE.format(task=task)
        if context:
            prompt = f"## 上下文信息\n{context}\n\n" + prompt
        return prompt

    @classmethod
    def build_codex_prompt(cls, task: str, context: Optional[str] = None) -> str:
        """构建 Codex 规划 prompt"""
        prompt = cls.CODEX_PLANNING_TEMPLATE.format(task=task)
        if context:
            prompt = f"## Context\n{context}\n\n" + prompt
        return prompt


class ProposalParser:
    """提案解析器"""

    @classmethod
    def parse(cls, raw_output: str, model: str) -> PlanProposal:
        """
        解析模型输出为 PlanProposal。

        使用多种策略尝试解析：
        1. JSON 块提取
        2. 正则模式匹配
        3. 智能 fallback
        """
        # 尝试提取 JSON 块
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_output, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return cls._from_dict(data, model, raw_output)
            except json.JSONDecodeError:
                pass

        # 尝试直接解析 JSON
        try:
            # 查找 { 开头的 JSON
            json_start = raw_output.find('{')
            if json_start != -1:
                # 找到匹配的 }
                brace_count = 0
                json_end = json_start
                for i, char in enumerate(raw_output[json_start:], json_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                json_str = raw_output[json_start:json_end]
                data = json.loads(json_str)
                return cls._from_dict(data, model, raw_output)
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: 使用正则提取关键信息
        return cls._fallback_parse(raw_output, model)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any], model: str, raw_output: str) -> PlanProposal:
        """从字典构建 PlanProposal"""
        subtasks = []
        for i, task_data in enumerate(data.get("subtasks", [])):
            subtasks.append(Subtask(
                id=task_data.get("id", f"task-{i+1}"),
                description=task_data.get("description", ""),
                priority=task_data.get("priority", 1),
                estimated_effort=task_data.get("estimated_effort", "medium"),
                dependencies=task_data.get("dependencies", []),
                files=task_data.get("files", [])
            ))

        approach_str = data.get("approach", "balanced").lower()
        approach = {
            "conservative": ApproachType.CONSERVATIVE,
            "balanced": ApproachType.BALANCED,
            "aggressive": ApproachType.AGGRESSIVE
        }.get(approach_str, ApproachType.BALANCED)

        return PlanProposal(
            model=model,
            summary=data.get("summary", ""),
            subtasks=subtasks,
            approach=approach,
            rationale=data.get("rationale", ""),
            risks=data.get("risks", []),
            confidence=data.get("confidence", 0.8),
            raw_output=raw_output,
            parse_success=True
        )

    @classmethod
    def _fallback_parse(cls, raw_output: str, model: str) -> PlanProposal:
        """Fallback 解析：从非结构化文本提取信息"""
        # 尝试提取子任务（查找编号列表）
        subtasks = []
        task_patterns = [
            r'^\s*(\d+)[.)\]]\s*(.+?)(?:\n|$)',  # 1. task 或 1) task
            r'^\s*[-*]\s*(.+?)(?:\n|$)',          # - task 或 * task
        ]

        for pattern in task_patterns:
            matches = re.findall(pattern, raw_output, re.MULTILINE)
            if matches:
                for i, match in enumerate(matches[:8]):  # 最多8个子任务
                    desc = match[1] if isinstance(match, tuple) and len(match) > 1 else match
                    subtasks.append(Subtask(
                        id=f"task-{i+1}",
                        description=desc.strip()[:200],  # 限制长度
                        priority=i + 1
                    ))
                break

        # 如果没有找到子任务，创建一个通用的
        if not subtasks:
            subtasks = [Subtask(
                id="task-1",
                description="执行主要任务（解析失败，请手动审核）",
                priority=1
            )]

        # 提取摘要（取前200个字符）
        summary = raw_output.strip()[:200]
        if len(raw_output) > 200:
            summary += "..."

        return PlanProposal(
            model=model,
            summary=summary,
            subtasks=subtasks,
            approach=ApproachType.BALANCED,
            rationale="（解析失败，使用 fallback 提取）",
            raw_output=raw_output,
            parse_success=False,
            confidence=0.5
        )


class ConsensusAnalyzer:
    """
    共识分析器 - 比较 Claude 和 Codex 的规划方案，识别分歧。
    """

    def __init__(self, config: Optional[SkillpackConfig] = None):
        self.config = config or SkillpackConfig()
        self._similarity_threshold = 0.7  # 相似度阈值

    def analyze(
        self,
        claude_proposal: PlanProposal,
        codex_proposal: PlanProposal
    ) -> PlanningConsensus:
        """
        分析两个方案的共识程度。

        比较维度：
        1. 方案类型（approach）
        2. 子任务数量和内容
        3. 风险识别
        4. 依赖关系
        """
        divergences = []

        # 1. 比较方案类型
        if claude_proposal.approach != codex_proposal.approach:
            divergences.append(Divergence(
                aspect="approach",
                level=DivergenceLevel.MAJOR,
                claude_position=claude_proposal.approach.value,
                codex_position=codex_proposal.approach.value,
                description=f"方案类型不一致: Claude={claude_proposal.approach.value}, Codex={codex_proposal.approach.value}",
                resolution_suggestion="建议采用更稳妥的方案类型"
            ))

        # 2. 比较子任务数量
        task_count_diff = abs(len(claude_proposal.subtasks) - len(codex_proposal.subtasks))
        if task_count_diff > 2:
            divergences.append(Divergence(
                aspect="subtask_count",
                level=DivergenceLevel.MINOR,
                claude_position=f"{len(claude_proposal.subtasks)} 个子任务",
                codex_position=f"{len(codex_proposal.subtasks)} 个子任务",
                description=f"子任务数量差异: {task_count_diff}",
                resolution_suggestion="综合两者的子任务，取并集"
            ))

        # 3. 比较子任务内容（使用简单的关键词匹配）
        claude_task_keywords = self._extract_keywords(claude_proposal.subtasks)
        codex_task_keywords = self._extract_keywords(codex_proposal.subtasks)

        unique_to_claude = claude_task_keywords - codex_task_keywords
        unique_to_codex = codex_task_keywords - claude_task_keywords

        if unique_to_claude:
            divergences.append(Divergence(
                aspect="subtask_content",
                level=DivergenceLevel.MINOR,
                claude_position=f"包含: {', '.join(list(unique_to_claude)[:3])}",
                codex_position="不包含这些关键点",
                description=f"Claude 方案包含 Codex 未提及的内容",
                resolution_suggestion="合并 Claude 的独特子任务"
            ))

        if unique_to_codex:
            divergences.append(Divergence(
                aspect="subtask_content",
                level=DivergenceLevel.MINOR,
                claude_position="不包含这些关键点",
                codex_position=f"包含: {', '.join(list(unique_to_codex)[:3])}",
                description=f"Codex 方案包含 Claude 未提及的内容",
                resolution_suggestion="合并 Codex 的独特子任务"
            ))

        # 4. 比较风险识别
        claude_risks = set(r.lower()[:50] for r in claude_proposal.risks)
        codex_risks = set(r.lower()[:50] for r in codex_proposal.risks)

        if claude_risks and codex_risks:
            risk_overlap = len(claude_risks & codex_risks) / max(len(claude_risks), len(codex_risks))
            if risk_overlap < 0.3:
                divergences.append(Divergence(
                    aspect="risk_assessment",
                    level=DivergenceLevel.MAJOR,
                    claude_position=f"识别风险: {', '.join(claude_proposal.risks[:2])}",
                    codex_position=f"识别风险: {', '.join(codex_proposal.risks[:2])}",
                    description="风险识别差异较大，需要综合考虑",
                    resolution_suggestion="合并双方识别的风险"
                ))

        # 5. 比较置信度
        confidence_diff = abs(claude_proposal.confidence - codex_proposal.confidence)
        if confidence_diff > 0.2:
            divergences.append(Divergence(
                aspect="confidence",
                level=DivergenceLevel.NEGLIGIBLE,
                claude_position=f"置信度: {claude_proposal.confidence:.0%}",
                codex_position=f"置信度: {codex_proposal.confidence:.0%}",
                description=f"置信度差异: {confidence_diff:.0%}",
                resolution_suggestion="参考置信度较高的方案"
            ))

        # 判断共识状态
        critical_count = sum(1 for d in divergences if d.level == DivergenceLevel.CRITICAL)
        major_count = sum(1 for d in divergences if d.level == DivergenceLevel.MAJOR)

        if critical_count > 0:
            status = ConsensusStatus.DISAGREEMENT
        elif major_count >= 2:
            status = ConsensusStatus.DISAGREEMENT
        elif major_count == 1 or len(divergences) > 3:
            status = ConsensusStatus.PARTIAL_AGREEMENT
        else:
            status = ConsensusStatus.FULL_AGREEMENT

        # 合并子任务
        final_subtasks = self._merge_subtasks(
            claude_proposal.subtasks,
            codex_proposal.subtasks
        )

        # 计算共识置信度
        consensus_confidence = self._calculate_consensus_confidence(
            claude_proposal, codex_proposal, divergences
        )

        return PlanningConsensus(
            status=status,
            claude_proposal=claude_proposal,
            codex_proposal=codex_proposal,
            divergences=divergences,
            final_subtasks=final_subtasks,
            consensus_confidence=consensus_confidence
        )

    def _extract_keywords(self, subtasks: List[Subtask]) -> set:
        """从子任务中提取关键词"""
        keywords = set()
        # 关键动词和名词
        important_words = {
            'create', 'implement', 'add', 'modify', 'update', 'fix', 'refactor',
            'test', 'validate', 'review', 'setup', 'configure', 'integrate',
            '创建', '实现', '添加', '修改', '更新', '修复', '重构',
            '测试', '验证', '审查', '配置', '集成'
        }

        for task in subtasks:
            words = re.findall(r'\w+', task.description.lower())
            for word in words:
                if word in important_words or len(word) > 6:
                    keywords.add(word)
            # 添加文件路径作为关键词
            for f in task.files:
                keywords.add(Path(f).stem.lower())

        return keywords

    def _merge_subtasks(
        self,
        claude_tasks: List[Subtask],
        codex_tasks: List[Subtask]
    ) -> List[Subtask]:
        """
        合并两个方案的子任务。

        策略：以 Claude 方案为基础，补充 Codex 的独特子任务。
        """
        merged = list(claude_tasks)  # 复制 Claude 的任务
        existing_descriptions = {t.description.lower()[:50] for t in merged}

        for task in codex_tasks:
            task_key = task.description.lower()[:50]
            # 检查是否有相似的任务
            is_similar = any(
                self._text_similarity(task_key, existing) > 0.6
                for existing in existing_descriptions
            )
            if not is_similar:
                # 添加 Codex 独特的任务
                new_task = Subtask(
                    id=f"codex-{task.id}",
                    description=f"[Codex 补充] {task.description}",
                    priority=task.priority + 10,  # 降低优先级
                    estimated_effort=task.estimated_effort,
                    dependencies=task.dependencies,
                    files=task.files
                )
                merged.append(new_task)
                existing_descriptions.add(task_key)

        # 按优先级排序
        merged.sort(key=lambda t: t.priority)

        # 重新编号
        for i, task in enumerate(merged):
            task.id = f"task-{i+1}"

        return merged

    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算（Jaccard 相似度）"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _calculate_consensus_confidence(
        self,
        claude: PlanProposal,
        codex: PlanProposal,
        divergences: List[Divergence]
    ) -> float:
        """计算共识置信度"""
        # 基础置信度：两个方案置信度的平均值
        base_confidence = (claude.confidence + codex.confidence) / 2

        # 根据分歧扣分
        penalty = 0.0
        for d in divergences:
            if d.level == DivergenceLevel.CRITICAL:
                penalty += 0.15
            elif d.level == DivergenceLevel.MAJOR:
                penalty += 0.08
            elif d.level == DivergenceLevel.MINOR:
                penalty += 0.03

        # 如果有解析失败，额外扣分
        if not claude.parse_success:
            penalty += 0.1
        if not codex.parse_success:
            penalty += 0.1

        return max(0.3, min(1.0, base_confidence - penalty))


class ConsensusOrchestrator:
    """
    共识编排器 - 协调 Claude 和 Codex 的并行规划。
    """

    def __init__(
        self,
        dispatcher,  # ModelDispatcher 实例
        config: Optional[SkillpackConfig] = None
    ):
        self.dispatcher = dispatcher
        self.config = config or SkillpackConfig()
        self.analyzer = ConsensusAnalyzer(config)
        self._planning_timeout = 120  # 单模型规划超时（秒）

    def orchestrate(
        self,
        task: str,
        context: Optional[TaskContext] = None,
        claude_callback: Optional[Callable[[str], str]] = None
    ) -> PlanningConsensus:
        """
        编排多模型规划共识流程。

        Args:
            task: 任务描述
            context: 任务上下文（可选）
            claude_callback: Claude 规划回调函数（用于当前 Claude 实例执行规划）

        Returns:
            PlanningConsensus 共识结果
        """
        start_time = time.time()

        context_str = ""
        if context and context.working_dir:
            context_str = f"工作目录: {context.working_dir}"

        # 并行调用 Claude 和 Codex
        claude_proposal = None
        codex_proposal = None

        with ThreadPoolExecutor(max_workers=2) as pool:
            # 提交 Codex 规划任务
            codex_future = pool.submit(
                self._call_codex_planning,
                task,
                context_str
            )

            # Claude 规划（通过回调或占位）
            if claude_callback:
                try:
                    claude_start = time.time()
                    claude_prompt = PlanningPromptBuilder.build_claude_prompt(task, context_str)
                    claude_output = claude_callback(claude_prompt)
                    claude_time_ms = int((time.time() - claude_start) * 1000)

                    claude_proposal = ProposalParser.parse(claude_output, "claude")
                    claude_proposal.generation_time_ms = claude_time_ms
                except Exception as e:
                    claude_proposal = self._create_fallback_proposal("claude", str(e))
            else:
                # 如果没有回调，创建一个占位提案
                claude_proposal = self._create_placeholder_proposal("claude", task)

            # 等待 Codex 完成
            try:
                codex_proposal = codex_future.result(timeout=self._planning_timeout)
            except FuturesTimeoutError:
                codex_proposal = self._create_fallback_proposal("codex", "规划超时")
            except Exception as e:
                codex_proposal = self._create_fallback_proposal("codex", str(e))

        # 分析共识
        if claude_proposal and codex_proposal:
            consensus = self.analyzer.analyze(claude_proposal, codex_proposal)
        else:
            # 单模型情况
            proposal = claude_proposal or codex_proposal
            consensus = PlanningConsensus(
                status=ConsensusStatus.SINGLE_MODEL,
                claude_proposal=claude_proposal,
                codex_proposal=codex_proposal,
                divergences=[],
                final_subtasks=proposal.subtasks if proposal else [],
                consensus_confidence=proposal.confidence if proposal else 0.5
            )

        consensus.total_planning_time_ms = int((time.time() - start_time) * 1000)

        return consensus

    def _call_codex_planning(self, task: str, context_str: str) -> PlanProposal:
        """调用 Codex 进行规划"""
        start_time = time.time()

        prompt = PlanningPromptBuilder.build_codex_prompt(task, context_str)
        result = self.dispatcher.call_codex_for_planning(prompt)

        time_ms = int((time.time() - start_time) * 1000)

        if result.success:
            proposal = ProposalParser.parse(result.output, "codex")
        else:
            proposal = self._create_fallback_proposal("codex", result.error or "执行失败")

        proposal.generation_time_ms = time_ms
        return proposal

    def _create_fallback_proposal(self, model: str, error: str) -> PlanProposal:
        """创建 fallback 提案（当模型调用失败时）"""
        return PlanProposal(
            model=model,
            summary=f"({model} 规划失败: {error})",
            subtasks=[Subtask(
                id="task-1",
                description="执行主要任务（规划阶段失败）",
                priority=1
            )],
            approach=ApproachType.CONSERVATIVE,
            rationale=f"由于 {model} 规划失败，使用保守策略",
            risks=[f"{model} 规划失败可能导致方案不完整"],
            confidence=0.4,
            parse_success=False
        )

    def _create_placeholder_proposal(self, model: str, task: str) -> PlanProposal:
        """创建占位提案（当没有回调时）"""
        return PlanProposal(
            model=model,
            summary=f"为任务 '{task[:50]}...' 的规划（待完成）",
            subtasks=[Subtask(
                id="task-1",
                description=task[:200],
                priority=1
            )],
            approach=ApproachType.BALANCED,
            rationale="占位提案，等待实际规划",
            confidence=0.5,
            parse_success=True
        )

    def arbitrate(self, consensus: PlanningConsensus) -> PlanningConsensus:
        """
        仲裁分歧（由 Claude 执行）。

        当 consensus.status == DISAGREEMENT 时调用。
        返回更新后的 consensus，包含仲裁决策。
        """
        if consensus.status != ConsensusStatus.DISAGREEMENT:
            return consensus

        # 生成仲裁提示（供 Claude 使用）
        arbitration_prompt = self._build_arbitration_prompt(consensus)

        # 仲裁决策（这里生成占位，实际由 Claude 填充）
        consensus.arbitration = ArbitrationDecision(
            accepted_approach="merged",
            reasoning="综合两个方案的优点，采用合并策略",
            resolved_divergences=[d.to_dict() for d in consensus.divergences],
            confidence=consensus.consensus_confidence
        )

        # 更新状态
        consensus.status = ConsensusStatus.PARTIAL_AGREEMENT

        return consensus

    def _build_arbitration_prompt(self, consensus: PlanningConsensus) -> str:
        """构建仲裁 prompt"""
        divergences_text = "\n".join([
            f"- [{d.level.value}] {d.aspect}: {d.description}"
            for d in consensus.divergences
        ])

        return f"""## 规划仲裁请求

两个模型在规划阶段产生了分歧，请仲裁。

### Claude 方案
{consensus.claude_proposal.summary if consensus.claude_proposal else "无"}

### Codex 方案
{consensus.codex_proposal.summary if consensus.codex_proposal else "无"}

### 分歧点
{divergences_text}

### 请决策
1. 采纳哪个方案（claude/codex/merged）
2. 决策理由
3. 如何解决各分歧点
"""


def format_consensus_markdown(consensus: PlanningConsensus) -> str:
    """格式化共识为 Markdown 输出"""
    lines = [
        "# 规划共识报告 (v5.5)",
        "",
        "## 概览",
        f"- **共识状态**: {consensus.status.value}",
        f"- **共识置信度**: {consensus.consensus_confidence:.0%}",
        f"- **规划总耗时**: {consensus.total_planning_time_ms}ms",
        ""
    ]

    # Claude 方案
    if consensus.claude_proposal:
        cp = consensus.claude_proposal
        lines.extend([
            "## Claude 方案",
            f"- **方案类型**: {cp.approach.value}",
            f"- **置信度**: {cp.confidence:.0%}",
            f"- **解析状态**: {'✅ 成功' if cp.parse_success else '⚠️ 降级解析'}",
            f"- **生成耗时**: {cp.generation_time_ms}ms",
            "",
            f"### 摘要",
            cp.summary,
            "",
            "### 子任务",
        ])
        for task in cp.subtasks:
            lines.append(f"- [{task.priority}] {task.description}")
        if cp.risks:
            lines.extend(["", "### 风险"])
            for risk in cp.risks:
                lines.append(f"- {risk}")
        lines.append("")

    # Codex 方案
    if consensus.codex_proposal:
        cp = consensus.codex_proposal
        lines.extend([
            "## Codex 方案",
            f"- **方案类型**: {cp.approach.value}",
            f"- **置信度**: {cp.confidence:.0%}",
            f"- **解析状态**: {'✅ 成功' if cp.parse_success else '⚠️ 降级解析'}",
            f"- **生成耗时**: {cp.generation_time_ms}ms",
            "",
            f"### 摘要",
            cp.summary,
            "",
            "### 子任务",
        ])
        for task in cp.subtasks:
            lines.append(f"- [{task.priority}] {task.description}")
        if cp.risks:
            lines.extend(["", "### 风险"])
            for risk in cp.risks:
                lines.append(f"- {risk}")
        lines.append("")

    # 分歧
    if consensus.divergences:
        lines.extend([
            "## 分歧分析",
        ])
        for d in consensus.divergences:
            lines.extend([
                f"### {d.aspect} [{d.level.value}]",
                f"- **Claude**: {d.claude_position}",
                f"- **Codex**: {d.codex_position}",
                f"- **说明**: {d.description}",
                f"- **建议**: {d.resolution_suggestion}",
                ""
            ])

    # 仲裁决策
    if consensus.arbitration:
        arb = consensus.arbitration
        lines.extend([
            "## 仲裁决策",
            f"- **采纳方案**: {arb.accepted_approach}",
            f"- **决策置信度**: {arb.confidence:.0%}",
            "",
            "### 决策理由",
            arb.reasoning,
            ""
        ])

    # 最终子任务
    lines.extend([
        "## 最终执行计划",
    ])
    for task in consensus.final_subtasks:
        lines.append(f"{task.id}. [{task.priority}级] {task.description} (工作量: {task.estimated_effort})")

    return "\n".join(lines)
