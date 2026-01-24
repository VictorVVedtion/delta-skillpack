"""
任务 DAG 测试 (v6.0)
"""

import pytest

from skillpack.tasks import TaskDAG, TaskNode, DependencyError, DAGVisualizer
from skillpack.tasks.dag import TaskState


class TestTaskDAG:
    """TaskDAG 测试"""

    def test_add_task(self):
        """添加任务"""
        dag = TaskDAG()
        node = dag.add_task("task-1", "测试任务")
        assert node.id == "task-1"
        assert node.name == "测试任务"
        assert node.state == TaskState.PENDING

    def test_add_task_with_dependencies(self):
        """添加带依赖的任务"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2", dependencies=["task-1"])

        task2 = dag.get_task("task-2")
        assert "task-1" in task2.dependencies

        task1 = dag.get_task("task-1")
        assert "task-2" in task1.dependents

    def test_add_task_missing_dependency(self):
        """添加依赖不存在的任务"""
        dag = TaskDAG()
        with pytest.raises(DependencyError):
            dag.add_task("task-1", "任务1", dependencies=["non-existent"])

    def test_add_task_duplicate(self):
        """添加重复任务"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        with pytest.raises(DependencyError):
            dag.add_task("task-1", "重复任务")

    def test_compute_waves_linear(self):
        """线性依赖波次计算"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2", dependencies=["task-1"])
        dag.add_task("task-3", "任务3", dependencies=["task-2"])

        waves = dag.compute_waves()
        assert len(waves) == 3
        assert "task-1" in waves[0]
        assert "task-2" in waves[1]
        assert "task-3" in waves[2]

    def test_compute_waves_parallel(self):
        """并行任务波次计算"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2")
        dag.add_task("task-3", "任务3", dependencies=["task-1", "task-2"])

        waves = dag.compute_waves()
        assert len(waves) == 2
        assert set(waves[0]) == {"task-1", "task-2"}
        assert "task-3" in waves[1]

    def test_compute_waves_complex(self):
        """复杂依赖波次计算"""
        dag = TaskDAG()
        dag.add_task("a", "A")
        dag.add_task("b", "B")
        dag.add_task("c", "C", dependencies=["a"])
        dag.add_task("d", "D", dependencies=["a", "b"])
        dag.add_task("e", "E", dependencies=["c", "d"])

        waves = dag.compute_waves()
        assert len(waves) == 3
        # 第一波：a, b
        assert set(waves[0]) == {"a", "b"}
        # 第二波：c, d
        assert set(waves[1]) == {"c", "d"}
        # 第三波：e
        assert waves[2] == ["e"]

    def test_get_ready_tasks(self):
        """获取可执行任务"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2", dependencies=["task-1"])

        # 初始状态，只有 task-1 可执行
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "task-1"

        # 完成 task-1 后，task-2 可执行
        dag.update_task_state("task-1", TaskState.COMPLETED)
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "task-2"

    def test_get_progress(self):
        """进度统计"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2")
        dag.add_task("task-3", "任务3")

        progress = dag.get_progress()
        assert progress["total"] == 3
        assert progress["pending"] == 3
        assert progress["completed"] == 0

        dag.update_task_state("task-1", TaskState.COMPLETED)
        progress = dag.get_progress()
        assert progress["completed"] == 1
        assert progress["progress_percent"] == pytest.approx(33.33, 0.1)

    def test_topological_sort(self):
        """拓扑排序"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2", dependencies=["task-1"])
        dag.add_task("task-3", "任务3", dependencies=["task-2"])

        sorted_tasks = dag.topological_sort()
        assert sorted_tasks.index("task-1") < sorted_tasks.index("task-2")
        assert sorted_tasks.index("task-2") < sorted_tasks.index("task-3")

    def test_critical_path(self):
        """关键路径计算"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1", estimated_duration_s=10)
        dag.add_task("task-2", "任务2", estimated_duration_s=5)
        dag.add_task("task-3", "任务3", dependencies=["task-1"], estimated_duration_s=20)
        dag.add_task("task-4", "任务4", dependencies=["task-2"], estimated_duration_s=5)
        dag.add_task("task-5", "任务5", dependencies=["task-3", "task-4"], estimated_duration_s=10)

        path = dag.get_critical_path()
        # 关键路径应该是 task-1 -> task-3 -> task-5 (10+20+10=40)
        # 而不是 task-2 -> task-4 -> task-5 (5+5+10=20)
        assert "task-1" in path
        assert "task-3" in path
        assert "task-5" in path

    def test_cycle_detection(self):
        """环检测"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2", dependencies=["task-1"])

        # 尝试添加会形成环的依赖
        with pytest.raises(DependencyError):
            dag.add_dependency("task-1", "task-2")


class TestTaskNode:
    """TaskNode 测试"""

    def test_mark_running(self):
        """标记为执行中"""
        node = TaskNode(id="task-1", name="测试")
        node.mark_running()
        assert node.state == TaskState.RUNNING
        assert node.started_at is not None

    def test_mark_completed(self):
        """标记为完成"""
        node = TaskNode(id="task-1", name="测试")
        node.mark_completed("成功")
        assert node.state == TaskState.COMPLETED
        assert node.result == "成功"
        assert node.completed_at is not None

    def test_mark_failed(self):
        """标记为失败"""
        node = TaskNode(id="task-1", name="测试")
        node.mark_failed("出错了")
        assert node.state == TaskState.FAILED
        assert node.error == "出错了"


class TestDAGVisualizer:
    """DAGVisualizer 测试"""

    def test_render_summary(self):
        """渲染摘要"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2")

        visualizer = DAGVisualizer(dag)
        summary = visualizer.render_summary()
        assert "总任务数" in summary
        assert "2" in summary

    def test_render_progress_bar(self):
        """渲染进度条"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1")
        dag.add_task("task-2", "任务2")
        dag.update_task_state("task-1", TaskState.COMPLETED)

        visualizer = DAGVisualizer(dag)
        bar = visualizer.render_progress_bar()
        assert "█" in bar
        assert "50%" in bar

    def test_render_waves(self):
        """渲染波次图"""
        dag = TaskDAG()
        dag.add_task("task-1", "任务1", model="codex")
        dag.add_task("task-2", "任务2", model="gemini")

        visualizer = DAGVisualizer(dag)
        waves = visualizer.render_waves()
        assert "Wave 1" in waves
        assert "[C]" in waves or "[G]" in waves
