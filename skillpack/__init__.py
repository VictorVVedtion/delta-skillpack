"""
SkillPack - 智能任务执行器

统一入口，自动路由，实时反馈

Usage:
    skill do "任务描述"
    skill do "任务" --quick      # 跳过规划
    skill do "任务" --deep       # 强制 Ralph
    skill do "任务" --kb <id>    # 指定知识库
    skill status                 # 查看状态
    skill cancel                 # 取消执行
"""

from .models import (
    TaskComplexity,
    ExecutionRoute,
    TaskContext,
    ExecutionStatus,
    SkillpackConfig,
    KnowledgeConfig,
    OutputConfig,
)
from .router import TaskRouter
from .executor import TaskExecutor
from .ralph.dashboard import (
    ProgressTracker,
    SimpleProgressTracker,
    Phase,
    ProgressCallback,
)

__version__ = "1.0.0"
__all__ = [
    # Models
    "TaskComplexity",
    "ExecutionRoute",
    "TaskContext",
    "ExecutionStatus",
    "SkillpackConfig",
    "KnowledgeConfig",
    "OutputConfig",
    # Router
    "TaskRouter",
    # Executor
    "TaskExecutor",
    # Progress
    "ProgressTracker",
    "SimpleProgressTracker",
    "Phase",
    "ProgressCallback",
]
