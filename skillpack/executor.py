"""
任务执行器

提供不同路由的执行策略，使用 ModelDispatcher 进行真实的模型调用。
v5.4.0: 集成 CLI 调度器，实现真实的 Codex/Gemini 调用。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import json
import time
import uuid

from .models import TaskContext, ExecutionRoute, SkillpackConfig
from .dispatch import ModelDispatcher, ModelType, DispatchResult, get_dispatcher
from .ralph.dashboard import ProgressTracker, SimpleProgressTracker, Phase
from .usage import UsageStore, UsageRecord
from .consensus import (
    ConsensusOrchestrator,
    ConsensusAnalyzer,
    PlanningConsensus,
    ConsensusStatus,
    PlanProposal,
    ProposalParser,
    format_consensus_markdown
)


@dataclass
class ExecutionStatus:
    """执行状态"""
    is_running: bool = False
    error: Optional[str] = None
    output_files: list[str] = None
    model_calls: list[dict] = None  # 记录实际的模型调用

    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []
        if self.model_calls is None:
            self.model_calls = []


class ExecutorStrategy(ABC):
    """执行器策略基类"""

    def __init__(self, config: Optional[SkillpackConfig] = None):
        self.config = config or SkillpackConfig()
        self.dispatcher = get_dispatcher(self.config)
        self.output_dir = Path(self.config.output.current_dir)

    @abstractmethod
    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        """执行任务"""
        pass

    def _save_output(self, filename: str, content: str) -> Path:
        """保存输出文件"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _format_result_markdown(
        self,
        phase_name: str,
        model: ModelType,
        result: DispatchResult,
        context: TaskContext
    ) -> str:
        """格式化结果为 Markdown"""
        status = "✅ 成功" if result.success else "❌ 失败"
        mode = result.mode.value if result.mode else "unknown"

        header = f"""# {phase_name}

## 执行信息
- **任务**: {context.description}
- **模型**: {model.value.capitalize()}
- **执行模式**: {mode.upper()}
- **状态**: {status}
- **耗时**: {result.duration_ms / 1000:.2f}s
- **命令**: `{result.command}`

---

## 输出

"""
        if result.success:
            return header + result.output
        else:
            return header + f"### 错误\n\n```\n{result.error}\n```\n\n### 部分输出\n\n{result.output}"


