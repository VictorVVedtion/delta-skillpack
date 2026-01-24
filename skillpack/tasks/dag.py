"""
任务 DAG 依赖图 (v6.0)

管理任务依赖关系，支持波次计算和并行执行。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from datetime import datetime


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"         # 等待执行
    READY = "ready"             # 依赖已满足，可执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    SKIPPED = "skipped"         # 跳过
    BLOCKED = "blocked"         # 被阻塞


class DependencyError(Exception):
    """依赖错误"""
    pass


@dataclass
class TaskNode:
    """任务节点"""
    id: str                                    # 任务 ID
    name: str                                  # 任务名称
    description: str = ""                      # 任务描述
    state: TaskState = TaskState.PENDING       # 当前状态
    dependencies: Set[str] = field(default_factory=set)  # 依赖的任务 ID
    dependents: Set[str] = field(default_factory=set)    # 被依赖的任务 ID
    wave: int = 0                              # 所属波次
    model: str = "codex"                       # 执行模型
    priority: int = 100                        # 优先级
    estimated_duration_s: int = 60             # 预估时长（秒）

    # 执行信息
    started_at: Optional[str] = None           # 开始时间
    completed_at: Optional[str] = None         # 完成时间
    result: Optional[str] = None               # 执行结果
    error: Optional[str] = None                # 错误信息
    output_file: Optional[str] = None          # 输出文件

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self) -> bool:
        """检查是否可以执行"""
        return self.state == TaskState.READY

    def mark_running(self):
        """标记为执行中"""
        self.state = TaskState.RUNNING
        self.started_at = datetime.now().isoformat()

    def mark_completed(self, result: Optional[str] = None):
        """标记为完成"""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.now().isoformat()
        self.result = result

    def mark_failed(self, error: str):
        """标记为失败"""
        self.state = TaskState.FAILED
        self.completed_at = datetime.now().isoformat()
        self.error = error


class TaskDAG:
    """
    任务有向无环图

    支持功能:
    - 添加/移除任务和依赖
    - 环检测
    - 拓扑排序
    - 波次计算
    - 并行度分析
    """

    def __init__(self):
        self._nodes: Dict[str, TaskNode] = {}
        self._waves: List[List[str]] = []
        self._computed = False

    def add_task(
        self,
        task_id: str,
        name: str,
        description: str = "",
        dependencies: Optional[List[str]] = None,
        model: str = "codex",
        priority: int = 100,
        estimated_duration_s: int = 60,
        metadata: Optional[Dict] = None,
    ) -> TaskNode:
        """
        添加任务

        Args:
            task_id: 任务 ID
            name: 任务名称
            description: 任务描述
            dependencies: 依赖的任务 ID 列表
            model: 执行模型
            priority: 优先级
            estimated_duration_s: 预估时长
            metadata: 元数据

        Returns:
            创建的任务节点

        Raises:
            DependencyError: 依赖不存在或形成环
        """
        if task_id in self._nodes:
            raise DependencyError(f"任务 {task_id} 已存在")

        # 创建节点
        node = TaskNode(
            id=task_id,
            name=name,
            description=description,
            dependencies=set(dependencies or []),
            model=model,
            priority=priority,
            estimated_duration_s=estimated_duration_s,
            metadata=metadata or {},
        )

        # 验证依赖存在
        for dep_id in node.dependencies:
            if dep_id not in self._nodes:
                raise DependencyError(f"依赖任务 {dep_id} 不存在")

        # 添加节点
        self._nodes[task_id] = node

        # 更新依赖关系
        for dep_id in node.dependencies:
            self._nodes[dep_id].dependents.add(task_id)

        # 标记需要重新计算
        self._computed = False

        return node

    def add_dependency(self, task_id: str, depends_on: str):
        """
        添加依赖关系

        Args:
            task_id: 任务 ID
            depends_on: 依赖的任务 ID

        Raises:
            DependencyError: 任务不存在或形成环
        """
        if task_id not in self._nodes:
            raise DependencyError(f"任务 {task_id} 不存在")
        if depends_on not in self._nodes:
            raise DependencyError(f"依赖任务 {depends_on} 不存在")

        # 检查是否会形成环
        if self._would_create_cycle(task_id, depends_on):
            raise DependencyError(f"添加依赖 {task_id} -> {depends_on} 会形成环")

        self._nodes[task_id].dependencies.add(depends_on)
        self._nodes[depends_on].dependents.add(task_id)
        self._computed = False

    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id not in self._nodes:
            return

        node = self._nodes[task_id]

        # 移除依赖关系
        for dep_id in node.dependencies:
            if dep_id in self._nodes:
                self._nodes[dep_id].dependents.discard(task_id)

        # 移除被依赖关系
        for dependent_id in node.dependents:
            if dependent_id in self._nodes:
                self._nodes[dependent_id].dependencies.discard(task_id)

        del self._nodes[task_id]
        self._computed = False

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """获取任务"""
        return self._nodes.get(task_id)

    def compute_waves(self) -> List[List[str]]:
        """
        计算执行波次

        同一波次内的任务可以并行执行。

        Returns:
            波次列表，每个波次包含任务 ID 列表
        """
        if self._computed and self._waves:
            return self._waves

        self._waves = []
        remaining = set(self._nodes.keys())

        while remaining:
            # 找出当前可执行的任务（依赖都已完成或在之前波次）
            current_wave = []
            completed = set(self._nodes.keys()) - remaining

            for task_id in remaining:
                node = self._nodes[task_id]
                if node.dependencies.issubset(completed):
                    current_wave.append(task_id)

            if not current_wave:
                # 有环或所有剩余任务都被阻塞
                raise DependencyError("存在循环依赖或不可解析的依赖")

            # 按优先级排序
            current_wave.sort(key=lambda tid: self._nodes[tid].priority)

            # 更新波次
            wave_num = len(self._waves)
            for task_id in current_wave:
                self._nodes[task_id].wave = wave_num
                remaining.remove(task_id)

            self._waves.append(current_wave)

        self._computed = True
        return self._waves

    def get_ready_tasks(self) -> List[TaskNode]:
        """获取当前可执行的任务"""
        if not self._computed:
            self.compute_waves()

        ready = []
        for node in self._nodes.values():
            if node.state == TaskState.PENDING:
                # 检查所有依赖是否完成
                deps_completed = all(
                    self._nodes[dep_id].state == TaskState.COMPLETED
                    for dep_id in node.dependencies
                )
                if deps_completed:
                    node.state = TaskState.READY
                    ready.append(node)

        ready.sort(key=lambda n: (n.wave, n.priority))
        return ready

    def update_task_state(self, task_id: str, state: TaskState, result: Optional[str] = None, error: Optional[str] = None):
        """更新任务状态"""
        if task_id not in self._nodes:
            return

        node = self._nodes[task_id]

        if state == TaskState.RUNNING:
            node.mark_running()
        elif state == TaskState.COMPLETED:
            node.mark_completed(result)
        elif state == TaskState.FAILED:
            node.mark_failed(error or "未知错误")
        else:
            node.state = state

    def get_progress(self) -> Dict[str, Any]:
        """获取进度统计"""
        total = len(self._nodes)
        completed = sum(1 for n in self._nodes.values() if n.state == TaskState.COMPLETED)
        running = sum(1 for n in self._nodes.values() if n.state == TaskState.RUNNING)
        failed = sum(1 for n in self._nodes.values() if n.state == TaskState.FAILED)
        pending = total - completed - running - failed

        return {
            "total": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "pending": pending,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "waves_total": len(self._waves) if self._computed else 0,
            "current_wave": self._get_current_wave(),
        }

    def _get_current_wave(self) -> int:
        """获取当前波次"""
        if not self._computed or not self._waves:
            return 0

        for i, wave in enumerate(self._waves):
            for task_id in wave:
                node = self._nodes[task_id]
                if node.state in (TaskState.PENDING, TaskState.READY, TaskState.RUNNING):
                    return i

        return len(self._waves) - 1

    def _would_create_cycle(self, task_id: str, depends_on: str) -> bool:
        """检查添加依赖是否会形成环"""
        # 从 depends_on 开始 DFS，看是否能到达 task_id
        visited = set()
        stack = [depends_on]

        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)

            if current in self._nodes:
                for dep_id in self._nodes[current].dependencies:
                    if dep_id not in visited:
                        stack.append(dep_id)

        return False

    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        if not self._computed:
            self.compute_waves()

        result = []
        for wave in self._waves:
            result.extend(wave)
        return result

    def get_critical_path(self) -> List[str]:
        """获取关键路径（最长执行路径）"""
        if not self._nodes:
            return []

        # 计算每个节点的最长路径
        longest_path: Dict[str, int] = {}

        def get_longest(task_id: str) -> int:
            if task_id in longest_path:
                return longest_path[task_id]

            node = self._nodes[task_id]
            if not node.dependencies:
                longest_path[task_id] = node.estimated_duration_s
            else:
                max_dep = max(get_longest(dep) for dep in node.dependencies)
                longest_path[task_id] = max_dep + node.estimated_duration_s

            return longest_path[task_id]

        # 计算所有节点
        for task_id in self._nodes:
            get_longest(task_id)

        # 找到终点（没有被依赖的节点）
        endpoints = [tid for tid, node in self._nodes.items() if not node.dependents]
        if not endpoints:
            return list(self._nodes.keys())

        # 回溯关键路径
        current = max(endpoints, key=lambda tid: longest_path[tid])
        path = [current]

        while self._nodes[current].dependencies:
            deps = list(self._nodes[current].dependencies)
            current = max(deps, key=lambda tid: longest_path[tid])
            path.append(current)

        path.reverse()
        return path

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self):
        return iter(self._nodes.values())
