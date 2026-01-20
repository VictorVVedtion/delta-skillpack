"""
Skillpack 测试共享 fixtures

为所有测试提供统一的 fixtures 和测试工具。
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Callable

from click.testing import CliRunner

from skillpack.models import (
    TaskComplexity,
    ExecutionRoute,
    ScoreCard,
    TaskContext,
    SkillpackConfig,
    KnowledgeConfig,
    RoutingConfig,
    CheckpointConfig,
    ParallelConfig,
)
from skillpack.router import TaskRouter
from skillpack.executor import TaskExecutor
from skillpack.ralph.dashboard import SimpleProgressTracker, Phase, ProgressCallback


# =============================================================================
# CLI Fixtures
# =============================================================================

@pytest.fixture
def runner():
    """Click CLI 测试运行器"""
    return CliRunner()


@pytest.fixture
def isolated_filesystem(runner):
    """隔离的文件系统"""
    with runner.isolated_filesystem() as fs:
        yield Path(fs) if isinstance(fs, str) else Path.cwd()


@pytest.fixture
def temp_dir():
    """临时目录 fixture"""
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


# =============================================================================
# Factory Fixtures
# =============================================================================

@pytest.fixture
def score_card_factory():
    """评分卡工厂 - 按比例创建指定总分的 ScoreCard"""
    def _factory(
        total: int,
        scope_ratio: float = 0.25,
        dependency_ratio: float = 0.20,
        technical_ratio: float = 0.20,
        risk_ratio: float = 0.15,
        time_ratio: float = 0.10,
        ui_ratio: float = 0.10,
    ) -> ScoreCard:
        """
        根据总分按比例分配各维度分数。

        Args:
            total: 目标总分 (0-100)
            *_ratio: 各维度权重比例

        Returns:
            ScoreCard 实例
        """
        # 确保比例总和为 1
        ratios_sum = scope_ratio + dependency_ratio + technical_ratio + risk_ratio + time_ratio + ui_ratio

        # 计算各维度分数并限制在合理范围
        scope = min(25, max(0, int(total * (scope_ratio / ratios_sum))))
        dependency = min(20, max(0, int(total * (dependency_ratio / ratios_sum))))
        technical = min(20, max(0, int(total * (technical_ratio / ratios_sum))))
        risk = min(15, max(0, int(total * (risk_ratio / ratios_sum))))
        time = min(10, max(0, int(total * (time_ratio / ratios_sum))))
        ui = min(10, max(0, int(total * (ui_ratio / ratios_sum))))

        # 调整确保总分准确
        current = scope + dependency + technical + risk + time + ui
        diff = total - current

        # 简单调整: 在 scope 上加减差值
        scope = min(25, max(0, scope + diff))

        return ScoreCard(
            scope=scope,
            dependency=dependency,
            technical=technical,
            risk=risk,
            time=time,
            ui=ui,
        )

    return _factory


@pytest.fixture
def task_context_factory():
    """TaskContext 工厂"""
    def _factory(
        description: str = "Test task",
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        route: ExecutionRoute = ExecutionRoute.PLANNED,
        working_dir: Optional[Path] = None,
        notebook_id: Optional[str] = None,
        score_card: Optional[ScoreCard] = None,
        quick_mode: bool = False,
        deep_mode: bool = False,
        parallel_mode: Optional[bool] = None,
        cli_mode: bool = False,
    ) -> TaskContext:
        return TaskContext(
            description=description,
            complexity=complexity,
            route=route,
            working_dir=working_dir,
            notebook_id=notebook_id,
            score_card=score_card,
            quick_mode=quick_mode,
            deep_mode=deep_mode,
            parallel_mode=parallel_mode,
            cli_mode=cli_mode,
        )

    return _factory


@pytest.fixture
def config_factory():
    """SkillpackConfig 工厂"""
    def _factory(
        version: str = "5.4",
        default_notebook: Optional[str] = None,
        auto_query: bool = True,
        thresholds: Optional[dict] = None,
        parallel_enabled: bool = False,
    ) -> SkillpackConfig:
        knowledge = KnowledgeConfig(
            default_notebook=default_notebook,
            auto_query=auto_query,
        )

        routing = RoutingConfig()
        if thresholds:
            routing.thresholds = thresholds

        parallel = ParallelConfig(enabled=parallel_enabled)

        return SkillpackConfig(
            version=version,
            knowledge=knowledge,
            routing=routing,
            parallel=parallel,
        )

    return _factory


@pytest.fixture
def checkpoint_factory(temp_dir):
    """检查点工厂"""
    def _factory(
        task_id: str = "test-task",
        description: str = "Test task description",
        status: str = "in_progress",
        progress: float = 0.5,
        route: str = "PLANNED",
        extra_data: Optional[dict] = None,
    ) -> Path:
        """创建检查点文件并返回路径"""
        checkpoint_dir = temp_dir / ".skillpack" / "current"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = checkpoint_dir / "checkpoint.json"

        data = {
            "task_id": task_id,
            "description": description,
            "status": status,
            "progress": progress,
            "route": route,
        }

        if extra_data:
            data.update(extra_data)

        checkpoint_file.write_text(json.dumps(data, indent=2))
        return checkpoint_file

    return _factory


# =============================================================================
# Grounding Fixtures (from test_grounding.py)
# =============================================================================

@pytest.fixture
def evidence_factory():
    """Evidence 工厂"""
    # 导入 test_grounding 中定义的类
    from tests.test_grounding import Evidence

    def _factory(
        file_path: str = "src/module.py",
        line: int = 42,
        code: str = "def example_function():",
        description: str = "",
    ) -> "Evidence":
        return Evidence(
            file_path=file_path,
            line=line,
            code=code,
            description=description,
        )

    return _factory


@pytest.fixture
def grounding_result_factory(evidence_factory):
    """GroundingResult 工厂"""
    from tests.test_grounding import GroundingResult

    def _factory(
        conclusion: str = "测试结论",
        evidence_count: int = 0,
        notebook_ref_count: int = 0,
    ) -> "GroundingResult":
        result = GroundingResult(conclusion)

        for i in range(evidence_count):
            result.add_evidence(evidence_factory(
                file_path=f"src/file_{i}.py",
                line=i + 1,
                code=f"code_line_{i}",
            ))

        for i in range(notebook_ref_count):
            result.add_notebook_reference(f"[NB] Reference {i}")

        return result

    return _factory


# =============================================================================
# Cross Validation Fixtures (from test_cross_validation.py)
# =============================================================================

@pytest.fixture
def model_review_result_factory():
    """ModelReviewResult 工厂"""
    from tests.test_cross_validation import ModelReviewResult, ReviewFinding

    def _factory(
        model_name: str = "Codex",
        conclusion: str = "Review complete",
        findings_count: int = 0,
        has_critical: bool = False,
        coverage_percentage: float = 90.0,
        passed: bool = True,
    ) -> "ModelReviewResult":
        findings = []

        for i in range(findings_count):
            severity = "high" if (has_critical and i == 0) else "medium"
            findings.append(ReviewFinding(
                issue=f"Issue {i}",
                severity=severity,
                file_path=f"src/file_{i}.py",
                line=i + 1,
                suggestion=f"Fix {i}",
            ))

        return ModelReviewResult(
            model_name=model_name,
            conclusion=conclusion,
            findings=findings,
            coverage_percentage=coverage_percentage,
            passed=passed,
        )

    return _factory


# =============================================================================
# Progress Tracker Fixtures
# =============================================================================

class MockProgressCallback(ProgressCallback):
    """测试用进度回调"""

    def __init__(self):
        self.phases_started: list = []
        self.progress_updates: list = []
        self.phases_completed: list = []
        self.errors: list = []

    def on_phase_start(self, phase: Phase, message: str):
        self.phases_started.append((phase, message))

    def on_progress(self, phase: Phase, progress: float, message: str):
        self.progress_updates.append((phase, progress, message))

    def on_phase_complete(self, phase: Phase):
        self.phases_completed.append(phase)

    def on_error(self, phase: Phase, error: str):
        self.errors.append((phase, error))


@pytest.fixture
def mock_callback():
    """Mock 进度回调"""
    return MockProgressCallback()


@pytest.fixture
def tracker_factory(mock_callback):
    """进度追踪器工厂"""
    def _factory(
        task_id: str = "test-task",
        description: str = "Test task",
        quiet: bool = True,
        with_callback: bool = False,
    ) -> SimpleProgressTracker:
        callback = mock_callback if with_callback else None
        return SimpleProgressTracker(
            task_id=task_id,
            description=description,
            callback=callback,
            quiet=quiet,
        )

    return _factory


# =============================================================================
# Router and Executor Fixtures
# =============================================================================

@pytest.fixture
def router():
    """默认配置的 TaskRouter"""
    return TaskRouter()


@pytest.fixture
def router_with_config(config_factory):
    """带自定义配置的 TaskRouter 工厂"""
    def _factory(**config_kwargs) -> TaskRouter:
        config = config_factory(**config_kwargs)
        return TaskRouter(config)

    return _factory


@pytest.fixture
def executor():
    """静默模式的 TaskExecutor"""
    return TaskExecutor(quiet=True)


# =============================================================================
# Skillpackrc Fixtures
# =============================================================================

@pytest.fixture
def skillpackrc_factory(temp_dir):
    """Skillpackrc 配置文件工厂"""
    def _factory(config: Optional[dict] = None) -> Path:
        """创建 .skillpackrc 配置文件"""
        config_path = temp_dir / ".skillpackrc"

        default_config = {
            "version": "5.4",
            "knowledge": {
                "default_notebook": None,
                "auto_query": True
            },
            "routing": {
                "weights": {
                    "scope": 25,
                    "dependency": 20,
                    "technical": 20,
                    "risk": 15,
                    "time": 10,
                    "ui": 10
                },
                "thresholds": {
                    "direct": 20,
                    "planned": 45,
                    "ralph": 70
                }
            },
            "checkpoint": {
                "auto_save": True,
                "save_interval_minutes": 5
            },
            "parallel": {
                "enabled": False,
                "max_concurrent_tasks": 3
            }
        }

        if config:
            # 深度合并配置
            for key, value in config.items():
                if isinstance(value, dict) and key in default_config:
                    default_config[key].update(value)
                else:
                    default_config[key] = value

        config_path.write_text(json.dumps(default_config, indent=2, ensure_ascii=False))
        return config_path

    return _factory
