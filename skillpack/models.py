"""
SkillPack 配置模型

SOLID: Single Responsibility - 每个模型只负责一种配置类型
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json


class TaskComplexity(Enum):
    """任务复杂度等级"""
    SIMPLE = "simple"      # 单文件修改
    MEDIUM = "medium"      # 2-5 文件
    COMPLEX = "complex"    # 多模块
    UI = "ui"              # UI 相关


class ExecutionRoute(Enum):
    """执行路由类型"""
    DIRECT = "direct"              # 直接执行
    PLANNED = "planned"            # plan → implement → review
    RALPH = "ralph"                # Ralph 自动化
    UI_FLOW = "ui_flow"            # UI → implement → browser


@dataclass
class KnowledgeConfig:
    """知识库配置"""
    default_notebook: Optional[str] = None
    auto_query: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeConfig":
        return cls(
            default_notebook=data.get("default_notebook"),
            auto_query=data.get("auto_query", True)
        )


@dataclass
class OutputConfig:
    """输出目录配置"""
    current_dir: str = ".skillpack/current"
    history_dir: str = ".skillpack/history"

    def get_current_path(self, base: Path) -> Path:
        return base / self.current_dir

    def get_history_path(self, base: Path, timestamp: str) -> Path:
        return base / self.history_dir / timestamp


@dataclass
class SkillpackConfig:
    """Skillpack 主配置"""
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    default_route: Optional[ExecutionRoute] = None

    @classmethod
    def load(cls, config_path: Path) -> "SkillpackConfig":
        """从 .skillpackrc 加载配置"""
        if not config_path.exists():
            return cls()

        try:
            with open(config_path) as f:
                data = json.load(f)

            return cls(
                knowledge=KnowledgeConfig.from_dict(data.get("knowledge", {})),
                output=OutputConfig(
                    current_dir=data.get("output", {}).get("current_dir", ".skillpack/current"),
                    history_dir=data.get("output", {}).get("history_dir", ".skillpack/history")
                ),
                default_route=ExecutionRoute(data["default_route"]) if data.get("default_route") else None
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"配置文件解析错误: {e}")
            return cls()

    @classmethod
    def find_and_load(cls, start_path: Path) -> "SkillpackConfig":
        """向上查找并加载配置文件"""
        current = start_path.resolve()

        while current != current.parent:
            config_path = current / ".skillpackrc"
            if config_path.exists():
                return cls.load(config_path)
            current = current.parent

        return cls()


@dataclass
class TaskContext:
    """任务上下文"""
    description: str
    complexity: TaskComplexity
    route: ExecutionRoute
    notebook_id: Optional[str] = None
    quick_mode: bool = False
    deep_mode: bool = False
    working_dir: Path = field(default_factory=Path.cwd)

    def __post_init__(self):
        if isinstance(self.working_dir, str):
            self.working_dir = Path(self.working_dir)


@dataclass
class ExecutionStatus:
    """执行状态"""
    task_id: str
    phase: str
    progress: float  # 0.0 - 1.0
    message: str
    is_running: bool = True
    error: Optional[str] = None
    output_dir: Optional[Path] = None
