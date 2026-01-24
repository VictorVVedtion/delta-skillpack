"""
工具注册表 (v6.0)

管理 MCP 工具的元数据和 Schema。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ToolSource(Enum):
    """工具来源"""
    MCP = "mcp"                 # MCP 服务器工具
    BUILTIN = "builtin"        # 内置工具
    SKILL = "skill"            # Skill 提供的工具
    CUSTOM = "custom"          # 自定义工具


@dataclass
class ToolParameter:
    """工具参数"""
    name: str                         # 参数名
    type: str                         # 参数类型
    description: str = ""             # 参数描述
    required: bool = False            # 是否必需
    default: Any = None               # 默认值
    enum: List[str] = None            # 枚举值


@dataclass
class ToolInfo:
    """工具信息"""
    name: str                         # 工具名称 (e.g., "mcp__codex-cli__codex")
    description: str                  # 工具描述
    source: ToolSource                # 工具来源
    server: str = ""                  # MCP 服务器名称
    parameters: List[ToolParameter] = field(default_factory=list)  # 参数列表
    schema: Optional[Dict] = None     # 完整 JSON Schema (懒加载)
    keywords: List[str] = field(default_factory=list)  # 搜索关键词
    examples: List[str] = field(default_factory=list)  # 使用示例
    category: str = ""                # 分类
    priority: int = 100               # 优先级
    enabled: bool = True              # 是否启用

    # 加载状态
    schema_loaded: bool = False       # Schema 是否已加载
    last_used: Optional[str] = None   # 最后使用时间

    @property
    def short_name(self) -> str:
        """短名称（去掉前缀）"""
        if self.name.startswith("mcp__"):
            parts = self.name.split("__")
            return parts[-1] if len(parts) > 2 else self.name
        return self.name


class ToolRegistry:
    """
    工具注册表

    支持功能:
    - 工具元数据注册
    - 按名称/关键词搜索
    - 懒加载 Schema
    - 使用统计
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        初始化注册表

        Args:
            cache_ttl_seconds: 缓存有效期
        """
        self._tools: Dict[str, ToolInfo] = {}
        self._keywords: Dict[str, List[str]] = {}  # keyword -> [tool_names]
        self._categories: Dict[str, List[str]] = {}  # category -> [tool_names]
        self._cache_ttl = cache_ttl_seconds
        self._loaded_at: Optional[str] = None

    def register(self, tool: ToolInfo, force: bool = False) -> bool:
        """
        注册工具

        Args:
            tool: 工具信息
            force: 是否强制覆盖

        Returns:
            是否注册成功
        """
        if tool.name in self._tools and not force:
            return False

        self._tools[tool.name] = tool

        # 索引关键词
        for keyword in tool.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower not in self._keywords:
                self._keywords[keyword_lower] = []
            if tool.name not in self._keywords[keyword_lower]:
                self._keywords[keyword_lower].append(tool.name)

        # 索引分类
        if tool.category:
            if tool.category not in self._categories:
                self._categories[tool.category] = []
            if tool.name not in self._categories[tool.category]:
                self._categories[tool.category].append(tool.name)

        return True

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name not in self._tools:
            return False

        tool = self._tools[name]

        # 移除关键词索引
        for keyword in tool.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self._keywords:
                if name in self._keywords[keyword_lower]:
                    self._keywords[keyword_lower].remove(name)

        # 移除分类索引
        if tool.category and tool.category in self._categories:
            if name in self._categories[tool.category]:
                self._categories[tool.category].remove(name)

        del self._tools[name]
        return True

    def get(self, name: str) -> Optional[ToolInfo]:
        """按名称获取工具"""
        return self._tools.get(name)

    def search(
        self,
        query: str,
        limit: int = 10,
        source: Optional[ToolSource] = None,
        category: Optional[str] = None,
    ) -> List[ToolInfo]:
        """
        搜索工具

        Args:
            query: 搜索查询
            limit: 最大返回数量
            source: 过滤来源
            category: 过滤分类

        Returns:
            匹配的工具列表
        """
        query_lower = query.lower()
        results: List[ToolInfo] = []
        seen_names: set = set()

        # 1. 精确名称匹配
        for name, tool in self._tools.items():
            if query_lower in name.lower() or query_lower in tool.short_name.lower():
                if self._match_filters(tool, source, category):
                    if name not in seen_names:
                        results.append(tool)
                        seen_names.add(name)

        # 2. 关键词匹配
        if query_lower in self._keywords:
            for name in self._keywords[query_lower]:
                if name in self._tools and name not in seen_names:
                    tool = self._tools[name]
                    if self._match_filters(tool, source, category):
                        results.append(tool)
                        seen_names.add(name)

        # 3. 描述匹配
        for name, tool in self._tools.items():
            if name not in seen_names:
                if query_lower in tool.description.lower():
                    if self._match_filters(tool, source, category):
                        results.append(tool)
                        seen_names.add(name)

        # 排序
        results.sort(key=lambda t: t.priority)

        return results[:limit]

    def list_by_category(self, category: str) -> List[ToolInfo]:
        """按分类列出工具"""
        names = self._categories.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def list_categories(self) -> List[str]:
        """列出所有分类"""
        return list(self._categories.keys())

    def list_all(
        self,
        enabled_only: bool = True,
        limit: Optional[int] = None,
    ) -> List[ToolInfo]:
        """列出所有工具"""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        tools.sort(key=lambda t: t.priority)
        if limit:
            tools = tools[:limit]
        return tools

    def mark_used(self, name: str):
        """标记工具已使用"""
        if name in self._tools:
            self._tools[name].last_used = datetime.now().isoformat()

    def _match_filters(
        self,
        tool: ToolInfo,
        source: Optional[ToolSource],
        category: Optional[str],
    ) -> bool:
        """检查是否匹配过滤条件"""
        if not tool.enabled:
            return False
        if source and tool.source != source:
            return False
        if category and tool.category != category:
            return False
        return True

    def get_metadata_summary(self) -> Dict[str, Any]:
        """获取元数据摘要（用于启动时加载）"""
        return {
            "total_tools": len(self._tools),
            "categories": list(self._categories.keys()),
            "tools": [
                {
                    "name": t.name,
                    "description": t.description[:100],
                    "keywords": t.keywords[:5],
                    "category": t.category,
                }
                for t in self.list_all(limit=50)
            ],
        }

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
