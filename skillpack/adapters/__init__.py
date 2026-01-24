"""
Skillpack 适配器层 (v6.0)

提供 CLI 版本检测和功能适配，支持优雅降级。
"""

from .version_detector import VersionDetector, CLIVersion
from .base import BaseAdapter
from .codex_adapter import CodexAdapter
from .gemini_adapter import GeminiAdapter

__all__ = [
    "VersionDetector",
    "CLIVersion",
    "BaseAdapter",
    "CodexAdapter",
    "GeminiAdapter",
]