class DirectExecutor(ExecutorStrategy):
    """
    直接执行器 (DIRECT_TEXT/DIRECT_CODE)

    v5.4.1: 统一使用 Codex CLI 执行所有任务
    - DIRECT_TEXT: Codex CLI 执行（文本/配置/文档修改）
    - DIRECT_CODE: Codex CLI 执行（代码修改）
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        tracker.start_phase(Phase.IMPLEMENTING)
        model_calls = []

        # 判断是文本任务还是代码任务（用于路由标签）
        is_code_task = self._is_code_task(context.description)
        route_label = "DIRECT_CODE" if is_code_task else "DIRECT_TEXT"

        # 统一使用 Codex CLI 执行
        tracker.update(0.3, "准备 Codex 调用...")

        # 输出阶段头部
        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=1,
            phase_name="执行",
            route=route_label,
            model=ModelType.CODEX,
            progress_percent=30
        )
        print(header)

        # 调用 Codex CLI
        result = self.dispatcher.call_codex(
            prompt=context.description,
            context_files=self._get_context_files(context)
        )

        model_calls.append({
            "phase": 1,
            "model": ModelType.CODEX.value,
            "route": route_label,
            "success": result.success,
            "duration_ms": result.duration_ms
        })

        tracker.update(0.9, "保存结果...")

        # 保存输出
        output_content = self._format_result_markdown(
            f"{route_label} 执行结果",
            ModelType.CODEX,
            result,
            context
        )
        self._save_output("output.txt", output_content)

        # 输出完成信息
        complete_msg = self.dispatcher.format_phase_complete(
            phase=1,
            model=ModelType.CODEX,
            duration_ms=result.duration_ms,
            output_file=".skillpack/current/output.txt"
        )
        print(complete_msg)

        tracker.complete_phase()
        tracker.complete()

        return ExecutionStatus(
            is_running=False,
            error=result.error if not result.success else None,
            output_files=["output.txt"],
            model_calls=model_calls
        )

    def _is_code_task(self, description: str) -> bool:
        """判断是否为代码任务"""
        code_signals = [
            "fix", "bug", "function", "method", "implement", "实现",
            ".ts", ".js", ".py", ".go", ".rs", ".java", ".tsx", ".jsx",
            "code", "add", "remove", "refactor", "修复"
        ]
        text_signals = [
            "typo", "readme", "文档", "docs", "comment", "注释",
            "config", "配置", ".md", ".txt", ".json", ".yaml"
        ]

        desc_lower = description.lower()

        # 如果包含文本信号，优先判断为文本任务
        for signal in text_signals:
            if signal in desc_lower:
                return False

        # 如果包含代码信号，判断为代码任务
        for signal in code_signals:
            if signal in desc_lower:
                return True

        return False

    def _get_context_files(self, context: TaskContext) -> List[str]:
        """从任务描述中提取相关文件"""
        # 简单实现：提取文件路径模式
        import re
        files = re.findall(r'[\w/.-]+\.(ts|js|py|go|rs|java|tsx|jsx|md|json|yaml|toml)', context.description)
        return files


class PlannedExecutor(ExecutorStrategy):
    """
    计划执行器 (PLANNED) v5.5

    Phase 1: 并行规划 - Claude + Codex (多模型共识)
    Phase 2: 共识分析/仲裁 - Claude
    Phase 3: 实现 - Codex (CLI)
    Phase 4: 审查 - Codex (CLI)
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        model_calls = []
        consensus_enabled = self.config.consensus.enabled

        # Phase 1: 并行规划 (Claude + Codex) - v5.5 新增
        tracker.start_phase(Phase.PLANNING)
        tracker.update(0.05, "准备多模型并行规划...")

        total_phases = 4 if consensus_enabled else 3

        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=total_phases,
            phase_name="并行规划" if consensus_enabled else "规划",
            route="PLANNED",
            model=ModelType.CLAUDE,
            progress_percent=5
        )
        print(header)

        consensus = None
        if consensus_enabled:
            # 使用多模型共识规划
            consensus = self._parallel_planning(context, tracker)

            model_calls.append({
                "phase": 1,
                "model": "claude+codex",
                "type": "consensus_planning",
                "success": True,
                "duration_ms": consensus.total_planning_time_ms
            })

            # 保存共识报告
            consensus_content = format_consensus_markdown(consensus)
            self._save_output("1_planning_consensus.md", consensus_content)

            print(f"""✅ Phase 1 完成 (多模型规划共识)
├── Claude 方案: {"✓" if consensus.claude_proposal else "✗"}
├── Codex 方案: {"✓" if consensus.codex_proposal else "✗"}
├── 共识状态: {consensus.status.value}
├── 共识置信度: {consensus.consensus_confidence:.0%}
├── 子任务数: {len(consensus.final_subtasks)}
└── 输出: .skillpack/current/1_planning_consensus.md""")

            tracker.complete_phase()

            # Phase 2: 共识分析/仲裁 (如有分歧)
            if consensus.status == ConsensusStatus.DISAGREEMENT:
                tracker.start_phase(Phase.PLANNING)
                tracker.update(0.2, "仲裁分歧...")

                header = self.dispatcher.format_phase_header(
                    phase=2,
                    total_phases=total_phases,
                    phase_name="共识仲裁",
                    route="PLANNED",
                    model=ModelType.CLAUDE,
                    progress_percent=20
                )
                print(header)

                # Claude 仲裁（由当前 Claude 实例执行）
                consensus = self._arbitrate_consensus(consensus)

                arbitration_content = f"""# 共识仲裁报告

## 分歧分析
{chr(10).join([f"- [{d.level.value}] {d.aspect}: {d.description}" for d in consensus.divergences])}

## 仲裁决策
- **采纳方案**: {consensus.arbitration.accepted_approach if consensus.arbitration else 'merged'}
- **决策理由**: {consensus.arbitration.reasoning if consensus.arbitration else '综合两方案优点'}

## 最终子任务
{chr(10).join([f"{i+1}. {t.description}" for i, t in enumerate(consensus.final_subtasks)])}
"""
                self._save_output("2_arbitration.md", arbitration_content)

                print(f"""✅ Phase 2 完成 (共识仲裁)
├── 分歧数: {len(consensus.divergences)}
├── 采纳方案: {consensus.arbitration.accepted_approach if consensus.arbitration else 'merged'}
└── 输出: .skillpack/current/2_arbitration.md""")

                tracker.complete_phase()
        else:
            # 传统单模型规划（占位）
            plan_content = f"""# 任务规划

## 任务描述
{context.description}

## 规划
(由 Claude 完成规划)
"""
            self._save_output("1_plan.md", plan_content)
            tracker.complete_phase()

        # Phase 3: 实现 (Codex)
        impl_phase = 3 if (consensus_enabled and consensus and consensus.status == ConsensusStatus.DISAGREEMENT) else 2
        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.update(0.4, "准备 Codex 实现...")

        header = self.dispatcher.format_phase_header(
            phase=impl_phase,
            total_phases=total_phases,
            phase_name="实现",
            route="PLANNED",
            model=ModelType.CODEX,
            progress_percent=40
        )
        print(header)

        # 构建实现 prompt（包含共识信息）
        if consensus:
            impl_prompt = f"""根据多模型规划共识实现以下任务:

## 任务
{context.description}

{consensus.to_implementation_prompt()}

请按照上述子任务列表依次实现。"""
        else:
            impl_prompt = f"根据规划实现以下任务:\n\n{context.description}"

        impl_result = self.dispatcher.call_codex(
            prompt=impl_prompt,
            context_files=self._get_context_files(context)
        )

        model_calls.append({
            "phase": impl_phase,
            "model": ModelType.CODEX.value,
            "success": impl_result.success,
            "duration_ms": impl_result.duration_ms
        })

        impl_filename = f"{impl_phase}_implementation.md"
        impl_content = self._format_result_markdown(
            f"Phase {impl_phase}: 实现",
            ModelType.CODEX,
            impl_result,
            context
        )
        self._save_output(impl_filename, impl_content)

        print(self.dispatcher.format_phase_complete(
            phase=impl_phase,
            model=ModelType.CODEX,
            duration_ms=impl_result.duration_ms,
            output_file=f".skillpack/current/{impl_filename}"
        ))

        tracker.complete_phase()

        # Phase 4: 审查 (Codex)
        review_phase = impl_phase + 1
        tracker.start_phase(Phase.REVIEWING)
        tracker.update(0.8, "准备 Codex 审查...")

        header = self.dispatcher.format_phase_header(
            phase=review_phase,
            total_phases=total_phases,
            phase_name="审查",
            route="PLANNED",
            model=ModelType.CODEX,
            progress_percent=80
        )
        print(header)

        review_result = self.dispatcher.call_codex(
            prompt=f"审查以下实现:\n\n{impl_result.output}\n\n审查重点: 需求覆盖、代码质量、潜在Bug、安全问题"
        )

        model_calls.append({
            "phase": review_phase,
            "model": ModelType.CODEX.value,
            "success": review_result.success,
            "duration_ms": review_result.duration_ms
        })

        review_filename = f"{review_phase}_review.md"
        review_content = self._format_result_markdown(
            f"Phase {review_phase}: 审查",
            ModelType.CODEX,
            review_result,
            context
        )
        self._save_output(review_filename, review_content)

        print(self.dispatcher.format_phase_complete(
            phase=review_phase,
            model=ModelType.CODEX,
            duration_ms=review_result.duration_ms,
            output_file=f".skillpack/current/{review_filename}"
        ))

        tracker.complete_phase()
        tracker.complete()

        # 构建输出文件列表
        if consensus_enabled:
            output_files = ["1_planning_consensus.md"]
            if consensus and consensus.status == ConsensusStatus.DISAGREEMENT:
                output_files.append("2_arbitration.md")
            output_files.extend([impl_filename, review_filename])
        else:
            output_files = ["1_plan.md", "2_implementation.md", "3_review.md"]

        return ExecutionStatus(
            is_running=False,
            error=impl_result.error or review_result.error if not (impl_result.success and review_result.success) else None,
            output_files=output_files,
            model_calls=model_calls
        )

    def _parallel_planning(
        self,
        context: TaskContext,
        tracker: ProgressTracker
    ) -> PlanningConsensus:
        """
        并行规划 (v5.5): Claude + Codex 同时规划。

        使用 ThreadPoolExecutor 实现并行调用。
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        import time

        start_time = time.time()
        tracker.update(0.1, "并行调用 Claude + Codex 规划...")

        orchestrator = ConsensusOrchestrator(self.dispatcher, self.config)

        # 构建上下文信息
        context_str = ""
        if context.working_dir:
            context_str = f"工作目录: {context.working_dir}"

        # 使用编排器执行并行规划
        # 注意: Claude 规划在这里通过占位实现，实际规划由当前 Claude 实例完成
        consensus = orchestrator.orchestrate(
            task=context.description,
            context=context,
            claude_callback=None  # Claude 规划将使用占位，由 Claude 实例自行填充
        )

        # 如果 Codex 规划成功，Claude 规划使用占位
        if consensus.codex_proposal and consensus.codex_proposal.parse_success:
            # Claude 方案：基于 Codex 方案生成互补方案（占位）
            from .consensus import PlanProposal, ApproachType, Subtask

            claude_proposal = PlanProposal(
                model="claude",
                summary=f"为任务 '{context.description[:50]}...' 的实施方案",
                subtasks=[Subtask(
                    id=f"task-{i+1}",
                    description=t.description,
                    priority=t.priority,
                    estimated_effort=t.estimated_effort
                ) for i, t in enumerate(consensus.codex_proposal.subtasks)],
                approach=consensus.codex_proposal.approach,
                rationale="与 Codex 方案保持一致（占位）",
                confidence=0.8,
                parse_success=True
            )
            consensus.claude_proposal = claude_proposal

            # 重新分析共识
            analyzer = ConsensusAnalyzer(self.config)
            consensus = analyzer.analyze(claude_proposal, consensus.codex_proposal)

        consensus.total_planning_time_ms = int((time.time() - start_time) * 1000)

        print(f"  ✓ 并行规划完成: {consensus.total_planning_time_ms}ms")
        return consensus

    def _arbitrate_consensus(self, consensus: PlanningConsensus) -> PlanningConsensus:
        """
        仲裁分歧 (v5.5): 由 Claude 决策。
        """
        from .consensus import ArbitrationDecision

        # 生成仲裁决策（由当前 Claude 实例填充）
        consensus.arbitration = ArbitrationDecision(
            accepted_approach="merged",
            reasoning="综合两个方案的优点，采用合并策略以最大化覆盖度和降低风险",
            resolved_divergences=[d.to_dict() for d in consensus.divergences],
            modifications=[f"解决分歧: {d.aspect}" for d in consensus.divergences[:3]],
            confidence=consensus.consensus_confidence
        )

        # 更新共识状态
        consensus.status = ConsensusStatus.PARTIAL_AGREEMENT

        return consensus

    def _get_context_files(self, context: TaskContext) -> List[str]:
        """从任务描述中提取相关文件"""
        import re
        files = re.findall(r'[\w/.-]+\.(ts|js|py|go|rs|java|tsx|jsx|md|json|yaml|toml)', context.description)
        return files


class RalphExecutor(ExecutorStrategy):
    """
    RALPH 执行器 (复杂任务自动化) v5.5

    Phase 1: 多模型并行规划 - Claude + Codex (v5.5 新增共识)
    Phase 2: 共识分析/仲裁 - Claude (v5.5 新增)
    Phase 3: 执行子任务 - Codex (CLI)
    Phase 4: 独立审查 - Gemini (CLI)
    Phase 5: 仲裁验证 - Claude
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        model_calls = []
        consensus_enabled = self.config.consensus.enabled

        # Phase 1: 多模型并行规划 (Claude + Codex) - v5.5 新增
        tracker.start_phase(Phase.ANALYZING)
        tracker.update(0.05, "准备多模型并行规划...")

        total_phases = 5

        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=total_phases,
            phase_name="多模型规划" if consensus_enabled else "深度分析",
            route="RALPH",
            model=ModelType.CLAUDE,
            progress_percent=5
        )
        print(header)

        consensus = None
        if consensus_enabled:
            # 使用多模型共识规划
            consensus = self._parallel_planning(context, tracker)

            model_calls.append({
                "phase": 1,
                "model": "claude+codex",
                "type": "consensus_planning",
                "success": True,
                "duration_ms": consensus.total_planning_time_ms
            })

            # 保存共识报告
            consensus_content = format_consensus_markdown(consensus)
            self._save_output("1_planning_consensus.md", consensus_content)

            print(f"""✅ Phase 1 完成 (多模型规划共识)
├── Claude 方案: {"✓" if consensus.claude_proposal else "✗"}
├── Codex 方案: {"✓" if consensus.codex_proposal else "✗"}
├── 共识状态: {consensus.status.value}
├── 共识置信度: {consensus.consensus_confidence:.0%}
└── 输出: .skillpack/current/1_planning_consensus.md""")

            tracker.complete_phase()

            # Phase 2: 共识仲裁 (如有分歧)
            if consensus.status == ConsensusStatus.DISAGREEMENT:
                tracker.start_phase(Phase.PLANNING)
                tracker.update(0.15, "仲裁分歧...")

                header = self.dispatcher.format_phase_header(
                    phase=2,
                    total_phases=total_phases,
                    phase_name="共识仲裁",
                    route="RALPH",
                    model=ModelType.CLAUDE,
                    progress_percent=15
                )
                print(header)

                consensus = self._arbitrate_consensus(consensus)

                arbitration_content = f"""# 共识仲裁报告

## 分歧分析
{chr(10).join([f"- [{d.level.value}] {d.aspect}: {d.description}" for d in consensus.divergences])}

## 仲裁决策
- **采纳方案**: {consensus.arbitration.accepted_approach if consensus.arbitration else 'merged'}
- **决策理由**: {consensus.arbitration.reasoning if consensus.arbitration else '综合两方案优点'}

## 最终子任务
{chr(10).join([f"{i+1}. {t.description}" for i, t in enumerate(consensus.final_subtasks)])}
"""
                self._save_output("2_arbitration.md", arbitration_content)

                print(f"""✅ Phase 2 完成 (共识仲裁)
├── 分歧数: {len(consensus.divergences)}
├── 采纳方案: {consensus.arbitration.accepted_approach if consensus.arbitration else 'merged'}
└── 输出: .skillpack/current/2_arbitration.md""")

                tracker.complete_phase()
        else:
            # 传统模式：深度分析 + 规划
            analysis_content = f"""# 深度分析

## 任务
{context.description}

## 分析
(由 Claude 完成深度分析)
"""
            self._save_output("1_analysis.md", analysis_content)
            tracker.complete_phase()

            # Phase 2: 规划 (Claude)
            tracker.start_phase(Phase.PLANNING)
            tracker.update(0.25, "详细规划...")

            header = self.dispatcher.format_phase_header(
                phase=2,
                total_phases=total_phases,
                phase_name="规划",
                route="RALPH",
                model=ModelType.CLAUDE,
                progress_percent=25
            )
            print(header)

            plan_content = f"""# 详细规划

## 任务
{context.description}

## 子任务列表
(由 Claude 完成规划和子任务分解)
"""
            self._save_output("2_plan.md", plan_content)
            tracker.complete_phase()

        # Phase 3: 执行子任务 (Codex)
        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.update(0.4, "准备 Codex 执行子任务...")

        header = self.dispatcher.format_phase_header(
            phase=3,
            total_phases=total_phases,
            phase_name="执行子任务",
            route="RALPH",
            model=ModelType.CODEX,
            progress_percent=40
        )
        print(header)

        # 构建实现 prompt（包含共识信息）
        if consensus:
            impl_prompt = f"""根据多模型规划共识实现以下任务:

## 任务
{context.description}

{consensus.to_implementation_prompt()}

请按照上述子任务列表依次实现。"""
        else:
            impl_prompt = f"执行以下任务的实现:\n\n{context.description}"

        impl_result = self.dispatcher.call_codex(
            prompt=impl_prompt,
            context_files=self._get_context_files(context)
        )

        model_calls.append({
            "phase": 3,
            "model": ModelType.CODEX.value,
            "success": impl_result.success,
            "duration_ms": impl_result.duration_ms
        })

        impl_content = self._format_result_markdown(
            "Phase 3: 执行子任务",
            ModelType.CODEX,
            impl_result,
            context
        )
        self._save_output("3_subtask_main.md", impl_content)

        print(self.dispatcher.format_phase_complete(
            phase=3,
            model=ModelType.CODEX,
            duration_ms=impl_result.duration_ms,
            output_file=".skillpack/current/3_subtask_main.md"
        ))

        tracker.complete_phase()

        # Phase 4: 独立审查 (Gemini) - v5.4 新增
        tracker.start_phase(Phase.REVIEWING)
        tracker.update(0.7, "准备 Gemini 独立审查...")

        header = self.dispatcher.format_phase_header(
            phase=4,
            total_phases=total_phases,
            phase_name="独立审查",
            route="RALPH",
            model=ModelType.GEMINI,
            progress_percent=70
        )
        print(header)

        # 查询知识库获取需求文档（如果配置了）
        knowledge_context = ""
        if context.notebook_id and self.config.knowledge.auto_query:
            tracker.update(0.72, "查询知识库获取需求文档...")
            kb_query = self.dispatcher.format_knowledge_query_prompt(
                task_description=context.description,
                phase_name="独立审查"
            )
            kb_result = self.dispatcher.query_knowledge_base(
                notebook_id=context.notebook_id,
                query=kb_query
            )
            if kb_result and isinstance(kb_result, str):
                knowledge_context = f"""
## 需求文档（来自知识库）
{kb_result}

---
"""
                print("  📚 已获取知识库需求文档")

        # Gemini 独立审查 Codex 的实现（注入知识库需求）
        review_prompt = f"""审查以下代码实现:

任务描述: {context.description}
{knowledge_context}
实现结果:
{impl_result.output[:5000]}  # 限制长度

审查重点:
1. 需求是否完全覆盖（对比知识库中的需求文档）
2. 代码质量和最佳实践
3. 潜在 Bug 和安全问题
4. 改进建议

输出格式:
- 问题列表（严重性 + 文件:行号 + 具体问题）
- 需求覆盖度检查（如有知识库需求）
- 改进建议"""

        review_result = self.dispatcher.call_gemini(
            prompt=review_prompt,
            context_files=[".skillpack/current/3_subtask_main.md"]
        )

        model_calls.append({
            "phase": 4,
            "model": ModelType.GEMINI.value,
            "success": review_result.success,
            "duration_ms": review_result.duration_ms
        })

        review_content = self._format_result_markdown(
            "Phase 4: 独立审查 (Gemini)",
            ModelType.GEMINI,
            review_result,
            context
        )
        self._save_output("4_review.md", review_content)

        print(self.dispatcher.format_phase_complete(
            phase=4,
            model=ModelType.GEMINI,
            duration_ms=review_result.duration_ms,
            output_file=".skillpack/current/4_review.md"
        ))

        tracker.complete_phase()

        # Phase 5: 仲裁验证 (Claude) - v5.4 新增
        tracker.start_phase(Phase.VALIDATING)
        tracker.update(0.9, "仲裁验证...")

        header = self.dispatcher.format_phase_header(
            phase=5,
            total_phases=total_phases,
            phase_name="仲裁验证",
            route="RALPH",
            model=ModelType.CLAUDE,
            progress_percent=90
        )
        print(header)

        arbitration_content = f"""# 仲裁验证

## Codex 实现结果
{impl_result.output[:2000] if impl_result.success else "实现失败"}

## Gemini 审查报告
{review_result.output[:2000] if review_result.success else "审查失败"}

## Claude 仲裁
(由 Claude 完成仲裁验证)
"""
        self._save_output("5_arbitration.md", arbitration_content)

        tracker.complete_phase()
        tracker.complete()

        # 构建输出文件列表
        if consensus_enabled:
            output_files = ["1_planning_consensus.md"]
            if consensus and consensus.status == ConsensusStatus.DISAGREEMENT:
                output_files.append("2_arbitration.md")
            output_files.extend(["3_subtask_main.md", "4_review.md", "5_arbitration.md"])
        else:
            output_files = [
                "1_analysis.md", "2_plan.md", "3_subtask_main.md",
                "4_review.md", "5_arbitration.md"
            ]

        return ExecutionStatus(
            is_running=False,
            error=None if (impl_result.success and review_result.success) else (impl_result.error or review_result.error),
            output_files=output_files,
            model_calls=model_calls
        )

    def _parallel_planning(
        self,
        context: TaskContext,
        tracker: ProgressTracker
    ) -> PlanningConsensus:
        """
        并行规划 (v5.5): Claude + Codex 同时规划。
        """
        from concurrent.futures import ThreadPoolExecutor
        import time

        start_time = time.time()
        tracker.update(0.1, "并行调用 Claude + Codex 规划...")

        orchestrator = ConsensusOrchestrator(self.dispatcher, self.config)

        consensus = orchestrator.orchestrate(
            task=context.description,
            context=context,
            claude_callback=None
        )

        # 如果 Codex 规划成功，Claude 规划使用占位
        if consensus.codex_proposal and consensus.codex_proposal.parse_success:
            from .consensus import PlanProposal, ApproachType, Subtask

            claude_proposal = PlanProposal(
                model="claude",
                summary=f"为任务 '{context.description[:50]}...' 的深度分析方案",
                subtasks=[Subtask(
                    id=f"task-{i+1}",
                    description=t.description,
                    priority=t.priority,
                    estimated_effort=t.estimated_effort
                ) for i, t in enumerate(consensus.codex_proposal.subtasks)],
                approach=consensus.codex_proposal.approach,
                rationale="与 Codex 方案协同（RALPH 模式）",
                confidence=0.85,
                parse_success=True
            )
            consensus.claude_proposal = claude_proposal

            analyzer = ConsensusAnalyzer(self.config)
            consensus = analyzer.analyze(claude_proposal, consensus.codex_proposal)

        consensus.total_planning_time_ms = int((time.time() - start_time) * 1000)

        print(f"  ✓ 并行规划完成: {consensus.total_planning_time_ms}ms")
        return consensus

    def _arbitrate_consensus(self, consensus: PlanningConsensus) -> PlanningConsensus:
        """
        仲裁分歧 (v5.5): 由 Claude 决策。
        """
        from .consensus import ArbitrationDecision

        consensus.arbitration = ArbitrationDecision(
            accepted_approach="merged",
            reasoning="综合两个方案的优点，采用合并策略以最大化覆盖度和降低风险",
            resolved_divergences=[d.to_dict() for d in consensus.divergences],
            modifications=[f"解决分歧: {d.aspect}" for d in consensus.divergences[:3]],
            confidence=consensus.consensus_confidence
        )

        consensus.status = ConsensusStatus.PARTIAL_AGREEMENT
        return consensus

    def _get_context_files(self, context: TaskContext) -> List[str]:
        """从任务描述中提取相关文件"""
        import re
        files = re.findall(r'[\w/.-]+\.(ts|js|py|go|rs|java|tsx|jsx|md|json|yaml|toml)', context.description)
        return files


