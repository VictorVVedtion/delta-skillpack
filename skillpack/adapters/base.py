"""
适配器基类 (v6.0)

定义 CLI 适配器的抽象接口，支持版本感知和功能探测。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class FeatureStatus(Enum):
    """功能状态"""
    AVAILABLE = "available"         # 功能可用
    UNAVAILABLE = "unavailable"     # 功能不可用
    DEGRADED = "degraded"           # 降级模式可用
    UNKNOWN = "unknown"             # 未知状态


@dataclass
class CLIVersion:
    """CLI 版本信息"""
    cli_name: str                               # CLI 名称 (codex, gemini)
    version: str                                # 版本号 (e.g., "0.89.0")
    features: Dict[str, FeatureStatus] = field(default_factory=dict)  # 功能状态
    raw_output: str = ""                        # 原始版本输出
    detected_at: str = ""                       # 检测时间

    @property
    def major(self) -> int:
        """主版本号"""
        parts = self.version.split(".")
        return int(parts[0]) if parts else 0

    @property
    def minor(self) -> int:
        """次版本号"""
        parts = self.version.split(".")
        return int(parts[1]) if len(parts) > 1 else 0

    @property
    def patch(self) -> int:
        """补丁版本号"""
        parts = self.version.split(".")
        return int(parts[2].split("-")[0]) if len(parts) > 2 else 0

    def __ge__(self, other: str) -> bool:
        """版本比较: >= """
        other_parts = other.split(".")
        other_major = int(other_parts[0]) if other_parts else 0
        other_minor = int(other_parts[1]) if len(other_parts) > 1 else 0
        other_patch = int(other_parts[2].split("-")[0]) if len(other_parts) > 2 else 0

        if self.major != other_major:
            return self.major > other_major
        if self.minor != other_minor:
            return self.minor > other_minor
        return self.patch >= other_patch

    def __lt__(self, other: str) -> bool:
        """版本比较: < """
        return not self >= other

    def has_feature(self, feature: str) -> bool:
        """检查功能是否可用"""
        status = self.features.get(feature, FeatureStatus.UNKNOWN)
        return status == FeatureStatus.AVAILABLE

    def feature_status(self, feature: str) -> FeatureStatus:
        """获取功能状态"""
        return self.features.get(feature, FeatureStatus.UNKNOWN)


@dataclass
class AdapterCommand:
    """适配器命令结构"""
    base_command: str                           # 基础命令
    args: List[str] = field(default_factory=list)  # 参数列表
    env: Dict[str, str] = field(default_factory=dict)  # 环境变量
    timeout_seconds: int = 600                  # 超时时间
    sandbox_mode: Optional[str] = None          # 沙箱模式


class BaseAdapter(ABC):
    """
    CLI 适配器基类

    根据检测到的 CLI 版本提供适配的命令和功能。
    """

    def __init__(self, version: CLIVersion):
        self.version = version
        self._feature_cache: Dict[str, FeatureStatus] = {}

    @property
    @abstractmethod
    def cli_name(self) -> str:
        """CLI 名称"""
        pass

    @property
    @abstractmethod
    def min_supported_version(self) -> str:
        """最低支持版本"""
        pass

    @property
    @abstractmethod
    def recommended_version(self) -> str:
        """推荐版本"""
        pass

    @abstractmethod
    def build_exec_command(
        self,
        prompt: str,
        sandbox: str = "workspace-write",
        context_files: Optional[List[str]] = None,
        **kwargs
    ) -> AdapterCommand:
        """
        构建执行命令

        Args:
            prompt: 任务提示
            sandbox: 沙箱模式
            context_files: 上下文文件列表
            **kwargs: 额外参数

        Returns:
            AdapterCommand 命令结构
        """
        pass

    @abstractmethod
    def get_available_features(self) -> Dict[str, FeatureStatus]:
        """获取当前版本可用的功能列表"""
        pass

    def is_supported(self) -> bool:
        """检查版本是否支持"""
        return self.version >= self.min_supported_version

    def needs_upgrade(self) -> bool:
        """检查是否需要升级"""
        return self.version < self.recommended_version

    def get_upgrade_message(self) -> Optional[str]:
        """获取升级提示消息"""
        if not self.is_supported():
            return (
                f"⚠️ {self.cli_name} 版本 {self.version.version} 低于最低支持版本 "
                f"{self.min_supported_version}。请升级以确保功能正常。"
            )
        if self.needs_upgrade():
            return (
                f"💡 {self.cli_name} 版本 {self.version.version} 可升级到 "
                f"{self.recommended_version} 以获取更多功能。"
            )
        return None

    def _check_feature(self, feature: str, min_version: str) -> FeatureStatus:
        """根据版本检查功能状态"""
        if self.version >= min_version:
            return FeatureStatus.AVAILABLE
        return FeatureStatus.UNAVAILABLE
