"""
任务路由器 - 智能分析任务并选择最优执行路径

KISS: 简单的规则匹配，无复杂 ML
DRY: 复用复杂度检测逻辑
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

from .models import (
    TaskComplexity,
    ExecutionRoute,
    TaskContext,
    SkillpackConfig,
)


@dataclass
class ComplexitySignal:
    """复杂度信号"""
    name: str
    weight: float
    matched: bool


class TaskRouter:
    """
    任务路由器

    根据任务描述自动判断复杂度并选择执行路径：
    - 简单任务 → 直接执行
    - 中等任务 → plan → implement → review
    - 复杂任务 → Ralph 自动化
    - UI 任务 → UI flow
    """

    # UI 相关关键词
    UI_KEYWORDS = [
        r'\bui\b', r'\bux\b', r'界面', r'组件', r'component',
        r'页面', r'page', r'布局', r'layout', r'样式', r'style',
        r'css', r'tailwind', r'前端', r'frontend', r'按钮', r'button',
        r'表单', r'form', r'modal', r'弹窗', r'导航', r'nav',
    ]

    # 复杂度信号
    COMPLEXITY_SIGNALS = {
        'simple': [
            (r'fix\s*typo', 0.9),
            (r'修复\s*拼写', 0.9),
            (r'update\s*(readme|doc)', 0.8),
            (r'更新\s*(文档|readme)', 0.8),
            (r'add\s*comment', 0.7),
            (r'添加\s*注释', 0.7),
            (r'rename', 0.6),
            (r'重命名', 0.6),
        ],
        'complex': [
            (r'system', 0.6),
            (r'系统', 0.6),
            (r'架构', 0.8),
            (r'architecture', 0.8),
            (r'完整', 0.7),
            (r'complete', 0.7),
            (r'全面', 0.7),
            (r'comprehensive', 0.7),
            (r'多模块', 0.9),
            (r'multi.?module', 0.9),
            (r'重构', 0.7),
            (r'refactor', 0.7),
            (r'从零', 0.8),
            (r'from\s*scratch', 0.8),
        ],
    }

    def __init__(self, config: Optional[SkillpackConfig] = None):
        self.config = config or SkillpackConfig()

    def analyze_task(self, description: str) -> Tuple[TaskComplexity, List[ComplexitySignal]]:
        """
        分析任务描述，返回复杂度和匹配的信号

        Returns:
            Tuple[TaskComplexity, List[ComplexitySignal]]
        """
        description_lower = description.lower()
        signals: List[ComplexitySignal] = []

        # 检查 UI 关键词
        for pattern in self.UI_KEYWORDS:
            if re.search(pattern, description_lower, re.IGNORECASE):
                return TaskComplexity.UI, [
                    ComplexitySignal("ui_keyword", 1.0, True)
                ]

        # 计算简单度分数
        simple_score = 0.0
        for pattern, weight in self.COMPLEXITY_SIGNALS['simple']:
            matched = bool(re.search(pattern, description_lower, re.IGNORECASE))
            signals.append(ComplexitySignal(f"simple:{pattern}", weight, matched))
            if matched:
                simple_score += weight

        # 计算复杂度分数
        complex_score = 0.0
        for pattern, weight in self.COMPLEXITY_SIGNALS['complex']:
            matched = bool(re.search(pattern, description_lower, re.IGNORECASE))
            signals.append(ComplexitySignal(f"complex:{pattern}", weight, matched))
            if matched:
                complex_score += weight

        # 基于描述长度的启发式
        word_count = len(description.split())
        if word_count > 30:
            complex_score += 0.3
            signals.append(ComplexitySignal("long_description", 0.3, True))
        elif word_count < 10:
            simple_score += 0.2
            signals.append(ComplexitySignal("short_description", 0.2, True))

        # 决策
        if simple_score >= 0.6:
            return TaskComplexity.SIMPLE, signals
        elif complex_score >= 0.8:
            return TaskComplexity.COMPLEX, signals
        else:
            return TaskComplexity.MEDIUM, signals

    def determine_route(
        self,
        complexity: TaskComplexity,
        quick_mode: bool = False,
        deep_mode: bool = False
    ) -> ExecutionRoute:
        """
        根据复杂度和模式确定执行路由

        Args:
            complexity: 任务复杂度
            quick_mode: --quick 模式，跳过规划
            deep_mode: --deep 模式，强制 Ralph

        Returns:
            ExecutionRoute
        """
        # 强制模式覆盖
        if deep_mode:
            return ExecutionRoute.RALPH
        if quick_mode:
            return ExecutionRoute.DIRECT

        # 配置默认路由
        if self.config.default_route:
            return self.config.default_route

        # 基于复杂度路由
        route_map = {
            TaskComplexity.SIMPLE: ExecutionRoute.DIRECT,
            TaskComplexity.MEDIUM: ExecutionRoute.PLANNED,
            TaskComplexity.COMPLEX: ExecutionRoute.RALPH,
            TaskComplexity.UI: ExecutionRoute.UI_FLOW,
        }

        return route_map.get(complexity, ExecutionRoute.PLANNED)

    def route(
        self,
        description: str,
        quick_mode: bool = False,
        deep_mode: bool = False,
        notebook_id: Optional[str] = None,
        working_dir: Optional[Path] = None
    ) -> TaskContext:
        """
        主路由方法 - 分析任务并创建执行上下文

        Args:
            description: 任务描述
            quick_mode: 快速模式
            deep_mode: 深度模式
            notebook_id: 指定知识库 ID
            working_dir: 工作目录

        Returns:
            TaskContext 包含完整执行上下文
        """
        # 分析复杂度
        complexity, signals = self.analyze_task(description)

        # 确定路由
        route = self.determine_route(complexity, quick_mode, deep_mode)

        # 解析知识库配置
        effective_notebook = notebook_id or self.config.knowledge.default_notebook

        return TaskContext(
            description=description,
            complexity=complexity,
            route=route,
            notebook_id=effective_notebook,
            quick_mode=quick_mode,
            deep_mode=deep_mode,
            working_dir=working_dir or Path.cwd()
        )

    def explain_routing(self, context: TaskContext) -> str:
        """
        生成路由决策解释

        Returns:
            人类可读的路由解释
        """
        complexity_names = {
            TaskComplexity.SIMPLE: "简单",
            TaskComplexity.MEDIUM: "中等",
            TaskComplexity.COMPLEX: "复杂",
            TaskComplexity.UI: "UI相关",
        }

        route_names = {
            ExecutionRoute.DIRECT: "直接执行",
            ExecutionRoute.PLANNED: "规划 → 实现 → 审查",
            ExecutionRoute.RALPH: "Ralph 自动化",
            ExecutionRoute.UI_FLOW: "UI → 实现 → 浏览器预览",
        }

        lines = [
            f"📊 任务复杂度: {complexity_names[context.complexity]}",
            f"🚀 执行路径: {route_names[context.route]}",
        ]

        if context.notebook_id:
            lines.append(f"📚 知识库: {context.notebook_id}")

        if context.quick_mode:
            lines.append("⚡ 快速模式已启用")
        if context.deep_mode:
            lines.append("🔬 深度模式已启用")

        return "\n".join(lines)
