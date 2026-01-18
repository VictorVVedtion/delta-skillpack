"""
统一进度追踪器

SOLID: 单一职责 - 只负责进度显示和状态管理
KISS: 简单的 Rich 控制台输出
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, List
from enum import Enum

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class Phase(Enum):
    """执行阶段"""
    ANALYZING = "analyzing"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    REVIEWING = "reviewing"
    UI_GENERATING = "ui_generating"
    BROWSER_PREVIEW = "browser_preview"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseInfo:
    """阶段信息"""
    name: str
    icon: str
    description: str


PHASE_INFO = {
    Phase.ANALYZING: PhaseInfo("分析中", "🔍", "分析任务复杂度和路由"),
    Phase.PLANNING: PhaseInfo("规划中", "📋", "生成实施计划"),
    Phase.IMPLEMENTING: PhaseInfo("实现中", "⚙️", "执行代码变更"),
    Phase.REVIEWING: PhaseInfo("审查中", "👀", "代码审查和质量检查"),
    Phase.UI_GENERATING: PhaseInfo("UI生成", "🎨", "生成界面组件"),
    Phase.BROWSER_PREVIEW: PhaseInfo("预览中", "🌐", "浏览器预览"),
    Phase.COMPLETED: PhaseInfo("完成", "✅", "任务已完成"),
    Phase.FAILED: PhaseInfo("失败", "❌", "任务执行失败"),
}


@dataclass
class ProgressEvent:
    """进度事件"""
    phase: Phase
    progress: float  # 0.0 - 1.0
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Optional[str] = None


class ProgressCallback:
    """进度回调接口"""

    def on_phase_start(self, phase: Phase, message: str) -> None:
        pass

    def on_progress(self, phase: Phase, progress: float, message: str) -> None:
        pass

    def on_phase_complete(self, phase: Phase) -> None:
        pass

    def on_error(self, phase: Phase, error: str) -> None:
        pass


class ProgressTracker:
    """
    统一进度追踪器

    支持：
    - 实时进度面板显示
    - 阶段转换追踪
    - 事件历史记录
    - 回调通知
    """

    def __init__(
        self,
        task_id: str,
        task_description: str,
        output_dir: Optional[Path] = None,
        callback: Optional[ProgressCallback] = None,
        quiet: bool = False
    ):
        self.task_id = task_id
        self.task_description = task_description
        self.output_dir = output_dir
        self.callback = callback
        self.quiet = quiet

        self.current_phase: Phase = Phase.ANALYZING
        self.current_progress: float = 0.0
        self.events: List[ProgressEvent] = []
        self.start_time = datetime.now()
        self.error: Optional[str] = None

        if RICH_AVAILABLE and not quiet:
            self.console = Console()
        else:
            self.console = None

    def _emit_event(self, phase: Phase, progress: float, message: str, details: Optional[str] = None):
        """记录事件"""
        event = ProgressEvent(
            phase=phase,
            progress=progress,
            message=message,
            details=details
        )
        self.events.append(event)

    def start_phase(self, phase: Phase, message: Optional[str] = None):
        """开始新阶段"""
        self.current_phase = phase
        self.current_progress = 0.0

        info = PHASE_INFO[phase]
        msg = message or info.description

        self._emit_event(phase, 0.0, msg)

        if self.callback:
            self.callback.on_phase_start(phase, msg)

        if self.console and not self.quiet:
            self.console.print(f"{info.icon} [bold]{info.name}[/]: {msg}")

    def update(self, progress: float, message: str, details: Optional[str] = None):
        """更新进度"""
        self.current_progress = min(1.0, max(0.0, progress))

        self._emit_event(self.current_phase, self.current_progress, message, details)

        if self.callback:
            self.callback.on_progress(self.current_phase, self.current_progress, message)

        if self.console and not self.quiet:
            pct = int(self.current_progress * 100)
            self.console.print(f"  └─ [{pct}%] {message}")

    def complete_phase(self, message: Optional[str] = None):
        """完成当前阶段"""
        self.current_progress = 1.0

        info = PHASE_INFO[self.current_phase]
        msg = message or f"{info.name}完成"

        self._emit_event(self.current_phase, 1.0, msg)

        if self.callback:
            self.callback.on_phase_complete(self.current_phase)

        if self.console and not self.quiet:
            self.console.print(f"  ✓ {msg}", style="green")

    def fail(self, error: str):
        """标记失败"""
        self.error = error
        self.current_phase = Phase.FAILED

        self._emit_event(Phase.FAILED, self.current_progress, error)

        if self.callback:
            self.callback.on_error(self.current_phase, error)

        if self.console:
            self.console.print(f"❌ [red]失败[/]: {error}")

    def complete(self, message: Optional[str] = None):
        """标记任务完成"""
        self.current_phase = Phase.COMPLETED
        self.current_progress = 1.0

        elapsed = datetime.now() - self.start_time
        msg = message or f"任务完成 (耗时 {elapsed.total_seconds():.1f}s)"

        self._emit_event(Phase.COMPLETED, 1.0, msg)

        if self.console:
            self.console.print(f"\n✅ [bold green]{msg}[/]")
            if self.output_dir:
                self.console.print(f"📁 输出目录: {self.output_dir}")

    def get_summary(self) -> str:
        """获取执行摘要"""
        lines = [
            f"任务: {self.task_description}",
            f"ID: {self.task_id}",
            f"状态: {PHASE_INFO[self.current_phase].name}",
            f"进度: {int(self.current_progress * 100)}%",
        ]

        if self.error:
            lines.append(f"错误: {self.error}")

        if self.output_dir:
            lines.append(f"输出: {self.output_dir}")

        return "\n".join(lines)

    @contextmanager
    def live_panel(self):
        """Rich Live 面板上下文"""
        if not RICH_AVAILABLE or self.quiet:
            yield
            return

        def make_panel():
            table = Table(show_header=False, box=None)
            table.add_column("Key", style="dim")
            table.add_column("Value")

            table.add_row("任务", self.task_description[:50])
            table.add_row("阶段", PHASE_INFO[self.current_phase].name)
            table.add_row("进度", f"{int(self.current_progress * 100)}%")

            if self.events:
                last_msg = self.events[-1].message[:60]
                table.add_row("状态", last_msg)

            return Panel(table, title=f"[bold]SkillPack 执行中[/]", border_style="blue")

        with Live(make_panel(), refresh_per_second=4, console=self.console) as live:
            self._live = live
            self._make_panel = make_panel
            yield
            self._live = None


class SimpleProgressTracker(ProgressTracker):
    """简单进度追踪器 - 用于无 Rich 环境"""

    def __init__(self, task_id: str, task_description: str, **kwargs):
        # 移除 kwargs 中的 quiet，强制使用 True
        kwargs.pop('quiet', None)
        super().__init__(task_id, task_description, quiet=True, **kwargs)

    def start_phase(self, phase: Phase, message: Optional[str] = None):
        super().start_phase(phase, message)
        info = PHASE_INFO[phase]
        msg = message or info.description
        print(f"[{info.name}] {msg}")

    def update(self, progress: float, message: str, details: Optional[str] = None):
        super().update(progress, message, details)
        pct = int(self.current_progress * 100)
        print(f"  [{pct}%] {message}")

    def complete(self, message: Optional[str] = None):
        super().complete(message)
        elapsed = datetime.now() - self.start_time
        msg = message or f"完成 ({elapsed.total_seconds():.1f}s)"
        print(f"[完成] {msg}")
