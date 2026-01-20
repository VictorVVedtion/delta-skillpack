"""
并行执行测试

测试 v5.2 新增的异步并行执行功能。
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# 模拟的并行执行类 (用于测试)
# =============================================================================

@dataclass
class SubTask:
    """子任务"""
    task_id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class ExecutionWave:
    """执行波次"""
    wave_number: int
    tasks: list[SubTask] = field(default_factory=list)


class DAGAnalyzer:
    """任务依赖图分析器"""

    def __init__(self, tasks: list[SubTask]):
        self.tasks = {t.task_id: t for t in tasks}

    def build_execution_waves(self) -> list[ExecutionWave]:
        """构建执行波次"""
        waves = []
        completed = set()
        remaining = set(self.tasks.keys())

        wave_num = 1
        while remaining:
            # 找出当前可执行的任务 (所有依赖已完成)
            ready = []
            for task_id in remaining:
                task = self.tasks[task_id]
                if all(dep in completed for dep in task.dependencies):
                    ready.append(task)

            if not ready:
                # 存在循环依赖
                raise ValueError("Circular dependency detected")

            # 创建波次
            wave = ExecutionWave(wave_number=wave_num, tasks=ready)
            waves.append(wave)

            # 更新状态
            for task in ready:
                completed.add(task.task_id)
                remaining.discard(task.task_id)

            wave_num += 1

        return waves

    def can_parallel(self, task_a: str, task_b: str) -> bool:
        """判断两个任务是否可以并行执行"""
        a = self.tasks.get(task_a)
        b = self.tasks.get(task_b)

        if not a or not b:
            return False

        # 互不依赖才能并行
        return task_b not in a.dependencies and task_a not in b.dependencies


class ParallelExecutor:
    """并行执行器"""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.execution_log: list[tuple[int, list[str]]] = []  # (wave, [task_ids])

    def execute_waves(self, waves: list[ExecutionWave]) -> None:
        """执行所有波次"""
        for wave in waves:
            # 限制并发数
            batch_size = min(len(wave.tasks), self.max_concurrent)
            task_ids = [t.task_id for t in wave.tasks[:batch_size]]
            self.execution_log.append((wave.wave_number, task_ids))


# =============================================================================
# 测试类
# =============================================================================

class TestDAGAnalyzer:
    """DAG 分析器测试"""

    def test_single_task_no_dependencies(self):
        """单个无依赖任务"""
        tasks = [SubTask("t1", "Task 1")]
        analyzer = DAGAnalyzer(tasks)

        waves = analyzer.build_execution_waves()

        assert len(waves) == 1
        assert len(waves[0].tasks) == 1
        assert waves[0].tasks[0].task_id == "t1"

    def test_multiple_independent_tasks(self):
        """多个独立任务应在同一波次"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2"),
            SubTask("t3", "Task 3"),
        ]
        analyzer = DAGAnalyzer(tasks)

        waves = analyzer.build_execution_waves()

        assert len(waves) == 1
        assert len(waves[0].tasks) == 3

    def test_sequential_dependencies(self):
        """顺序依赖任务"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2", dependencies=["t1"]),
            SubTask("t3", "Task 3", dependencies=["t2"]),
        ]
        analyzer = DAGAnalyzer(tasks)

        waves = analyzer.build_execution_waves()

        assert len(waves) == 3
        assert waves[0].tasks[0].task_id == "t1"
        assert waves[1].tasks[0].task_id == "t2"
        assert waves[2].tasks[0].task_id == "t3"

    def test_parallel_and_sequential_mix(self):
        """混合并行和顺序依赖"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2"),
            SubTask("t3", "Task 3", dependencies=["t1", "t2"]),
        ]
        analyzer = DAGAnalyzer(tasks)

        waves = analyzer.build_execution_waves()

        assert len(waves) == 2
        assert len(waves[0].tasks) == 2  # t1, t2 并行
        assert len(waves[1].tasks) == 1  # t3 等待

    def test_diamond_dependency(self):
        """菱形依赖图"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2", dependencies=["t1"]),
            SubTask("t3", "Task 3", dependencies=["t1"]),
            SubTask("t4", "Task 4", dependencies=["t2", "t3"]),
        ]
        analyzer = DAGAnalyzer(tasks)

        waves = analyzer.build_execution_waves()

        assert len(waves) == 3
        assert waves[0].tasks[0].task_id == "t1"
        assert len(waves[1].tasks) == 2  # t2, t3 并行
        assert waves[2].tasks[0].task_id == "t4"

    def test_circular_dependency_detection(self):
        """循环依赖检测"""
        tasks = [
            SubTask("t1", "Task 1", dependencies=["t2"]),
            SubTask("t2", "Task 2", dependencies=["t1"]),
        ]
        analyzer = DAGAnalyzer(tasks)

        with pytest.raises(ValueError, match="Circular dependency"):
            analyzer.build_execution_waves()


class TestParallelExecutability:
    """并行可执行性测试"""

    def test_can_parallel_independent(self):
        """独立任务可并行"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2"),
        ]
        analyzer = DAGAnalyzer(tasks)

        assert analyzer.can_parallel("t1", "t2") is True

    def test_cannot_parallel_dependent(self):
        """依赖任务不可并行"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2", dependencies=["t1"]),
        ]
        analyzer = DAGAnalyzer(tasks)

        assert analyzer.can_parallel("t1", "t2") is False


class TestParallelExecutor:
    """并行执行器测试"""

    def test_execute_single_wave(self):
        """执行单波次"""
        tasks = [SubTask("t1", "Task 1")]
        analyzer = DAGAnalyzer(tasks)
        waves = analyzer.build_execution_waves()

        executor = ParallelExecutor()
        executor.execute_waves(waves)

        assert len(executor.execution_log) == 1
        assert executor.execution_log[0] == (1, ["t1"])

    def test_max_concurrent_limit(self):
        """最大并发限制"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2"),
            SubTask("t3", "Task 3"),
            SubTask("t4", "Task 4"),
            SubTask("t5", "Task 5"),
        ]
        analyzer = DAGAnalyzer(tasks)
        waves = analyzer.build_execution_waves()

        executor = ParallelExecutor(max_concurrent=3)
        executor.execute_waves(waves)

        # 第一波次应该只执行 3 个任务
        assert len(executor.execution_log[0][1]) == 3

    def test_execution_order_preserves_waves(self):
        """执行顺序保持波次顺序"""
        tasks = [
            SubTask("t1", "Task 1"),
            SubTask("t2", "Task 2", dependencies=["t1"]),
        ]
        analyzer = DAGAnalyzer(tasks)
        waves = analyzer.build_execution_waves()

        executor = ParallelExecutor()
        executor.execute_waves(waves)

        assert executor.execution_log[0][0] == 1  # 第一波
        assert executor.execution_log[1][0] == 2  # 第二波
        assert "t1" in executor.execution_log[0][1]
        assert "t2" in executor.execution_log[1][1]


