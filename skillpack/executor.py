"""
任务执行器

提供不同路由的执行策略，使用 ModelDispatcher 进行真实的模型调用。
v5.4.0: 集成 CLI 调度器，实现真实的 Codex/Gemini 调用。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import json
import time

from .models import TaskContext, ExecutionRoute, SkillpackConfig
from .dispatch import ModelDispatcher, ModelType, DispatchResult, get_dispatcher
from .ralph.dashboard import ProgressTracker, SimpleProgressTracker, Phase


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

    def __init__(self, config: SkillpackConfig):
        self.config = config
        self.dispatcher = get_dispatcher(config)
        self.output_dir = Path(config.output.current_dir)

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
    计划执行器 (PLANNED)

    Phase 1: 规划 - Claude
    Phase 2: 实现 - Codex (CLI)
    Phase 3: 审查 - Codex (CLI)
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        model_calls = []

        # Phase 1: 规划 (Claude)
        tracker.start_phase(Phase.PLANNING)
        tracker.update(0.1, "分析需求...")

        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=3,
            phase_name="规划",
            route="PLANNED",
            model=ModelType.CLAUDE,
            progress_percent=10
        )
        print(header)

        # Claude 规划（由调用方完成，这里保存占位输出）
        plan_content = f"""# 任务规划

## 任务描述
{context.description}

## 规划
(由 Claude 完成规划)
"""
        self._save_output("1_plan.md", plan_content)
        tracker.complete_phase()

        # Phase 2: 实现 (Codex)
        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.update(0.4, "准备 Codex 实现...")

        header = self.dispatcher.format_phase_header(
            phase=2,
            total_phases=3,
            phase_name="实现",
            route="PLANNED",
            model=ModelType.CODEX,
            progress_percent=40
        )
        print(header)

        impl_result = self.dispatcher.call_codex(
            prompt=f"根据规划实现以下任务:\n\n{context.description}",
            context_files=self._get_context_files(context)
        )

        model_calls.append({
            "phase": 2,
            "model": ModelType.CODEX.value,
            "success": impl_result.success,
            "duration_ms": impl_result.duration_ms
        })

        impl_content = self._format_result_markdown(
            "Phase 2: 实现",
            ModelType.CODEX,
            impl_result,
            context
        )
        self._save_output("2_implementation.md", impl_content)

        print(self.dispatcher.format_phase_complete(
            phase=2,
            model=ModelType.CODEX,
            duration_ms=impl_result.duration_ms,
            output_file=".skillpack/current/2_implementation.md"
        ))

        tracker.complete_phase()

        # Phase 3: 审查 (Codex)
        tracker.start_phase(Phase.REVIEWING)
        tracker.update(0.8, "准备 Codex 审查...")

        header = self.dispatcher.format_phase_header(
            phase=3,
            total_phases=3,
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
            "phase": 3,
            "model": ModelType.CODEX.value,
            "success": review_result.success,
            "duration_ms": review_result.duration_ms
        })

        review_content = self._format_result_markdown(
            "Phase 3: 审查",
            ModelType.CODEX,
            review_result,
            context
        )
        self._save_output("3_review.md", review_content)

        print(self.dispatcher.format_phase_complete(
            phase=3,
            model=ModelType.CODEX,
            duration_ms=review_result.duration_ms,
            output_file=".skillpack/current/3_review.md"
        ))

        tracker.complete_phase()
        tracker.complete()

        return ExecutionStatus(
            is_running=False,
            error=impl_result.error or review_result.error if not (impl_result.success and review_result.success) else None,
            output_files=["1_plan.md", "2_implementation.md", "3_review.md"],
            model_calls=model_calls
        )

    def _get_context_files(self, context: TaskContext) -> List[str]:
        """从任务描述中提取相关文件"""
        import re
        files = re.findall(r'[\w/.-]+\.(ts|js|py|go|rs|java|tsx|jsx|md|json|yaml|toml)', context.description)
        return files


class RalphExecutor(ExecutorStrategy):
    """
    RALPH 执行器 (复杂任务自动化) v5.4

    Phase 1: 深度分析 - Claude
    Phase 2: 规划 - Claude
    Phase 3: 执行子任务 - Codex (CLI)
    Phase 4: 独立审查 - Gemini (CLI) <- v5.4 新增
    Phase 5: 仲裁验证 - Claude <- v5.4 新增
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        model_calls = []

        # Phase 1: 深度分析 (Claude)
        tracker.start_phase(Phase.ANALYZING)
        tracker.update(0.1, "深度分析...")

        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=5,
            phase_name="深度分析",
            route="RALPH",
            model=ModelType.CLAUDE,
            progress_percent=10
        )
        print(header)

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
            total_phases=5,
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
            total_phases=5,
            phase_name="执行子任务",
            route="RALPH",
            model=ModelType.CODEX,
            progress_percent=40
        )
        print(header)

        impl_result = self.dispatcher.call_codex(
            prompt=f"执行以下任务的实现:\n\n{context.description}",
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
            total_phases=5,
            phase_name="独立审查",
            route="RALPH",
            model=ModelType.GEMINI,
            progress_percent=70
        )
        print(header)

        # Gemini 独立审查 Codex 的实现
        review_prompt = f"""审查以下代码实现:

任务描述: {context.description}

实现结果:
{impl_result.output[:5000]}  # 限制长度

审查重点:
1. 需求是否完全覆盖
2. 代码质量和最佳实践
3. 潜在 Bug 和安全问题
4. 改进建议

输出格式:
- 问题列表（严重性 + 文件:行号 + 具体问题）
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
            total_phases=5,
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

        return ExecutionStatus(
            is_running=False,
            error=None if (impl_result.success and review_result.success) else (impl_result.error or review_result.error),
            output_files=[
                "1_analysis.md", "2_plan.md", "3_subtask_main.md",
                "4_review.md", "5_arbitration.md"
            ],
            model_calls=model_calls
        )

    def _get_context_files(self, context: TaskContext) -> List[str]:
        """从任务描述中提取相关文件"""
        import re
        files = re.findall(r'[\w/.-]+\.(ts|js|py|go|rs|java|tsx|jsx|md|json|yaml|toml)', context.description)
        return files


class ArchitectExecutor(ExecutorStrategy):
    """
    ARCHITECT 执行器 (架构优先) v5.4

    Phase 1: 架构分析 - Gemini (CLI)
    Phase 2: 架构设计 - Claude
    Phase 3: 实施规划 - Claude
    Phase 4: 分阶段实施 - Codex (CLI)
    Phase 5: 独立审查 - Gemini (CLI) <- v5.4 调整
    Phase 6: 仲裁验证 - Claude <- v5.4 新增
    """

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        model_calls = []

        # Phase 1: 架构分析 (Gemini)
        tracker.start_phase(Phase.ANALYZING)
        tracker.update(0.05, "准备 Gemini 架构分析...")

        header = self.dispatcher.format_phase_header(
            phase=1,
            total_phases=6,
            phase_name="架构分析",
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

        # Phase 2: 架构设计 (Claude)
        tracker.start_phase(Phase.DESIGNING)
        tracker.update(0.2, "架构设计...")

        header = self.dispatcher.format_phase_header(
            phase=2,
            total_phases=6,
            phase_name="架构设计",
            route="ARCHITECT",
            model=ModelType.CLAUDE,
            progress_percent=20
        )
        print(header)

        design_content = f"""# 架构设计

