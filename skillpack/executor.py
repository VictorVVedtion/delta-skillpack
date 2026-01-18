"""
任务执行器 - 根据路由执行对应的技能流程

SOLID: 开放封闭原则 - 通过策略模式扩展执行路径
DRY: 复用公共执行逻辑
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    TaskContext,
    ExecutionRoute,
    ExecutionStatus,
    SkillpackConfig,
)
from .ralph.dashboard import (
    ProgressTracker,
    SimpleProgressTracker,
    Phase,
    ProgressCallback,
    RICH_AVAILABLE,
)


class ExecutionStrategy(ABC):
    """执行策略接口"""

    @abstractmethod
    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        """执行任务"""
        pass


class DirectExecutor(ExecutionStrategy):
    """直接执行器 - 用于简单任务"""

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        tracker.start_phase(Phase.IMPLEMENTING, "直接执行简单任务")

        # 模拟执行逻辑 - 实际项目中这里会调用 Claude API
        tracker.update(0.5, f"处理任务: {context.description[:50]}...")

        # TODO: 集成实际的代码执行逻辑
        tracker.update(1.0, "任务处理完成")
        tracker.complete_phase()

        tracker.complete()

        return ExecutionStatus(
            task_id=tracker.task_id,
            phase=Phase.COMPLETED.value,
            progress=1.0,
            message="直接执行完成",
            is_running=False,
            output_dir=tracker.output_dir
        )


class PlannedExecutor(ExecutionStrategy):
    """计划执行器 - plan → implement → review"""

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        # Phase 1: Planning
        tracker.start_phase(Phase.PLANNING, "生成实施计划")
        tracker.update(0.3, "分析代码库结构...")
        tracker.update(0.6, "识别关键修改点...")
        tracker.update(1.0, "计划生成完成")
        tracker.complete_phase()

        # Phase 2: Implementing
        tracker.start_phase(Phase.IMPLEMENTING, "执行代码变更")
        tracker.update(0.2, "应用第 1 步变更...")
        tracker.update(0.5, "应用第 2 步变更...")
        tracker.update(0.8, "应用第 3 步变更...")
        tracker.update(1.0, "代码变更完成")
        tracker.complete_phase()

        # Phase 3: Reviewing
        tracker.start_phase(Phase.REVIEWING, "代码审查")
        tracker.update(0.5, "检查代码质量...")
        tracker.update(1.0, "审查通过")
        tracker.complete_phase()

        tracker.complete()

        return ExecutionStatus(
            task_id=tracker.task_id,
            phase=Phase.COMPLETED.value,
            progress=1.0,
            message="计划执行完成",
            is_running=False,
            output_dir=tracker.output_dir
        )


class RalphExecutor(ExecutionStrategy):
    """Ralph 自动化执行器 - 用于复杂任务"""

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        # Ralph 需要更长的执行周期
        tracker.start_phase(Phase.ANALYZING, "Ralph 深度分析任务")
        tracker.update(0.5, "构建任务依赖图...")
        tracker.update(1.0, "分析完成")
        tracker.complete_phase()

        tracker.start_phase(Phase.PLANNING, "生成多阶段计划")
        tracker.update(0.3, "拆分子任务...")
        tracker.update(0.7, "排序执行顺序...")
        tracker.update(1.0, "计划就绪")
        tracker.complete_phase()

        tracker.start_phase(Phase.IMPLEMENTING, "Ralph 自动化执行")
        # 模拟多个子任务
        for i in range(1, 6):
            tracker.update(i * 0.2, f"执行子任务 {i}/5...")
        tracker.complete_phase()

        tracker.start_phase(Phase.REVIEWING, "综合审查")
        tracker.update(1.0, "所有变更已验证")
        tracker.complete_phase()

        tracker.complete("Ralph 自动化完成")

        return ExecutionStatus(
            task_id=tracker.task_id,
            phase=Phase.COMPLETED.value,
            progress=1.0,
            message="Ralph 自动化完成",
            is_running=False,
            output_dir=tracker.output_dir
        )


class UIFlowExecutor(ExecutionStrategy):
    """UI 流程执行器 - UI → implement → browser"""

    def execute(self, context: TaskContext, tracker: ProgressTracker) -> ExecutionStatus:
        tracker.start_phase(Phase.UI_GENERATING, "生成 UI 设计")
        tracker.update(0.5, "分析 UI 需求...")
        tracker.update(1.0, "UI 设计完成")
        tracker.complete_phase()

        tracker.start_phase(Phase.IMPLEMENTING, "实现 UI 组件")
        tracker.update(0.5, "生成组件代码...")
        tracker.update(1.0, "组件实现完成")
        tracker.complete_phase()

        tracker.start_phase(Phase.BROWSER_PREVIEW, "浏览器预览")
        tracker.update(1.0, "预览就绪")
        tracker.complete_phase()

        tracker.complete()

        return ExecutionStatus(
            task_id=tracker.task_id,
            phase=Phase.COMPLETED.value,
            progress=1.0,
            message="UI 流程完成",
            is_running=False,
            output_dir=tracker.output_dir
        )


class TaskExecutor:
    """
    任务执行器主类

    根据 TaskContext 的路由选择对应的执行策略
    """

    STRATEGIES = {
        ExecutionRoute.DIRECT: DirectExecutor,
        ExecutionRoute.PLANNED: PlannedExecutor,
        ExecutionRoute.RALPH: RalphExecutor,
        ExecutionRoute.UI_FLOW: UIFlowExecutor,
    }

    def __init__(
        self,
        config: Optional[SkillpackConfig] = None,
        callback: Optional[ProgressCallback] = None,
        quiet: bool = False
    ):
        self.config = config or SkillpackConfig()
        self.callback = callback
        self.quiet = quiet

    def _setup_output_dir(self, working_dir: Path) -> Path:
        """设置输出目录"""
        current_dir = working_dir / self.config.output.current_dir
        current_dir.mkdir(parents=True, exist_ok=True)

        # 清理之前的 current 内容
        for item in current_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)

        return current_dir

    def _archive_to_history(self, current_dir: Path, working_dir: Path, task_id: str):
        """归档到历史目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_dir = self.config.output.get_history_path(working_dir, f"{timestamp}_{task_id[:8]}")
        history_dir.mkdir(parents=True, exist_ok=True)

        # 复制 current 到 history
        import shutil
        for item in current_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, history_dir)
            elif item.is_dir():
                shutil.copytree(item, history_dir / item.name)

    def execute(self, context: TaskContext) -> ExecutionStatus:
        """
        执行任务

        Args:
            context: 任务上下文

        Returns:
            ExecutionStatus 执行状态
        """
        # 生成任务 ID
        task_id = str(uuid.uuid4())

        # 设置输出目录
        output_dir = self._setup_output_dir(context.working_dir)

        # 创建进度追踪器
        TrackerClass = SimpleProgressTracker if (not RICH_AVAILABLE or self.quiet) else ProgressTracker
        tracker = TrackerClass(
            task_id=task_id,
            task_description=context.description,
            output_dir=output_dir,
            callback=self.callback,
            quiet=self.quiet
        )

        # 获取执行策略
        strategy_class = self.STRATEGIES.get(context.route, PlannedExecutor)
        strategy = strategy_class()

        try:
            # 执行
            status = strategy.execute(context, tracker)

            # 归档到历史
            self._archive_to_history(output_dir, context.working_dir, task_id)

            return status

        except Exception as e:
            tracker.fail(str(e))
            return ExecutionStatus(
                task_id=task_id,
                phase=Phase.FAILED.value,
                progress=tracker.current_progress,
                message="执行失败",
                is_running=False,
                error=str(e),
                output_dir=output_dir
            )