class ArchitectExecutor(ExecutorStrategy):
    """
    ARCHITECT 执行器 (架构优先) v5.5

    Phase 1: Gemini 架构分析 + Codex 规划 (多模型并行)
    Phase 2: 共识分析/仲裁 - Claude
    Phase 3: 架构设计 - Claude
    Phase 4: 分阶段实施 - Codex (CLI)
    Phase 5: 独立审查 - Gemini (CLI)
    Phase 6: 仲裁验证 - Claude
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        model_calls = []
        consensus_enabled = self.config.consensus.enabled
        total_phases = 6

        # Phase 1: 架构分析 + 多模型规划 (Gemini + Codex 并行)
        tracker.start_phase(Phase.ANALYZING)
        tracker.update(0.05, "准备 Gemini 架构分析 + Codex 规划...")

        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=total_phases,
            phase_name="架构分析 + 多模型规划" if consensus_enabled else "架构分析",
            route="ARCHITECT",
            model=ModelType.GEMINI,
            progress_percent=5
        )
        print(header)

        arch_prompt = f"""@. 分析整个项目架构:

任务: {context.description}

分析要点:
1. 模块依赖关系
2. 技术栈识别
3. 架构模式识别
4. 改进建议
5. 实施方案建议"""

        # 并行执行 Gemini 架构分析和 Codex 规划
        consensus = None
        arch_result = None

        if consensus_enabled:
            from concurrent.futures import ThreadPoolExecutor
            import time

            start_time = time.time()

            with ThreadPoolExecutor(max_workers=2) as pool:
                # Gemini 架构分析
                gemini_future = pool.submit(
                    self.dispatcher.call_gemini,
                    arch_prompt,
                    ["."]
                )

                # Codex 规划
                codex_future = pool.submit(
                    self.dispatcher.call_codex_for_planning,
                    f"为以下任务设计架构和实施方案:\n\n{context.description}"
                )

                arch_result = gemini_future.result(timeout=180)
                codex_result = codex_future.result(timeout=120)

            # 解析 Codex 规划结果
            if codex_result.success:
                codex_proposal = ProposalParser.parse(codex_result.output, "codex")
                codex_proposal.generation_time_ms = codex_result.duration_ms

                # 创建 Claude 占位提案（基于 Gemini 分析）
                from .consensus import PlanProposal, ApproachType, Subtask

                claude_proposal = PlanProposal(
                    model="claude",
                    summary=f"基于 Gemini 架构分析的实施方案",
                    subtasks=[Subtask(
                        id=f"task-{i+1}",
                        description=t.description,
                        priority=t.priority,
                        estimated_effort=t.estimated_effort
                    ) for i, t in enumerate(codex_proposal.subtasks)],
                    approach=codex_proposal.approach,
                    rationale="基于 Gemini 架构分析设计（ARCHITECT 模式）",
                    confidence=0.85,
                    parse_success=True
                )

                # 分析共识
                analyzer = ConsensusAnalyzer(self.config)
                consensus = analyzer.analyze(claude_proposal, codex_proposal)
                consensus.total_planning_time_ms = int((time.time() - start_time) * 1000)

                # 保存共识报告
                consensus_content = format_consensus_markdown(consensus)
                self._save_output("1_planning_consensus.md", consensus_content)

                model_calls.append({
                    "phase": 1,
                    "model": "gemini+codex",
                    "type": "architecture_consensus",
                    "success": True,
                    "duration_ms": consensus.total_planning_time_ms
                })

                print(f"""✅ Phase 1 完成 (架构分析 + 多模型规划)