## 基于 Gemini 分析
{arch_result.output[:3000] if arch_result.success else "(分析失败)"}

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
            total_phases=6,
            phase_name="实施规划",
            route="ARCHITECT",
            model=ModelType.CLAUDE,
            progress_percent=35
        )
        print(header)

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
            total_phases=6,
            phase_name="分阶段实施",
            route="ARCHITECT",
            model=ModelType.CODEX,
            progress_percent=50
        )
        print(header)

        impl_result = self.dispatcher.call_codex(
            prompt=f"根据架构设计实施以下任务:\n\n{context.description}\n\n架构分析:\n{arch_result.output[:2000]}",
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
            total_phases=6,
            phase_name="独立审查",
            route="ARCHITECT",
            model=ModelType.GEMINI,
            progress_percent=75
        )
        print(header)

        review_prompt = f"""审查以下架构实现:

原始任务: {context.description}

实现结果:
{impl_result.output[:5000]}

审查重点:
1. 架构设计是否正确实现
2. 代码质量和最佳实践
3. 潜在问题和风险
4. 改进建议"""

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
            total_phases=6,
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

        return ExecutionStatus(
            is_running=False,
            error=None if all([arch_result.success, impl_result.success, review_result.success]) else "部分阶段执行失败",
            output_files=[
                "1_architecture_analysis.md", "2_architecture_design.md",
                "3_implementation_plan.md", "4_phase_implementation.md",
                "5_review.md", "6_arbitration.md"
            ],
            model_calls=model_calls
        )

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
        self._strategies = {
            ExecutionRoute.DIRECT: DirectExecutor(self.config),
            ExecutionRoute.PLANNED: PlannedExecutor(self.config),
            ExecutionRoute.RALPH: RalphExecutor(self.config),
            ExecutionRoute.ARCHITECT: ArchitectExecutor(self.config),
            ExecutionRoute.UI_FLOW: UIFlowExecutor(self.config),
        }

    def execute(self, context: TaskContext) -> ExecutionStatus:
        """执行任务"""
        # 创建输出目录
        working_dir = context.working_dir or Path.cwd()
        current_dir = working_dir / self.config.output.current_dir
        current_dir.mkdir(parents=True, exist_ok=True)

        history_dir = working_dir / self.config.output.history_dir
        history_dir.mkdir(parents=True, exist_ok=True)

        # 创建进度追踪器
        tracker = SimpleProgressTracker(
            task_id="task",
            description=context.description,
            quiet=self.quiet
        )

        # 输出执行模式
        mode = "CLI 优先" if self.config.cli.prefer_cli_over_mcp else "MCP"
        if not self.quiet:
            print(f"""
════════════════════════════════════════════════════════════
🚀 Skillpack v5.4.0 - 任务开始
════════════════════════════════════════════════════════════
📋 任务: {context.description}
📊 路由: {context.route.value}
🖥️ 执行模式: {mode}
────────────────────────────────────────────────────────────
""")

        # 获取执行策略
        strategy = self._strategies.get(context.route, DirectExecutor(self.config))

        # 执行
        return strategy.execute(context, tracker)
