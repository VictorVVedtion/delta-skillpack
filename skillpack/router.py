"""
任务路由器

基于 6 维度评分系统进行任务复杂度评估和路由决策。
"""

import re
from typing import Optional
from .models import (
    TaskComplexity,
    ExecutionRoute,
    TaskContext,
    ScoreCard,
    SkillpackConfig,
)


class TaskRouter:
    """任务路由器"""
    
    # 复杂度降低信号
    SIMPLE_SIGNALS = {
        "typo": -10, "拼写": -10, "comment": -10, "注释": -10,
        "rename": -8, "重命名": -8,
        "readme": -5, "文档": -5, "docs": -5,
        "简单": -5, "快速": -5, "小改": -5,
    }
    
    # 复杂度提升信号
    COMPLEX_SIGNALS = {
        "系统": 20, "架构": 20, "architecture": 20,
        "完整": 15, "complete": 15, "全面": 15,
        "重构": 15, "refactor": 15,
        "从零": 25, "from scratch": 25,
        "多模块": 15, "multi-module": 15,
    }
    
    # UI 信号
    UI_SIGNALS = [
        "ui", "ux", "界面", "组件", "component", "页面", "page",
        "布局", "layout", "样式", "css", "前端", "frontend",
        "jsx", "tsx", "hook", "useState", "vue", "next", "nuxt",
        "shadcn", "radix", "chakra", "material-ui", "antd",
        "framer", "framer-motion", "gsap", "animation",
        "button", "form", "modal", "card", "table", "tabs", "dialog",
    ]
    
    # 文本任务信号
    TEXT_SIGNALS = [".md", ".txt", ".json", ".yaml", ".toml", "config", "配置"]
    
    def __init__(self, config: Optional[SkillpackConfig] = None):
        self.config = config or SkillpackConfig()
    
    def route(
        self,
        description: str,
        quick_mode: bool = False,
        deep_mode: bool = False,
        notebook_id: Optional[str] = None,
        parallel_mode: Optional[bool] = None,
        cli_mode: bool = False,
    ) -> TaskContext:
        """分析任务并返回路由上下文"""
        
        # 确定 notebook_id
        final_notebook_id = notebook_id
        if not final_notebook_id and self.config.knowledge.default_notebook:
            final_notebook_id = self.config.knowledge.default_notebook
        
        # 强制模式覆盖
        if quick_mode:
            return TaskContext(
                description=description,
                complexity=TaskComplexity.SIMPLE,
                route=ExecutionRoute.DIRECT,
                notebook_id=final_notebook_id,
                quick_mode=True,
            )
        
        if deep_mode:
            return TaskContext(
                description=description,
                complexity=TaskComplexity.COMPLEX,
                route=ExecutionRoute.RALPH,
                notebook_id=final_notebook_id,
                deep_mode=True,
            )
        
        # 计算评分
        score_card = self._calculate_score(description)
        total = score_card.total
        
        # 检查 UI 信号 (降低阈值到 2，更容易触发 UI 路由)
        if self._has_ui_signal(description) and score_card.ui >= 2:
            return TaskContext(
                description=description,
                complexity=TaskComplexity.UI,
                route=ExecutionRoute.UI_FLOW,
                notebook_id=final_notebook_id,
                score_card=score_card,
                parallel_mode=parallel_mode,
                cli_mode=cli_mode,
            )
        
        # 根据总分确定路由
        complexity, route = self._determine_route(total, description)
        
        return TaskContext(
            description=description,
            complexity=complexity,
            route=route,
            notebook_id=final_notebook_id,
            score_card=score_card,
            parallel_mode=parallel_mode,
            cli_mode=cli_mode,
        )
    
    def _calculate_score(self, description: str) -> ScoreCard:
        """计算 6 维度评分"""
        desc_lower = description.lower()
        word_count = len(description.split())
        
        # 基础分数 (默认中等复杂度区间 21-45)
        base_scope = min(5 + word_count * 2, 25)
        score_card = ScoreCard(
            scope=base_scope,
            dependency=5,
            technical=5,
            risk=3,
            time=min(3 + word_count // 3, 10),
            ui=0,
        )
        
        # 应用信号调整
        simple_adjustment = 0
        complex_adjustment = 0
        
        for signal, value in self.SIMPLE_SIGNALS.items():
            if signal in desc_lower:
                simple_adjustment += value  # 负值
        
        for signal, value in self.COMPLEX_SIGNALS.items():
            if signal in desc_lower:
                complex_adjustment += value  # 正值
        
        # UI 复杂度
        ui_count = sum(1 for s in self.UI_SIGNALS if s in desc_lower)
        score_card.ui = min(ui_count * 3, 10)  # 增加 UI 权重
        
        # 应用调整
        total_adjustment = simple_adjustment + complex_adjustment
        
        if total_adjustment < -5:
            # 简单任务: 大幅降低分数
            reduction = abs(total_adjustment)
            score_card.scope = max(2, score_card.scope - reduction // 2)
            score_card.dependency = max(0, score_card.dependency - reduction // 3)
            score_card.technical = max(1, score_card.technical - reduction // 3)
            score_card.risk = max(1, score_card.risk - reduction // 4)
            score_card.time = max(1, score_card.time - reduction // 5)
        elif total_adjustment > 10:
            # 复杂任务: 大幅提升分数
            increase = total_adjustment
            score_card.scope = min(25, score_card.scope + increase // 2)
            score_card.dependency = min(20, score_card.dependency + increase // 2)
            score_card.technical = min(20, score_card.technical + increase // 2)
            score_card.risk = min(15, score_card.risk + increase // 3)
        
        return score_card
    
    def _has_ui_signal(self, description: str) -> bool:
        """检查是否包含 UI 信号"""
        desc_lower = description.lower()
        return any(signal in desc_lower for signal in self.UI_SIGNALS)
    
    def _determine_route(self, total: int, description: str) -> tuple[TaskComplexity, ExecutionRoute]:
        """根据总分确定复杂度和路由"""
        thresholds = self.config.routing.thresholds
        
        if total <= thresholds["direct"]:
            # 区分 TEXT 和 CODE
            if self._is_text_task(description):
                return TaskComplexity.SIMPLE, ExecutionRoute.DIRECT
            return TaskComplexity.SIMPLE, ExecutionRoute.DIRECT
        elif total <= thresholds["planned"]:
            return TaskComplexity.MEDIUM, ExecutionRoute.PLANNED
        elif total <= thresholds["ralph"]:
            return TaskComplexity.COMPLEX, ExecutionRoute.RALPH
        else:
            return TaskComplexity.ARCHITECT, ExecutionRoute.ARCHITECT
    
    def _is_text_task(self, description: str) -> bool:
        """检查是否是文本任务"""
        desc_lower = description.lower()
        return any(signal in desc_lower for signal in self.TEXT_SIGNALS)
    
    def explain_routing(self, context: TaskContext) -> str:
        """生成路由解释"""
        lines = [
            f"📊 任务复杂度分析",
            f"",
            f"复杂度: {context.complexity.value}",
            f"路由: {context.route.value}",
        ]
        
        if context.score_card:
            sc = context.score_card
            lines.extend([
                f"",
                f"评分详情:",
                f"  范围广度:    {sc.scope}/25",
                f"  依赖复杂度:  {sc.dependency}/20",
                f"  技术深度:    {sc.technical}/20",
                f"  风险等级:    {sc.risk}/15",
                f"  时间估算:    {sc.time}/10",
                f"  UI 复杂度:   {sc.ui}/10",
                f"  总分:        {sc.total}/100",
            ])
        
        if context.notebook_id:
            lines.append(f"知识库: {context.notebook_id}")
        
        complexity_names = {
            TaskComplexity.SIMPLE: "简单",
            TaskComplexity.MEDIUM: "中等",
            TaskComplexity.COMPLEX: "复杂",
            TaskComplexity.ARCHITECT: "超复杂",
            TaskComplexity.UI: "UI",
        }
        
        route_names = {
            ExecutionRoute.DIRECT: "直接执行",
            ExecutionRoute.PLANNED: "计划执行",
            ExecutionRoute.RALPH: "RALPH 自动化",
            ExecutionRoute.ARCHITECT: "架构优先",
            ExecutionRoute.UI_FLOW: "UI 流程",
        }
        
        lines.insert(3, f"  → {complexity_names.get(context.complexity, '')} 任务，{route_names.get(context.route, '')}")
        
        return "\n".join(lines)