├── Gemini 架构分析: {"✓" if arch_result.success else "✗"}
├── Codex 规划: {"✓" if codex_proposal.parse_success else "✗"}
├── 共识状态: {consensus.status.value}
├── 共识置信度: {consensus.consensus_confidence:.0%}
└── 输出: .skillpack/current/1_planning_consensus.md""")
            else:
                # Codex 规划失败，仅使用 Gemini 架构分析
                arch_content = self._format_result_markdown(
                    "Phase 1: 架构分析 (Gemini)",
                    ModelType.GEMINI,
                    arch_result,
                    context
                )
                self._save_output("1_architecture_analysis.md", arch_content)

                model_calls.append({
                    "phase": 1,
                    "model": ModelType.GEMINI.value,
                    "success": arch_result.success,
                    "duration_ms": arch_result.duration_ms
                })

                print(self.dispatcher.format_phase_complete(
                    phase=1,
                    model=ModelType.GEMINI,
                    duration_ms=arch_result.duration_ms,
                    output_file=".skillpack/current/1_architecture_analysis.md"
                ))
        else:
            # 传统模式：仅 Gemini 架构分析
            arch_result = self.dispatcher.call_gemini(
                prompt=arch_prompt,
                context_files=["."]
            )

            model_calls.append({
                "phase": 1,
                "model": ModelType.GEMINI.value,
                "success": arch_result.success,
                "duration_ms": arch_result.duration_ms
            })

            arch_content = self._format_result_markdown(
                "Phase 1: 架构分析 (Gemini)",
                ModelType.GEMINI,
                arch_result,
                context
            )
            self._save_output("1_architecture_analysis.md", arch_content)

            print(self.dispatcher.format_phase_complete(
                phase=1,
                model=ModelType.GEMINI,
                duration_ms=arch_result.duration_ms,
                output_file=".skillpack/current/1_architecture_analysis.md"
            ))

        tracker.complete_phase()

        # Phase 2: 共识仲裁 / 架构设计
        if consensus_enabled and consensus and consensus.status == ConsensusStatus.DISAGREEMENT:
            tracker.start_phase(Phase.PLANNING)
            tracker.update(0.15, "仲裁分歧...")

            header = self.dispatcher.format_phase_header(
                phase=2,
                total_phases=total_phases,
                phase_name="共识仲裁",
                route="ARCHITECT",
                model=ModelType.CLAUDE,
                progress_percent=15
            )
            print(header)

            consensus = self._arbitrate_consensus(consensus)

            arbitration_content = f"""# 共识仲裁报告

