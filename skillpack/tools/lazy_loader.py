"""
懒加载工具加载器 (v6.0)

实现工具的按需加载，减少启动时 Token 消耗。
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path
import json

from .registry import ToolRegistry, ToolInfo, ToolSource, ToolParameter


class LazyToolLoader:
    """
    懒加载工具加载器

    策略:
    1. 启动时只加载元数据（~5k tokens）
    2. 首次使用时加载完整 Schema
    3. 缓存已加载的 Schema
    """

    # 常用工具列表（预加载）
    COMMON_TOOLS = [
        "mcp__codex-cli__codex",
        "mcp__gemini-cli__ask-gemini",
        "mcp__notebooklm-mcp__notebook_query",
    ]

    def __init__(
        self,
        registry: ToolRegistry,
        cache_dir: Optional[Path] = None,
        preload_common: bool = True,
    ):
        """
        初始化加载器

        Args:
            registry: 工具注册表
            cache_dir: 缓存目录
            preload_common: 是否预加载常用工具
        """
        self._registry = registry
        self._cache_dir = cache_dir or Path.home() / ".skillpack" / "tool_cache"
        self._preload_common = preload_common

        # Schema 获取回调
        self._schema_fetcher: Optional[Callable[[str], Dict]] = None

        # 加载状态
        self._loaded_schemas: Dict[str, Dict] = {}

    def set_schema_fetcher(self, fetcher: Callable[[str], Dict]):
        """
        设置 Schema 获取器

        Args:
            fetcher: 获取 Schema 的回调函数 (tool_name) -> schema_dict
        """
        self._schema_fetcher = fetcher

    def load_metadata(self, tools_metadata: List[Dict[str, Any]]) -> int:
        """
        加载工具元数据（启动时调用）

        Args:
            tools_metadata: 工具元数据列表

        Returns:
            加载的工具数量
        """
        count = 0

        for meta in tools_metadata:
            tool = self._create_tool_from_metadata(meta)
            if tool:
                self._registry.register(tool)
                count += 1

        # 预加载常用工具的 Schema
        if self._preload_common:
            for name in self.COMMON_TOOLS:
                self._load_schema(name)

        return count

    def get_schema(self, tool_name: str) -> Optional[Dict]:
        """
        获取工具 Schema（懒加载）

        Args:
            tool_name: 工具名称

        Returns:
            Schema 字典或 None
        """
        # 检查缓存
        if tool_name in self._loaded_schemas:
            return self._loaded_schemas[tool_name]

        # 加载 Schema
        schema = self._load_schema(tool_name)
        return schema

    def _load_schema(self, tool_name: str) -> Optional[Dict]:
        """加载工具 Schema"""
        tool = self._registry.get(tool_name)
        if not tool:
            return None

        # 已加载
        if tool.schema_loaded and tool.schema:
            return tool.schema

        # 尝试从缓存读取
        cached = self._read_cache(tool_name)
        if cached:
            tool.schema = cached
            tool.schema_loaded = True
            self._loaded_schemas[tool_name] = cached
            return cached

        # 使用获取器
        if self._schema_fetcher:
            try:
                schema = self._schema_fetcher(tool_name)
                if schema:
                    tool.schema = schema
                    tool.schema_loaded = True
                    self._loaded_schemas[tool_name] = schema
                    self._write_cache(tool_name, schema)
                    return schema
            except Exception:
                pass

        return None

    def _create_tool_from_metadata(self, meta: Dict[str, Any]) -> Optional[ToolInfo]:
        """从元数据创建工具信息"""
        name = meta.get("name")
        if not name:
            return None

        # 解析参数
        parameters = []
        for param in meta.get("parameters", []):
            parameters.append(ToolParameter(
                name=param.get("name", ""),
                type=param.get("type", "string"),
                description=param.get("description", ""),
                required=param.get("required", False),
                default=param.get("default"),
                enum=param.get("enum"),
            ))

        # 推断来源
        source = ToolSource.MCP
        if name.startswith("mcp__"):
            source = ToolSource.MCP
        elif name.startswith("builtin__"):
            source = ToolSource.BUILTIN
        elif name.startswith("skill__"):
            source = ToolSource.SKILL

        # 推断服务器名
        server = ""
        if name.startswith("mcp__"):
            parts = name.split("__")
            if len(parts) >= 2:
                server = parts[1]

        # 推断关键词
        keywords = meta.get("keywords", [])
        if not keywords:
            # 从名称和描述提取关键词
            keywords = self._extract_keywords(name, meta.get("description", ""))

        return ToolInfo(
            name=name,
            description=meta.get("description", ""),
            source=source,
            server=server,
            parameters=parameters,
            keywords=keywords,
            examples=meta.get("examples", []),
            category=meta.get("category", self._infer_category(name)),
            priority=meta.get("priority", 100),
            enabled=meta.get("enabled", True),
        )

    def _extract_keywords(self, name: str, description: str) -> List[str]:
        """从名称和描述提取关键词"""
        keywords = []

        # 从名称提取
        parts = name.replace("mcp__", "").replace("__", " ").split("_")
        keywords.extend([p for p in parts if len(p) > 2])

        # 从描述提取常见动词
        action_words = ["create", "read", "write", "delete", "search", "query", "execute", "run"]
        desc_lower = description.lower()
        for word in action_words:
            if word in desc_lower:
                keywords.append(word)

        return list(set(keywords))[:10]

    def _infer_category(self, name: str) -> str:
        """推断工具分类"""
        name_lower = name.lower()

        if "codex" in name_lower:
            return "code"
        elif "gemini" in name_lower:
            return "ai"
        elif "notebook" in name_lower:
            return "knowledge"
        elif "file" in name_lower or "read" in name_lower or "write" in name_lower:
            return "filesystem"
        elif "git" in name_lower:
            return "vcs"
        elif "browser" in name_lower or "chrome" in name_lower:
            return "browser"
        elif "search" in name_lower or "web" in name_lower:
            return "web"

        return "general"

    def _read_cache(self, tool_name: str) -> Optional[Dict]:
        """读取缓存"""
        cache_file = self._cache_dir / f"{tool_name.replace('__', '_')}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text())
            except Exception:
                pass
        return None

    def _write_cache(self, tool_name: str, schema: Dict):
        """写入缓存"""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self._cache_dir / f"{tool_name.replace('__', '_')}.json"
            cache_file.write_text(json.dumps(schema, ensure_ascii=False, indent=2))
        except Exception:
            pass

    def clear_cache(self):
        """清空缓存"""
        self._loaded_schemas.clear()
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass

    def get_load_stats(self) -> Dict[str, Any]:
        """获取加载统计"""
        total = len(self._registry)
        loaded = sum(1 for t in self._registry.list_all() if t.schema_loaded)

        return {
            "total_tools": total,
            "schemas_loaded": loaded,
            "schemas_pending": total - loaded,
            "cache_size": len(list(self._cache_dir.glob("*.json"))) if self._cache_dir.exists() else 0,
        }