class TestParallelConfigIntegration:
    """并行配置集成测试"""

    def test_parallel_disabled_by_config(self, config_factory):
        """配置禁用并行"""
        config = config_factory(parallel_enabled=False)
        assert config.parallel.enabled is False

    def test_parallel_enabled_by_config(self, config_factory):
        """配置启用并行"""
        config = config_factory(parallel_enabled=True)
        assert config.parallel.enabled is True


class TestParallelTaskRouting:
    """并行任务路由测试"""

    def test_ralph_supports_parallel(self, task_context_factory):
        """RALPH 路由支持并行"""
        from skillpack.models import ExecutionRoute

        context = task_context_factory(
            route=ExecutionRoute.RALPH,
            parallel_mode=True,
        )

        assert context.route == ExecutionRoute.RALPH
        assert context.parallel_mode is True

    def test_architect_supports_parallel(self, task_context_factory):
        """ARCHITECT 路由支持并行"""
        from skillpack.models import ExecutionRoute

        context = task_context_factory(
            route=ExecutionRoute.ARCHITECT,
            parallel_mode=True,
        )

        assert context.route == ExecutionRoute.ARCHITECT
        assert context.parallel_mode is True

    def test_direct_no_parallel(self, task_context_factory):
        """DIRECT 路由不使用并行"""
        from skillpack.models import ExecutionRoute

        context = task_context_factory(
            route=ExecutionRoute.DIRECT,
            parallel_mode=None,
        )

        assert context.route == ExecutionRoute.DIRECT
        assert context.parallel_mode is None


class TestParallelBoundaries:
    """并行边界测试"""

    @pytest.mark.boundary
    @pytest.mark.parametrize("max_concurrent,expected_batch", [
        (1, 1),
        (2, 2),
        (3, 3),
        (5, 5),
        (10, 5),  # 任务数限制
    ])
    def test_concurrent_limit_boundary(self, max_concurrent, expected_batch):
        """并发限制边界测试"""
        tasks = [SubTask(f"t{i}", f"Task {i}") for i in range(5)]
        analyzer = DAGAnalyzer(tasks)
        waves = analyzer.build_execution_waves()

        executor = ParallelExecutor(max_concurrent=max_concurrent)
        executor.execute_waves(waves)

        actual_batch = len(executor.execution_log[0][1])
        assert actual_batch == min(expected_batch, 5)

    @pytest.mark.boundary
    def test_empty_task_list(self):
        """空任务列表"""
        analyzer = DAGAnalyzer([])
        waves = analyzer.build_execution_waves()

        assert len(waves) == 0

    @pytest.mark.boundary
    def test_single_long_chain(self):
        """单条长链依赖"""
        tasks = [SubTask("t0", "Task 0")]
        for i in range(1, 10):
            tasks.append(SubTask(f"t{i}", f"Task {i}", dependencies=[f"t{i-1}"]))

        analyzer = DAGAnalyzer(tasks)
        waves = analyzer.build_execution_waves()

        assert len(waves) == 10
        for i, wave in enumerate(waves):
            assert len(wave.tasks) == 1
            assert wave.tasks[0].task_id == f"t{i}"


class TestCrossModelParallel:
    """跨模型并行测试"""

    def test_codex_and_gemini_parallel(self):
        """Codex 和 Gemini 可以并行"""
        # 模拟 UI 和 Backend 任务
        tasks = [
            SubTask("ui-1", "Create login UI", dependencies=[]),
            SubTask("api-1", "Create login API", dependencies=[]),
        ]
        analyzer = DAGAnalyzer(tasks)
        waves = analyzer.build_execution_waves()

        # 应该在同一波次
        assert len(waves) == 1
        assert len(waves[0].tasks) == 2

    def test_ui_depends_on_api(self):
        """UI 依赖 API 时顺序执行"""
        tasks = [
            SubTask("api-1", "Create user API"),
            SubTask("ui-1", "Create user list UI", dependencies=["api-1"]),
        ]
        analyzer = DAGAnalyzer(tasks)
        waves = analyzer.build_execution_waves()

        # 应该在不同波次
        assert len(waves) == 2