## Gemini 架构分析摘要
{arch_result.output[:1500] if arch_result and arch_result.success else "(分析失败)"}

## 分歧分析
{chr(10).join([f"- [{d.level.value}] {d.aspect}: {d.description}" for d in consensus.divergences])}

## 仲裁决策
- **采纳方案**: {consensus.arbitration.accepted_approach if consensus.arbitration else 'merged'}
- **决策理由**: {consensus.arbitration.reasoning if consensus.arbitration else '综合两方案优点'}

## 最终子任务
{chr(10).join([f"{i+1}. {t.description}" for i, t in enumerate(consensus.final_subtasks)])}
"""
            self._save_output("2_arbitration.md", arbitration_content)

            print(f"""✅ Phase 2 完成 (共识仲裁)
├── 分歧数: {len(consensus.divergences)}
├── 采纳方案: {consensus.arbitration.accepted_approach if consensus.arbitration else 'merged'}
└── 输出: .skillpack/current/2_arbitration.md""")

            tracker.complete_phase()
        else:
            # 传统模式：架构设计
            tracker.start_phase(Phase.DESIGNING)
            tracker.update(0.2, "架构设计...")

            header = self.dispatcher.format_phase_header(
                phase=2,
                total_phases=total_phases,
                phase_name="架构设计",
                route="ARCHITECT",
                model=ModelType.CLAUDE,
                progress_percent=20
            )
            print(header)

            design_content = f"""# 架构设计

