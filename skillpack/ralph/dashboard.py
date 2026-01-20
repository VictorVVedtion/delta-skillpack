"""
RALPH 进度追踪仪表板

提供任务执行进度追踪和回调机制。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class Phase(Enum):
    """执行阶段"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    DESIGNING = "designing"
    IMPLEMENTING = "implementing"
    REVIEWING = "reviewing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """进度事件"""
    phase: Phase
    progress: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


class ProgressCallback(ABC):
    """进度回调接口"""
    
    @abstractmethod
    def on_phase_start(self, phase: Phase, message: str) -> None:
        pass
    
    @abstractmethod
    def on_progress(self, phase: Phase, progress: float, message: str) -> None:
        pass
    
    @abstractmethod
    def on_phase_complete(self, phase: Phase) -> None:
        pass
    
    @abstractmethod
    def on_error(self, phase: Phase, error: str) -> None:
        pass


class ProgressTracker(ABC):
    """进度追踪器接口"""
    
    @abstractmethod
    def start_phase(self, phase: Phase) -> None:
        pass
    
    @abstractmethod
    def update(self, progress: float, message: str) -> None:
        pass
    
    @abstractmethod
    def complete_phase(self) -> None:
        pass
    
    @abstractmethod
    def complete(self) -> None:
        pass
    
    @abstractmethod
    def fail(self, error: str) -> None:
        pass


class SimpleProgressTracker(ProgressTracker):
    """简单进度追踪器实现"""
    
    def __init__(
        self,
        task_id: str,
        description: str,
        callback: Optional[ProgressCallback] = None,
        quiet: bool = False,
    ):
        self.task_id = task_id
        self.description = description
        self.callback = callback
        self.quiet = quiet
        
        self.current_phase = Phase.PENDING
        self.current_progress = 0.0
        self.events: List[ProgressEvent] = []
        self.error: Optional[str] = None
    
    def start_phase(self, phase: Phase) -> None:
        """开始新阶段"""
        self.current_phase = phase
        self.current_progress = 0.0
        
        event = ProgressEvent(phase, 0.0, f"开始 {phase.value}")
        self.events.append(event)
        
        if self.callback:
            self.callback.on_phase_start(phase, f"开始 {phase.value}")
        
        if not self.quiet:
            print(f"[{phase.value}] 开始...")
    
    def update(self, progress: float, message: str) -> None:
        """更新进度"""
        self.current_progress = progress
        
        event = ProgressEvent(self.current_phase, progress, message)
        self.events.append(event)
        
        if self.callback:
            self.callback.on_progress(self.current_phase, progress, message)
        
        if not self.quiet:
            print(f"[{self.current_phase.value}] {progress*100:.0f}% - {message}")
    
    def complete_phase(self) -> None:
        """完成当前阶段"""
        self.current_progress = 1.0
        
        event = ProgressEvent(self.current_phase, 1.0, "完成")
        self.events.append(event)
        
        if self.callback:
            self.callback.on_phase_complete(self.current_phase)
        
        if not self.quiet:
            print(f"[{self.current_phase.value}] ✓ 完成")
    
    def complete(self) -> None:
        """完成整个任务"""
        self.current_phase = Phase.COMPLETED
        self.current_progress = 1.0
        
        if not self.quiet:
            print("✓ 任务完成")
    
    def fail(self, error: str) -> None:
        """任务失败"""
        self.error = error
        old_phase = self.current_phase
        self.current_phase = Phase.FAILED
        
        if self.callback:
            self.callback.on_error(old_phase, error)
        
        if not self.quiet:
            print(f"✗ 任务失败: {error}")
