"""
DAG 可视化器 (v6.0)

提供任务 DAG 的 ASCII 可视化。
"""

from typing import List, Dict, Optional
from .dag import TaskDAG, TaskNode, TaskState


class DAGVisualizer:
    """
    DAG 可视化器

    支持功能:
    - ASCII 波次图
    - 进度条
    - 依赖关系图
    """

    # 状态图标
    STATE_ICONS = {
        TaskState.PENDING: "○",
        TaskState.READY: "◎",
        TaskState.RUNNING: "●",
        TaskState.COMPLETED: "✓",
        TaskState.FAILED: "✗",
        TaskState.SKIPPED: "−",
        TaskState.BLOCKED: "⊘",
    }

    # 模型颜色标识
    MODEL_TAGS = {
        "codex": "[C]",
        "gemini": "[G]",
        "claude": "[Cl]",
    }

    def __init__(self, dag: TaskDAG):
        """
        初始化可视化器

        Args:
            dag: 任务 DAG
        """
        self._dag = dag

    def render_waves(self, show_dependencies: bool = False) -> str:
        """
        渲染波次视图

        Args:
            show_dependencies: 是否显示依赖关系

        Returns:
            ASCII 字符串
        """
        waves = self._dag.compute_waves()
        progress = self._dag.get_progress()

        lines = []

        # 标题
        lines.append("╔══════════════════════════════════════════════════════════╗")
        lines.append(f"║  任务执行进度: {progress['completed']}/{progress['total']} ({progress['progress_percent']:.0f}%)                          ║")
        lines.append("╠══════════════════════════════════════════════════════════╣")

        # 波次
        for i, wave in enumerate(waves):
            is_current = i == progress['current_wave']
            wave_marker = "►" if is_current else " "

            lines.append(f"║{wave_marker} Wave {i + 1}:                                                  ║")

            for task_id in wave:
                node = self._dag.get_task(task_id)
                if node:
                    task_line = self._render_task_line(node, show_dependencies)
                    lines.append(f"║   {task_line:<55}║")

            if i < len(waves) - 1:
                lines.append("║  ─────────────────────────────────────────────────────  ║")

        lines.append("╚══════════════════════════════════════════════════════════╝")

        return "\n".join(lines)

    def render_progress_bar(self, width: int = 40) -> str:
        """
        渲染进度条

        Args:
            width: 进度条宽度

        Returns:
            进度条字符串
        """
        progress = self._dag.get_progress()
        percent = progress['progress_percent']

        filled = int(width * percent / 100)
        empty = width - filled

        bar = f"[{'█' * filled}{'░' * empty}]"
        stats = f"{progress['completed']}/{progress['total']} ({percent:.0f}%)"

        return f"{bar} {stats}"

    def render_task_tree(self, root_id: Optional[str] = None) -> str:
        """
        渲染任务依赖树

        Args:
            root_id: 根任务 ID（可选）

        Returns:
            ASCII 树形图
        """
        lines = []

        if root_id:
            # 从指定任务开始
            self._render_tree_node(root_id, lines, "", True)
        else:
            # 渲染所有根节点（没有依赖的任务）
            roots = [
                node.id for node in self._dag
                if not node.dependencies
            ]

            for i, root in enumerate(roots):
                is_last = i == len(roots) - 1
                self._render_tree_node(root, lines, "", is_last)

        return "\n".join(lines)

    def render_summary(self) -> str:
        """渲染摘要"""
        progress = self._dag.get_progress()
        waves = self._dag.compute_waves()

        lines = [
            "┌─────────────────────────────────────┐",
            "│          任务执行摘要               │",
            "├─────────────────────────────────────┤",
            f"│ 总任务数:     {progress['total']:<20} │",
            f"│ 已完成:       {progress['completed']:<20} │",
            f"│ 执行中:       {progress['running']:<20} │",
            f"│ 待执行:       {progress['pending']:<20} │",
            f"│ 失败:         {progress['failed']:<20} │",
            f"│ 波次总数:     {len(waves):<20} │",
            f"│ 当前波次:     {progress['current_wave'] + 1:<20} │",
            "├─────────────────────────────────────┤",
            f"│ 进度: {self.render_progress_bar(25)}  │",
            "└─────────────────────────────────────┘",
        ]

        return "\n".join(lines)

    def render_critical_path(self) -> str:
        """渲染关键路径"""
        path = self._dag.get_critical_path()

        if not path:
            return "无关键路径"

        lines = ["关键路径:"]
        for i, task_id in enumerate(path):
            node = self._dag.get_task(task_id)
            if node:
                icon = self.STATE_ICONS.get(node.state, "?")
                arrow = "  │" if i < len(path) - 1 else ""
                lines.append(f"  {icon} {node.name} ({node.estimated_duration_s}s)")
                if arrow:
                    lines.append(f"  ↓")

        # 计算总时长
        total_duration = sum(
            self._dag.get_task(tid).estimated_duration_s
            for tid in path
            if self._dag.get_task(tid)
        )
        lines.append(f"\n预计总时长: {total_duration}s")

        return "\n".join(lines)

    def _render_task_line(self, node: TaskNode, show_deps: bool = False) -> str:
        """渲染单个任务行"""
        icon = self.STATE_ICONS.get(node.state, "?")
        model_tag = self.MODEL_TAGS.get(node.model, "[?]")

        line = f"{icon} {model_tag} {node.name}"

        if show_deps and node.dependencies:
            deps = ", ".join(sorted(node.dependencies)[:3])
            if len(node.dependencies) > 3:
                deps += f"... (+{len(node.dependencies) - 3})"
            line += f" ← {deps}"

        # 截断
        if len(line) > 50:
            line = line[:47] + "..."

        return line

    def _render_tree_node(
        self,
        task_id: str,
        lines: List[str],
        prefix: str,
        is_last: bool,
    ):
        """递归渲染树节点"""
        node = self._dag.get_task(task_id)
        if not node:
            return

        # 连接符
        connector = "└── " if is_last else "├── "
        icon = self.STATE_ICONS.get(node.state, "?")

        lines.append(f"{prefix}{connector}{icon} {node.name}")

        # 子节点前缀
        child_prefix = prefix + ("    " if is_last else "│   ")

        # 渲染被依赖的任务
        dependents = sorted(node.dependents)
        for i, dep_id in enumerate(dependents):
            is_last_child = i == len(dependents) - 1
            self._render_tree_node(dep_id, lines, child_prefix, is_last_child)