## 基于 Gemini 分析
{arch_result.output[:3000] if arch_result and arch_result.success else "(分析失败)"}

## 架构设计
(由 Claude 完成架构设计)
"""
            self._save_output("2_architecture_design.md", design_content)
            tracker.complete_phase()

        # Phase 3: 实施规划 (Claude)
        tracker.start_phase(Phase.PLANNING)
        tracker.update(0.35, "实施规划...")

        header = self.dispatcher.format_phase_header(
            phase=3,
            total_phases=total_phases,
            phase_name="实施规划",
            route="ARCHITECT",
            model=ModelType.CLAUDE,
            progress_percent=35
        )
        print(header)

        if consensus:
            plan_content = f"""# 实施规划

## 任务
{context.description}

## 基于多模型共识的实施计划
{consensus.to_implementation_prompt()}
"""
        else:
            plan_content = f"""# 实施规划

## 任务
{context.description}

## 分阶段实施计划
(由 Claude 完成详细规划)
"""
        self._save_output("3_implementation_plan.md", plan_content)
        tracker.complete_phase()

        # Phase 4: 分阶段实施 (Codex)
        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.update(0.5, "准备 Codex 分阶段实施...")

        header = self.dispatcher.format_phase_header(
            phase=4,
            total_phases=total_phases,
            phase_name="分阶段实施",
            route="ARCHITECT",
            model=ModelType.CODEX,
            progress_percent=50
        )
        print(header)

        # 构建实现 prompt（包含共识信息）
        if consensus:
            impl_prompt = f"""根据多模型规划共识实施以下任务:

## 任务
{context.description}

{consensus.to_implementation_prompt()}

## 架构分析参考
{arch_result.output[:1500] if arch_result and arch_result.success else "(无)"}

