"""
工具搜索器 (v6.0)

提供智能工具搜索和推荐功能。
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import re

from .registry import ToolRegistry, ToolInfo, ToolSource


@dataclass
class SearchResult:
    """搜索结果"""
    tool: ToolInfo                    # 工具信息
    score: float                      # 匹配分数 (0-1)
    match_reason: str                 # 匹配原因


class ToolSearcher:
    """
    工具搜索器

    支持功能:
    - 关键词搜索
    - 语义搜索（简化版）
    - 上下文推荐
    - 使用频率排序
    """

    # 任务-工具映射（语义推断）
    TASK_TOOL_MAPPING = {
        "代码": ["mcp__codex-cli__codex"],
        "code": ["mcp__codex-cli__codex"],
        "ui": ["mcp__gemini-cli__ask-gemini"],
        "界面": ["mcp__gemini-cli__ask-gemini"],
        "知识": ["mcp__notebooklm-mcp__notebook_query"],
        "文档": ["mcp__notebooklm-mcp__notebook_query"],
        "搜索": ["mcp__notebooklm-mcp__research_start"],
        "research": ["mcp__notebooklm-mcp__research_start"],
        "浏览器": ["mcp__claude-in-chrome__navigate", "mcp__claude-in-chrome__computer"],
        "browser": ["mcp__claude-in-chrome__navigate", "mcp__claude-in-chrome__computer"],
    }

    def __init__(self, registry: ToolRegistry):
        """
        初始化搜索器

        Args:
            registry: 工具注册表
        """
        self._registry = registry
        self._usage_counts: Dict[str, int] = {}

    def search(
        self,
        query: str,
        limit: int = 5,
        context: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        搜索工具

        Args:
            query: 搜索查询
            limit: 最大返回数量
            context: 任务上下文

        Returns:
            搜索结果列表
        """
        results: List[SearchResult] = []

        # 1. 语义推断
        semantic_tools = self._semantic_search(query)
        for name in semantic_tools:
            tool = self._registry.get(name)
            if tool:
                results.append(SearchResult(
                    tool=tool,
                    score=0.9,
                    match_reason="语义匹配",
                ))

        # 2. 关键词搜索
        keyword_results = self._registry.search(query, limit=limit * 2)
        for tool in keyword_results:
            if not any(r.tool.name == tool.name for r in results):
                score = self._calculate_score(query, tool)
                results.append(SearchResult(
                    tool=tool,
                    score=score,
                    match_reason="关键词匹配",
                ))

        # 3. 上下文推荐
        if context:
            context_tools = self._context_search(context)
            for tool in context_tools:
                if not any(r.tool.name == tool.name for r in results):
                    results.append(SearchResult(
                        tool=tool,
                        score=0.5,
                        match_reason="上下文推荐",
                    ))

        # 排序
        results.sort(key=lambda r: (-r.score, -self._usage_counts.get(r.tool.name, 0)))

        return results[:limit]

    def recommend_for_task(
        self,
        task_description: str,
        route: str,
    ) -> List[ToolInfo]:
        """
        为任务推荐工具

        Args:
            task_description: 任务描述
            route: 执行路由

        Returns:
            推荐的工具列表
        """
        recommendations: List[ToolInfo] = []

        # 根据路由推荐
        route_tools = self._get_route_tools(route)
        for name in route_tools:
            tool = self._registry.get(name)
            if tool:
                recommendations.append(tool)

        # 根据任务描述补充
        search_results = self.search(task_description, limit=3)
        for result in search_results:
            if result.tool not in recommendations:
                recommendations.append(result.tool)

        return recommendations[:5]

    def mark_used(self, tool_name: str):
        """记录工具使用"""
        self._usage_counts[tool_name] = self._usage_counts.get(tool_name, 0) + 1
        self._registry.mark_used(tool_name)

    def _semantic_search(self, query: str) -> List[str]:
        """语义搜索"""
        query_lower = query.lower()
        results = []

        for keyword, tools in self.TASK_TOOL_MAPPING.items():
            if keyword in query_lower:
                results.extend(tools)

        return list(set(results))

    def _context_search(self, context: str) -> List[ToolInfo]:
        """上下文搜索"""
        context_lower = context.lower()
        results = []

        # 检测文件扩展名
        if any(ext in context_lower for ext in [".ts", ".tsx", ".js", ".jsx", ".py"]):
            tool = self._registry.get("mcp__codex-cli__codex")
            if tool:
                results.append(tool)

        # 检测 UI 相关
        if any(word in context_lower for word in ["component", "page", "style", "css"]):
            tool = self._registry.get("mcp__gemini-cli__ask-gemini")
            if tool:
                results.append(tool)

        return results

    def _calculate_score(self, query: str, tool: ToolInfo) -> float:
        """计算匹配分数"""
        score = 0.0
        query_lower = query.lower()

        # 名称匹配
        if query_lower in tool.name.lower():
            score += 0.4
        if query_lower in tool.short_name.lower():
            score += 0.3

        # 描述匹配
        if query_lower in tool.description.lower():
            score += 0.2

        # 关键词匹配
        for keyword in tool.keywords:
            if query_lower in keyword.lower():
                score += 0.1
                break

        # 使用频率加成
        usage = self._usage_counts.get(tool.name, 0)
        score += min(usage * 0.01, 0.1)

        return min(score, 1.0)

    def _get_route_tools(self, route: str) -> List[str]:
        """获取路由对应的工具"""
        route_tools = {
            "DIRECT": ["mcp__codex-cli__codex"],
            "DIRECT_CODE": ["mcp__codex-cli__codex"],
            "DIRECT_TEXT": ["mcp__codex-cli__codex"],
            "PLANNED": ["mcp__codex-cli__codex"],
            "RALPH": ["mcp__codex-cli__codex", "mcp__gemini-cli__ask-gemini"],
            "ARCHITECT": ["mcp__gemini-cli__ask-gemini", "mcp__codex-cli__codex"],
            "UI_FLOW": ["mcp__gemini-cli__ask-gemini"],
        }

        return route_tools.get(route, [])

    def get_popular_tools(self, limit: int = 10) -> List[Tuple[str, int]]:
        """获取热门工具"""
        sorted_tools = sorted(
            self._usage_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_tools[:limit]
