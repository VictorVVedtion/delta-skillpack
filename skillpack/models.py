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
class ConsensusConfig:
    """
    多模型规划共识配置 (v5.5)

    在规划阶段引入 Codex/ChatGPT 打破 Claude 的"一言堂"，
    形成多模型共识后再执行。
    """
    enabled: bool = True                  # 是否启用多模型规划共识
    parallel_planning: bool = True        # 是否并行规划（Claude + Codex 同时）
    arbitration_threshold: float = 0.7    # 触发仲裁的共识度阈值
    planning_timeout_seconds: int = 120   # 单模型规划超时时间
    fallback_to_single_model: bool = True # 超时/失败时降级到单模型
    covered_routes: list = None           # 覆盖的路由（默认: PLANNED, RALPH, ARCHITECT）

    def __post_init__(self):
        if self.covered_routes is None:
            self.covered_routes = ["PLANNED", "RALPH", "ARCHITECT"]


# ==================== v6.0 新增配置类 ====================

@dataclass
class AdapterConfig:
    """
    CLI 适配器配置 (v6.0)

    控制版本检测和功能适配行为。
    """
    auto_detect: bool = True              # 是否自动检测 CLI 版本
    codex_min_version: str = "0.80.0"     # Codex 最低支持版本
    gemini_min_version: str = "0.15.0"    # Gemini 最低支持版本
    codex_recommended: str = "0.89.0"     # Codex 推荐版本
    gemini_recommended: str = "0.25.0"    # Gemini 推荐版本
    version_cache_ttl_seconds: int = 300  # 版本缓存有效期
    show_upgrade_hints: bool = True       # 显示升级提示


@dataclass
class SmartRoutingConfig:
    """
    智能模型路由配置 (v6.0)

    根据任务特征自动选择最优模型。
    """
    enabled: bool = True                      # 是否启用智能路由
    codex_max_threshold_tokens: int = 100_000 # 超过此 token 数使用 Codex-Max
    gemini_flash_threshold: int = 5           # UI 复杂度低于此值使用 Gemini Flash
    prefer_codex_for_code: bool = True        # 代码任务优先 Codex
    prefer_gemini_for_ui: bool = True         # UI 任务优先 Gemini
    auto_model_upgrade: bool = True           # 自动升级到更强模型


@dataclass
class ToolDiscoveryConfig:
    """
    工具发现配置 (v6.0)

    控制懒加载和工具缓存行为。
    """
    lazy_load: bool = True                # 是否启用懒加载
    cache_ttl_seconds: int = 300          # 工具元数据缓存有效期
    max_tools_per_request: int = 20       # 每次请求最大加载工具数
    preload_common_tools: bool = True     # 预加载常用工具


@dataclass
class BranchConfig:
    """
    分支管理配置 (v6.0)

    支持 Codex fork 功能和探索性分支。
    """
    enabled: bool = True                  # 是否启用分支管理
    max_branches: int = 5                 # 最大并行分支数
    auto_merge_threshold: float = 0.9     # 自动合并置信度阈值
    preserve_history: bool = True         # 保留分支历史


@dataclass
class SkillSystemConfig:
    """
    Skill 系统配置 (v6.0)

    统一的 Skill 注册和热重载配置。
    """
    enabled: bool = True                  # 是否启用 Skill 系统
    hot_reload: bool = True               # 是否启用热重载
    user_skills_dir: str = "~/.skillpack/skills"  # 用户 Skill 目录
    project_skills_dir: str = ".skillpack/skills" # 项目 Skill 目录
    debounce_ms: int = 500                # 热重载防抖时间


@dataclass
class LSPConfig:
    """
    LSP 集成配置 (v6.0)

    代码智能功能配置。
    """
    enabled: bool = False                 # 是否启用 LSP（默认关闭）
    auto_start: bool = False              # 是否自动启动 LSP 服务
    supported_languages: list = None      # 支持的语言列表
    timeout_seconds: int = 30             # LSP 请求超时

    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = ["typescript", "python", "go", "rust"]


@dataclass
class OutputConfig:
    """输出目录配置"""
    current_dir: str = ".skillpack/current"
    history_dir: str = ".skillpack/history"


@dataclass
class SkillpackConfig:
    """Skillpack 配置"""
    version: str = "6.0"
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)
    parallel: ParallelConfig = field(default_factory=ParallelConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)
    cross_validation: CrossValidationConfig = field(default_factory=CrossValidationConfig)
    consensus: ConsensusConfig = field(default_factory=ConsensusConfig)  # v5.5 新增
    output: OutputConfig = field(default_factory=OutputConfig)
    # v6.0 新增配置
    adapter: AdapterConfig = field(default_factory=AdapterConfig)
    smart_routing: SmartRoutingConfig = field(default_factory=SmartRoutingConfig)
    tool_discovery: ToolDiscoveryConfig = field(default_factory=ToolDiscoveryConfig)
    branch: BranchConfig = field(default_factory=BranchConfig)
    skill_system: SkillSystemConfig = field(default_factory=SkillSystemConfig)
    lsp: LSPConfig = field(default_factory=LSPConfig)


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
