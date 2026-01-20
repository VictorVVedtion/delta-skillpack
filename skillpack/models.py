"""
Skillpack 数据模型

定义任务复杂度、执行路由和配置模型。
"""

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any


class TaskComplexity(Enum):
    """任务复杂度等级"""
    SIMPLE = "simple"      # 0-20 分
    MEDIUM = "medium"      # 21-45 分
    COMPLEX = "complex"    # 46-70 分
    ARCHITECT = "architect"  # 71-100 分
    UI = "ui"              # UI 信号触发


class ExecutionRoute(Enum):
    """执行路由类型"""
    DIRECT = "DIRECT"          # 直接执行 (DIRECT_TEXT/DIRECT_CODE)
    PLANNED = "PLANNED"        # 计划执行
    RALPH = "RALPH"            # 复杂任务自动化
    ARCHITECT = "ARCHITECT"    # 架构优先
    UI_FLOW = "UI_FLOW"        # UI 流程


@dataclass
class KnowledgeConfig:
    """知识库配置"""
    default_notebook: Optional[str] = None
    auto_query: bool = True


@dataclass
class RoutingConfig:
    """路由配置"""
    weights: Dict[str, int] = field(default_factory=lambda: {
        "scope": 25,
        "dependency": 20,
        "technical": 20,
        "risk": 15,
        "time": 10,
        "ui": 10
    })
    thresholds: Dict[str, int] = field(default_factory=lambda: {
        "direct": 20,
        "planned": 45,
        "ralph": 70
    })


@dataclass
class CheckpointConfig:
    """检查点配置"""
    auto_save: bool = True
    atomic_writes: bool = True
    backup_count: int = 3
    save_interval_minutes: int = 5
    max_history: int = 10


@dataclass
class ParallelConfig:
    """并行执行配置"""
    enabled: bool = False
    max_concurrent_tasks: int = 3
    poll_interval_seconds: int = 5
    task_timeout_seconds: int = 300
    allow_cross_model_parallel: bool = True
    fallback_to_serial_on_failure: bool = True


@dataclass
class MCPConfig:
    """MCP 调用配置"""
    timeout_seconds: int = 180
    max_retries: int = 1
    auto_fallback_to_cli: bool = True


@dataclass
class CLIConfig:
    """CLI 直接调用配置"""
    prefer_cli_over_mcp: bool = True  # v5.3+ 默认 CLI 优先
    cli_timeout_seconds: int = 600
    codex_command: str = "codex"
    gemini_command: str = "gemini"
    auto_context: bool = True
    max_context_files: int = 15
    max_lines_per_file: int = 800


@dataclass
class CrossValidationConfig:
    """交叉验证配置 (v5.4)"""
    enabled: bool = True
    require_arbitration_on_disagreement: bool = True
    min_confidence_for_auto_pass: str = "high"  # low, medium, high


@dataclass
class OutputConfig:
    """输出目录配置"""
    current_dir: str = ".skillpack/current"
    history_dir: str = ".skillpack/history"


@dataclass
class SkillpackConfig:
    """Skillpack 配置"""
    version: str = "5.4"
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)
    parallel: ParallelConfig = field(default_factory=ParallelConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)
    cross_validation: CrossValidationConfig = field(default_factory=CrossValidationConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


@dataclass
class ScoreCard:
    """评分卡"""
    scope: int = 0          # 范围广度 (0-25)
    dependency: int = 0     # 依赖复杂度 (0-20)
    technical: int = 0      # 技术深度 (0-20)
    risk: int = 0           # 风险等级 (0-15)
    time: int = 0           # 时间估算 (0-10)
    ui: int = 0             # UI 复杂度 (0-10)
    
    @property
    def total(self) -> int:
        """计算总分"""
        return self.scope + self.dependency + self.technical + self.risk + self.time + self.ui


@dataclass
class TaskContext:
    """任务上下文"""
    description: str
    complexity: TaskComplexity
    route: ExecutionRoute
    working_dir: Optional[Path] = None
    notebook_id: Optional[str] = None
    score_card: Optional[ScoreCard] = None
    quick_mode: bool = False
    deep_mode: bool = False
    parallel_mode: Optional[bool] = None
    cli_mode: bool = False