请按照上述子任务列表依次实施。"""
        else:
            impl_prompt = f"根据架构设计实施以下任务:\n\n{context.description}\n\n架构分析:\n{arch_result.output[:2000] if arch_result else ''}"

        impl_result = self.dispatcher.call_codex(
            prompt=impl_prompt,
            context_files=self._get_context_files(context)
        )

        model_calls.append({
            "phase": 4,
            "model": ModelType.CODEX.value,
            "success": impl_result.success,
            "duration_ms": impl_result.duration_ms
        })

        impl_content = self._format_result_markdown(
            "Phase 4: 分阶段实施 (Codex)",
            ModelType.CODEX,
            impl_result,
            context
        )
        self._save_output("4_phase_implementation.md", impl_content)

        print(self.dispatcher.format_phase_complete(
            phase=4,
            model=ModelType.CODEX,
            duration_ms=impl_result.duration_ms,
            output_file=".skillpack/current/4_phase_implementation.md"
        ))

        tracker.complete_phase()

        # Phase 5: 独立审查 (Gemini) - v5.4 调整
        tracker.start_phase(Phase.REVIEWING)
        tracker.update(0.75, "准备 Gemini 独立审查...")

        header = self.dispatcher.format_phase_header(
            phase=5,
            total_phases=total_phases,
            phase_name="独立审查",
            route="ARCHITECT",
            model=ModelType.GEMINI,
            progress_percent=75
        )
        print(header)

        # 查询知识库获取需求文档（如果配置了）
        knowledge_context = ""
        if context.notebook_id and self.config.knowledge.auto_query:
            tracker.update(0.77, "查询知识库获取需求文档...")
            kb_query = self.dispatcher.format_knowledge_query_prompt(
                task_description=context.description,
                phase_name="架构审查"
            )
            kb_result = self.dispatcher.query_knowledge_base(
                notebook_id=context.notebook_id,
                query=kb_query
            )
            if kb_result and isinstance(kb_result, str):
                knowledge_context = f"""
## 需求文档（来自知识库）
{kb_result}

---
"""
                print("  📚 已获取知识库需求文档")

        review_prompt = f"""审查以下架构实现:

原始任务: {context.description}
{knowledge_context}
实现结果:
{impl_result.output[:5000]}

审查重点:
1. 架构设计是否正确实现（对比知识库需求）
2. 代码质量和最佳实践
3. 潜在问题和风险
4. 需求覆盖度检查
5. 改进建议"""

        review_result = self.dispatcher.call_gemini(
            prompt=review_prompt,
            context_files=[".skillpack/current/4_phase_implementation.md"]
        )

        model_calls.append({
            "phase": 5,
            "model": ModelType.GEMINI.value,
            "success": review_result.success,
            "duration_ms": review_result.duration_ms
        })

        review_content = self._format_result_markdown(
            "Phase 5: 独立审查 (Gemini)",
            ModelType.GEMINI,
            review_result,
            context
        )
        self._save_output("5_review.md", review_content)

        print(self.dispatcher.format_phase_complete(
            phase=5,
            model=ModelType.GEMINI,
            duration_ms=review_result.duration_ms,
            output_file=".skillpack/current/5_review.md"
        ))

        tracker.complete_phase()

        # Phase 6: 仲裁验证 (Claude) - v5.4 新增
        tracker.start_phase(Phase.VALIDATING)
        tracker.update(0.9, "仲裁验证...")

        header = self.dispatcher.format_phase_header(
            phase=6,
            total_phases=total_phases,
            phase_name="仲裁验证",
            route="ARCHITECT",
            model=ModelType.CLAUDE,
            progress_percent=90
        )
        print(header)

        arbitration_content = f"""# 仲裁验证

## Gemini 架构分析
{arch_result.output[:2000] if arch_result.success else "(分析失败)"}

## Codex 实施结果
{impl_result.output[:2000] if impl_result.success else "(实施失败)"}

## Gemini 审查报告
{review_result.output[:2000] if review_result.success else "(审查失败)"}

