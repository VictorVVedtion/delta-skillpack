"""
Skillpack 集成层 (v6.0)

提供 LSP 代码智能和其他外部集成。
"""

from .lsp import LSPClient, LSPConfig

__all__ = [
    "LSPClient",
    "LSPConfig",
]
