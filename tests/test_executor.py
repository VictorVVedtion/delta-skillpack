"""
测试任务执行器
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from skillpack.models import (
    TaskContext,
    TaskComplexity,
    ExecutionRoute,
    SkillpackConfig,
)
from skillpack.executor import (
    TaskExecutor,
    DirectExecutor,
    PlannedExecutor,
    RalphExecutor,
    UIFlowExecutor,
)
from skillpack.ralph.dashboard import (
    ProgressTracker,
    SimpleProgressTracker,
    Phase,
    ProgressCallback,
)


class MockProgressCallback(ProgressCallback):
    """测试用进度回调"""

    def __init__(self):
        self.phases_started = []
        self.progress_updates = []
        self.phases_completed = []
        self.errors = []

    def on_phase_start(self, phase: Phase, message: str):
        self.phases_started.append((phase, message))

    def on_progress(self, phase: Phase, progress: float, message: str):
        self.progress_updates.append((phase, progress, message))

    def on_phase_complete(self, phase: Phase):
        self.phases_completed.append(phase)

    def on_error(self, phase: Phase, error: str):
        self.errors.append((phase, error))


class TestProgressTracker:
    """进度追踪器测试"""

    def test_tracker_lifecycle(self):
        tracker = SimpleProgressTracker("test-id", "Test task")

        tracker.start_phase(Phase.PLANNING)
        assert tracker.current_phase == Phase.PLANNING

        tracker.update(0.5, "halfway")
        assert tracker.current_progress == 0.5

        tracker.complete_phase()
        assert tracker.current_progress == 1.0

        tracker.complete()
        assert tracker.current_phase == Phase.COMPLETED

    def test_tracker_events(self):
        tracker = SimpleProgressTracker("test-id", "Test task")

        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.update(0.3, "step 1")
        tracker.update(0.6, "step 2")
        tracker.complete_phase()

        assert len(tracker.events) == 4  # start + 2 updates + complete

    def test_tracker_failure(self):
        tracker = SimpleProgressTracker("test-id", "Test task")

        tracker.start_phase(Phase.IMPLEMENTING)
        tracker.fail("Something went wrong")

        assert tracker.current_phase == Phase.FAILED
        assert tracker.error == "Something went wrong"

    def test_callback_integration(self):
        callback = MockProgressCallback()
        tracker = SimpleProgressTracker(
            "test-id",
            "Test task",
            callback=callback
        )

        tracker.start_phase(Phase.PLANNING)
        tracker.update(0.5, "halfway")
        tracker.complete_phase()

        assert len(callback.phases_started) == 1
        assert len(callback.progress_updates) == 1
        assert len(callback.phases_completed) == 1


class TestExecutionStrategies:
    """执行策略测试"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_context(self, route: ExecutionRoute) -> TaskContext:
        return TaskContext(
            description="Test task",
            complexity=TaskComplexity.MEDIUM,
            route=route,
            working_dir=self.temp_dir
        )

    def test_direct_executor(self):
        executor = DirectExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)
        context = self._make_context(ExecutionRoute.DIRECT)

        status = executor.execute(context, tracker)

        assert status.is_running is False
        assert status.error is None
        assert tracker.current_phase == Phase.COMPLETED

    def test_planned_executor(self):
        executor = PlannedExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)
        context = self._make_context(ExecutionRoute.PLANNED)

        status = executor.execute(context, tracker)

        assert status.is_running is False
        assert tracker.current_phase == Phase.COMPLETED

    def test_ralph_executor(self):
        executor = RalphExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)
        context = self._make_context(ExecutionRoute.RALPH)

        status = executor.execute(context, tracker)

        assert status.is_running is False
        assert tracker.current_phase == Phase.COMPLETED

    def test_ui_flow_executor(self):
        executor = UIFlowExecutor()
        tracker = SimpleProgressTracker("test", "Test", quiet=True)
        context = self._make_context(ExecutionRoute.UI_FLOW)

        status = executor.execute(context, tracker)

        assert status.is_running is False
        assert tracker.current_phase == Phase.COMPLETED


class TestTaskExecutor:
    """TaskExecutor 集成测试"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_executor_creates_output_dir(self):
        executor = TaskExecutor(quiet=True)
        context = TaskContext(
            description="Test task",
            complexity=TaskComplexity.SIMPLE,
            route=ExecutionRoute.DIRECT,
            working_dir=self.temp_dir
        )

        status = executor.execute(context)

        current_dir = self.temp_dir / ".skillpack" / "current"
        assert current_dir.exists()

    def test_executor_archives_to_history(self):
        executor = TaskExecutor(quiet=True)
        context = TaskContext(
            description="Test task",
            complexity=TaskComplexity.SIMPLE,
            route=ExecutionRoute.DIRECT,
            working_dir=self.temp_dir
        )

        status = executor.execute(context)

        history_dir = self.temp_dir / ".skillpack" / "history"
        assert history_dir.exists()

    def test_executor_routes_correctly(self):
        """验证执行器根据路由选择正确策略"""
        executor = TaskExecutor(quiet=True)

        # DIRECT 路由
        context = TaskContext(
            description="Simple task",
            complexity=TaskComplexity.SIMPLE,
            route=ExecutionRoute.DIRECT,
            working_dir=self.temp_dir
        )
        status = executor.execute(context)
        assert status.error is None

        # RALPH 路由
        context = TaskContext(
            description="Complex task",
            complexity=TaskComplexity.COMPLEX,
            route=ExecutionRoute.RALPH,
            working_dir=self.temp_dir
        )
        status = executor.execute(context)
        assert status.error is None
