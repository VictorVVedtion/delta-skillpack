"""
LSP 配置 (v6.0)

定义 LSP 服务器配置和语言映射。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class LSPServerConfig:
    """LSP 服务器配置"""
    command: str                              # 启动命令
    args: List[str] = field(default_factory=list)  # 命令参数
    init_options: Dict = field(default_factory=dict)  # 初始化选项
    settings: Dict = field(default_factory=dict)  # 服务器设置
    root_patterns: List[str] = field(default_factory=list)  # 项目根标识文件


@dataclass
class LSPConfig:
    """LSP 总配置"""
    enabled: bool = False                     # 是否启用
    auto_start: bool = False                  # 自动启动
    timeout_seconds: int = 30                 # 请求超时
    workspace_root: Optional[Path] = None     # 工作区根目录

    # 语言-服务器映射
    servers: Dict[str, LSPServerConfig] = field(default_factory=dict)

    def __post_init__(self):
        # 默认服务器配置
        if not self.servers:
            self.servers = {
                "typescript": LSPServerConfig(
                    command="typescript-language-server",
                    args=["--stdio"],
                    root_patterns=["package.json", "tsconfig.json"],
                ),
                "python": LSPServerConfig(
                    command="pyright-langserver",
                    args=["--stdio"],
                    root_patterns=["pyproject.toml", "setup.py", "requirements.txt"],
                ),
                "go": LSPServerConfig(
                    command="gopls",
                    args=["serve"],
                    root_patterns=["go.mod", "go.sum"],
                ),
                "rust": LSPServerConfig(
                    command="rust-analyzer",
                    args=[],
                    root_patterns=["Cargo.toml"],
                ),
            }


# 文件扩展名到语言映射
EXTENSION_TO_LANGUAGE = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",  # 使用 TypeScript LSP
    ".jsx": "typescript",
    ".py": "python",
    ".pyi": "python",
    ".go": "go",
    ".rs": "rust",
}


def detect_language(file_path: Path) -> Optional[str]:
    """根据文件扩展名检测语言"""
    suffix = file_path.suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(suffix)