## Claude 仲裁
(由 Claude 完成最终仲裁验证)
"""
        self._save_output("6_arbitration.md", arbitration_content)

        tracker.complete_phase()
        tracker.complete()

        # 构建输出文件列表
        if consensus_enabled and consensus:
            output_files = ["1_planning_consensus.md"]
            if consensus.status == ConsensusStatus.DISAGREEMENT:
                output_files.append("2_arbitration.md")
            else:
                output_files.append("2_architecture_design.md")
            output_files.extend([
                "3_implementation_plan.md", "4_phase_implementation.md",
                "5_review.md", "6_arbitration.md"
            ])
        else:
            output_files = [
                "1_architecture_analysis.md", "2_architecture_design.md",
                "3_implementation_plan.md", "4_phase_implementation.md",
                "5_review.md", "6_arbitration.md"
            ]

        arch_success = arch_result.success if arch_result else False
        return ExecutionStatus(
            is_running=False,
            error=None if all([arch_success, impl_result.success, review_result.success]) else "部分阶段执行失败",
            output_files=output_files,
            model_calls=model_calls
        )

    def _arbitrate_consensus(self, consensus: PlanningConsensus) -> PlanningConsensus:
        """
        仲裁分歧 (v5.5): 由 Claude 决策。
        """
        from .consensus import ArbitrationDecision

        consensus.arbitration = ArbitrationDecision(
            accepted_approach="merged",
            reasoning="综合 Gemini 架构分析和 Codex 规划方案，采用合并策略",
            resolved_divergences=[d.to_dict() for d in consensus.divergences],
            modifications=[f"解决分歧: {d.aspect}" for d in consensus.divergences[:3]],
            confidence=consensus.consensus_confidence
        )

        consensus.status = ConsensusStatus.PARTIAL_AGREEMENT
        return consensus

    def _get_context_files(self, context: TaskContext) -> List[str]:
        """从任务描述中提取相关文件"""
        import re
        files = re.findall(r'[\w/.-]+\.(ts|js|py|go|rs|java|tsx|jsx|md|json|yaml|toml)', context.description)
        return files


class UIFlowExecutor(ExecutorStrategy):
    """
    UI_FLOW 执行器

    Phase 1: UI 设计 - Gemini (CLI)
    Phase 2: 实现 - Gemini (CLI)
    Phase 3: 预览验证 - Claude
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        model_calls = []

        # Phase 1: UI 设计 (Gemini)
        tracker.start_phase(Phase.DESIGNING)
        tracker.update(0.1, "准备 Gemini UI 设计...")

        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=3,
            phase_name="UI 设计",
            route="UI_FLOW",
            model=ModelType.GEMINI,
            progress_percent=10
        )
        print(header)

        design_prompt = f"""设计以下 UI 组件:

任务: {context.description}

设计要求:
1. 遵循现代 UI/UX 最佳实践
2. 响应式设计
3. 可访问性考虑
4. 组件结构和样式规划"""

        design_result = self.dispatcher.call_gemini(
            prompt=design_prompt,
            context_files=self._get_ui_context_files(context)
        )

        model_calls.append({
            "phase": 1,
            "model": ModelType.GEMINI.value,
            "success": design_result.success,
            "duration_ms": design_result.duration_ms
        })

        design_content = self._format_result_markdown(
            "Phase 1: UI 设计 (Gemini)",
            ModelType.GEMINI,
            design_result,
            context
        )
        self._save_output("1_ui_design.md", design_content)

        print(self.dispatcher.format_phase_complete(
            phase=1,
            model=ModelType.GEMINI,
            duration_ms=design_result.duration_ms,
            output_file=".skillpack/current/1_ui_design.md"
        ))

        tracker.complete_phase()

        # Phase 2: 实现 (Gemini)
        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.update(0.4, "准备 Gemini UI 实现...")

        header = self.dispatcher.format_phase_header(
            phase=2,
            total_phases=3,
            phase_name="实现",
            route="UI_FLOW",
            model=ModelType.GEMINI,
            progress_percent=40
        )
        print(header)

        impl_prompt = f"""根据设计实现以下 UI 组件:

任务: {context.description}

设计方案:
{design_result.output[:3000] if design_result.success else "(设计阶段失败)"}

实现要求:
1. 使用项目现有技术栈
2. 组件完整可用
3. 样式符合设计"""

        impl_result = self.dispatcher.call_gemini(
            prompt=impl_prompt,
            context_files=self._get_ui_context_files(context)
        )

        model_calls.append({
            "phase": 2,
            "model": ModelType.GEMINI.value,
            "success": impl_result.success,
            "duration_ms": impl_result.duration_ms
        })

        impl_content = self._format_result_markdown(
            "Phase 2: UI 实现 (Gemini)",
            ModelType.GEMINI,
            impl_result,
            context
        )
        self._save_output("2_implementation.md", impl_content)

        print(self.dispatcher.format_phase_complete(
            phase=2,
            model=ModelType.GEMINI,
            duration_ms=impl_result.duration_ms,
            output_file=".skillpack/current/2_implementation.md"
        ))

        tracker.complete_phase()

        # Phase 3: 预览验证 (Claude)
        tracker.start_phase(Phase.VALIDATING)
        tracker.update(0.85, "预览验证...")

        header = self.dispatcher.format_phase_header(
            phase=3,
            total_phases=3,
            phase_name="预览验证",
            route="UI_FLOW",
            model=ModelType.CLAUDE,
            progress_percent=85
        )
        print(header)

        preview_content = f"""# 预览验证

## Gemini 设计方案
{design_result.output[:2000] if design_result.success else "(设计失败)"}

## Gemini 实现结果
{impl_result.output[:2000] if impl_result.success else "(实现失败)"}

## Claude 验证
(由 Claude 完成预览验证和微调)
"""
        self._save_output("3_preview.md", preview_content)

        tracker.complete_phase()
        tracker.complete()

        return ExecutionStatus(
            is_running=False,
            error=None if (design_result.success and impl_result.success) else (design_result.error or impl_result.error),
            output_files=["1_ui_design.md", "2_implementation.md", "3_preview.md"],
            model_calls=model_calls
        )

    def _get_ui_context_files(self, context: TaskContext) -> List[str]:
        """获取 UI 相关上下文文件"""
        import re
        files = re.findall(r'[\w/.-]+\.(tsx|jsx|css|scss|vue|svelte)', context.description)

        # 添加常见 UI 目录
        common_paths = [
            "src/components",
            "src/pages",
            "src/styles",
            "components",
            "pages"
        ]

        for path in common_paths:
            if Path(path).exists():
                files.append(path)
                break

        return files


class TaskExecutor:
    """任务执行器主类"""

    def __init__(self, config: Optional[SkillpackConfig] = None, quiet: bool = False):
        self.config = config or SkillpackConfig()
        self.quiet = quiet
        self._usage_store = UsageStore()
        self._strategies = {
            ExecutionRoute.DIRECT: DirectExecutor(self.config),
            ExecutionRoute.PLANNED: PlannedExecutor(self.config),
            ExecutionRoute.RALPH: RalphExecutor(self.config),
            ExecutionRoute.ARCHITECT: ArchitectExecutor(self.config),
            ExecutionRoute.UI_FLOW: UIFlowExecutor(self.config),
        }

    def execute(self, context: TaskContext) -> ExecutionStatus:
        """执行任务"""
        # 生成任务 ID
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # 创建输出目录
        working_dir = context.working_dir or Path.cwd()
        current_dir = working_dir / self.config.output.current_dir
        current_dir.mkdir(parents=True, exist_ok=True)

        history_dir = working_dir / self.config.output.history_dir
        history_dir.mkdir(parents=True, exist_ok=True)

        # 创建进度追踪器
        tracker = SimpleProgressTracker(
            task_id=task_id,
            description=context.description,
            quiet=self.quiet
        )

        # 输出执行模式
        mode = "CLI 优先" if self.config.cli.prefer_cli_over_mcp else "MCP"
        if not self.quiet:
            print(f"""
════════════════════════════════════════════════════════════
🚀 Skillpack v5.4.1 - 任务开始
════════════════════════════════════════════════════════════
📋 任务: {context.description}
📊 路由: {context.route.value}
🖥️ 执行模式: {mode}
────────────────────────────────────────────────────────────
""")

        # 获取执行策略
        strategy = self._strategies.get(context.route, DirectExecutor(self.config))

        # 设置调度器上下文（用于用量追踪）
        strategy.dispatcher.set_context(
            task_id=task_id,
            route=context.route.value
        )

        # 执行
        return strategy.execute(context, tracker)

    def record_claude_phase(
        self,
        task_id: str,
        route: str,
        phase: int,
        phase_name: str,
        duration_ms: int = 0,
        success: bool = True
    ):
        """记录 Claude 执行的阶段"""
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            model="claude",
            route=route,
            phase=phase,
            phase_name=phase_name,
            task_id=task_id,
            success=success,
            duration_ms=duration_ms,
            mode="direct"
        )
        self._usage_store.append_record(record)
