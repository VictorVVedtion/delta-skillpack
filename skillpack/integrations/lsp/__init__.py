"""
LSP 集成 (v6.0)

提供代码智能功能：go-to-definition, find-references, hover-docs 等。
"""

from .client import LSPClient
from .config import LSPConfig

__all__ = [
    "LSPClient",
    "LSPConfig",
]
