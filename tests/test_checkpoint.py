"""
检查点机制测试

测试任务检查点的创建、保存、加载和恢复功能。
"""

import json
import pytest
from pathlib import Path
from datetime import datetime


class TestCheckpointCreation:
    """检查点创建测试"""

    def test_create_checkpoint(self, checkpoint_factory):
        """创建检查点文件"""
        checkpoint_path = checkpoint_factory()

        assert checkpoint_path.exists()
        assert checkpoint_path.name == "checkpoint.json"

    def test_checkpoint_default_content(self, checkpoint_factory):
        """检查点默认内容"""
        checkpoint_path = checkpoint_factory()
        data = json.loads(checkpoint_path.read_text())

        assert data["task_id"] == "test-task"
        assert data["description"] == "Test task description"
        assert data["status"] == "in_progress"
        assert data["progress"] == 0.5
        assert data["route"] == "PLANNED"

    def test_checkpoint_custom_content(self, checkpoint_factory):
        """自定义检查点内容"""
        checkpoint_path = checkpoint_factory(
            task_id="custom-task-123",
            description="Custom task",
            status="completed",
            progress=1.0,
            route="RALPH",
        )
        data = json.loads(checkpoint_path.read_text())

        assert data["task_id"] == "custom-task-123"
        assert data["description"] == "Custom task"
        assert data["status"] == "completed"
        assert data["progress"] == 1.0
        assert data["route"] == "RALPH"

    def test_checkpoint_with_extra_data(self, checkpoint_factory):
        """带额外数据的检查点"""
        checkpoint_path = checkpoint_factory(
            extra_data={
                "subtasks_completed": 5,
                "subtasks_total": 10,
                "current_phase": "implementing",
            }
        )
        data = json.loads(checkpoint_path.read_text())

        assert data["subtasks_completed"] == 5
        assert data["subtasks_total"] == 10
        assert data["current_phase"] == "implementing"


class TestCheckpointDirectoryStructure:
    """检查点目录结构测试"""

    def test_current_directory_created(self, checkpoint_factory, temp_dir):
        """current 目录创建"""
        checkpoint_factory()

        current_dir = temp_dir / ".skillpack" / "current"
        assert current_dir.exists()
        assert current_dir.is_dir()

    def test_checkpoint_in_correct_location(self, checkpoint_factory, temp_dir):
        """检查点文件位置正确"""
        checkpoint_path = checkpoint_factory()

        expected_path = temp_dir / ".skillpack" / "current" / "checkpoint.json"
        assert checkpoint_path == expected_path


class TestCheckpointStatus:
    """检查点状态测试"""

    @pytest.mark.parametrize("status", [
        "pending",
        "in_progress",
        "completed",
        "failed",
        "paused",
    ])
    def test_checkpoint_status_values(self, checkpoint_factory, status):
        """检查点状态值测试"""
        checkpoint_path = checkpoint_factory(status=status)
        data = json.loads(checkpoint_path.read_text())

        assert data["status"] == status


class TestCheckpointProgress:
    """检查点进度测试"""

    @pytest.mark.parametrize("progress", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_checkpoint_progress_values(self, checkpoint_factory, progress):
        """检查点进度值测试"""
        checkpoint_path = checkpoint_factory(progress=progress)
        data = json.loads(checkpoint_path.read_text())

        assert data["progress"] == progress


class TestCheckpointRoute:
    """检查点路由测试"""

    @pytest.mark.parametrize("route", [
        "DIRECT",
        "PLANNED",
        "RALPH",
        "ARCHITECT",
        "UI_FLOW",
    ])
    def test_checkpoint_route_values(self, checkpoint_factory, route):
        """检查点路由值测试"""
        checkpoint_path = checkpoint_factory(route=route)
        data = json.loads(checkpoint_path.read_text())

        assert data["route"] == route


class TestCheckpointRecovery:
    """检查点恢复测试"""

    def test_load_checkpoint(self, checkpoint_factory):
        """加载检查点"""
        checkpoint_path = checkpoint_factory()

        # 验证可以正确读取
        data = json.loads(checkpoint_path.read_text())
        assert isinstance(data, dict)
        assert "task_id" in data

    def test_checkpoint_file_integrity(self, checkpoint_factory):
        """检查点文件完整性"""
        checkpoint_path = checkpoint_factory()

        # 读取并验证 JSON 格式
        with open(checkpoint_path) as f:
            data = json.load(f)

        # 重新写入应该产生相同内容
        original_content = checkpoint_path.read_text()
        checkpoint_path.write_text(json.dumps(data, indent=2))

        # JSON 重新格式化后比较
        new_data = json.loads(checkpoint_path.read_text())
        assert data == new_data


class TestCheckpointHistory:
    """检查点历史测试"""

    def test_history_directory_creation(self, temp_dir, executor, task_context_factory):
        """历史目录创建"""
        context = task_context_factory(working_dir=temp_dir)

        # 执行任务
        executor.execute(context)

        # 验证历史目录创建
        history_dir = temp_dir / ".skillpack" / "history"
        assert history_dir.exists()


class TestCheckpointTimestamp:
    """检查点时间戳测试"""

    def test_checkpoint_with_timestamp(self, checkpoint_factory):
        """带时间戳的检查点"""
        timestamp = datetime.now().isoformat()
        checkpoint_path = checkpoint_factory(
            extra_data={"timestamp": timestamp}
        )
        data = json.loads(checkpoint_path.read_text())

        assert "timestamp" in data
        assert data["timestamp"] == timestamp


class TestCheckpointSubtasks:
    """检查点子任务测试"""

    def test_checkpoint_with_subtasks(self, checkpoint_factory):
        """带子任务的检查点"""
        checkpoint_path = checkpoint_factory(
            route="RALPH",
            extra_data={
                "subtasks": [
                    {"id": "st-1", "status": "completed", "description": "Task 1"},
                    {"id": "st-2", "status": "in_progress", "description": "Task 2"},
                    {"id": "st-3", "status": "pending", "description": "Task 3"},
                ]
            }
        )
        data = json.loads(checkpoint_path.read_text())

        assert len(data["subtasks"]) == 3
        assert data["subtasks"][0]["status"] == "completed"
        assert data["subtasks"][1]["status"] == "in_progress"
        assert data["subtasks"][2]["status"] == "pending"


class TestCheckpointError:
    """检查点错误处理测试"""

    def test_checkpoint_with_error(self, checkpoint_factory):
        """带错误信息的检查点"""
        checkpoint_path = checkpoint_factory(
            status="failed",
            extra_data={
                "error": "Connection timeout",
                "error_phase": "implementing",
            }
        )
        data = json.loads(checkpoint_path.read_text())

        assert data["status"] == "failed"
        assert data["error"] == "Connection timeout"
        assert data["error_phase"] == "implementing"


class TestMultipleCheckpoints:
    """多检查点测试"""

    def test_overwrite_checkpoint(self, checkpoint_factory):
        """覆盖检查点"""
        # 创建第一个检查点
        checkpoint_path = checkpoint_factory(progress=0.3)
        first_data = json.loads(checkpoint_path.read_text())
        assert first_data["progress"] == 0.3

        # 覆盖检查点
        checkpoint_path = checkpoint_factory(progress=0.7)
        second_data = json.loads(checkpoint_path.read_text())
        assert second_data["progress"] == 0.7


# =============================================================================
# CheckpointManager 测试 (v5.4.2)
# =============================================================================

from skillpack.checkpoint import (
    Checkpoint,
    CheckpointManager,
    PhaseCheckpoint,
    PhaseStatus,
    RecoveryInfo,
)


class TestCheckpointModel:
    """Checkpoint 数据模型测试"""

    def test_create_default(self):
        """测试默认创建"""
        cp = Checkpoint()
        assert cp.version == "3.0"
        assert cp.task_id == ""
        assert cp.progress == 0.0
        assert cp.status == "running"

    def test_create_with_phases(self):
        """测试带阶段创建"""
        cp = Checkpoint(
            task_id="test-123",
            phases=[
                PhaseCheckpoint(number=1, name="分析", status="completed"),
                PhaseCheckpoint(number=2, name="实现", status="running"),
            ],
        )
        assert len(cp.phases) == 2
        assert cp.phases[0].status == "completed"

    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        original = Checkpoint(
            task_id="round-trip",
            task_description="往返测试",
            route="RALPH",
            current_phase=2,
            total_phases=5,
            phases=[
                PhaseCheckpoint(number=1, name="Phase 1", status="completed"),
            ],
        )

        # 序列化
        data = original.to_dict()
        assert data["task_id"] == "round-trip"

        # 反序列化
        restored = Checkpoint.from_dict(data)
        assert restored.task_id == original.task_id
        assert restored.route == original.route

    def test_get_resume_info(self):
        """测试获取恢复信息"""
        cp = Checkpoint(
            task_id="resume-test",
            total_phases=3,
            phases=[
                PhaseCheckpoint(number=1, name="P1", status="completed"),
                PhaseCheckpoint(number=2, name="P2", status="failed"),
                PhaseCheckpoint(number=3, name="P3", status="pending"),
            ],
        )

        info = cp.get_resume_info()
        assert info["resume_phase"] == 2  # 第一个未完成的阶段


class TestCheckpointManagerBasic:
    """CheckpointManager 基础功能测试"""

    @pytest.fixture
    def manager(self, temp_dir):
        """创建管理器"""
        current = temp_dir / ".skillpack" / "current"
        history = temp_dir / ".skillpack" / "history"
        return CheckpointManager(
            current_dir=str(current),
            history_dir=str(history),
        )

    def test_save_and_load(self, manager):
        """测试保存和加载"""
        cp = Checkpoint(
            task_id="save-load-test",
            task_description="保存加载测试",
        )

        # 保存
        result = manager.save(cp)
        assert result is True

        # 加载
        loaded = manager.load_current()
        assert loaded is not None
        assert loaded.task_id == "save-load-test"

    def test_load_nonexistent(self, manager):
        """测试加载不存在的检查点"""
        loaded = manager.load_current()
        assert loaded is None

    def test_save_creates_checksum(self, manager):
        """测试保存创建校验和文件"""
        cp = Checkpoint(task_id="checksum-test")
        manager.save(cp)

        checksum_path = Path(manager.current_dir) / "checkpoint.json.sha256"
        assert checksum_path.exists()

    def test_backup_rotation(self, manager):
        """测试备份轮转"""
        # 多次保存
        for i in range(5):
            cp = Checkpoint(task_id=f"backup-test-{i}")
            manager.save(cp)

        # 检查备份文件
        backup1 = Path(manager.current_dir) / "checkpoint.json.backup.1"
        backup2 = Path(manager.current_dir) / "checkpoint.json.backup.2"
        backup3 = Path(manager.current_dir) / "checkpoint.json.backup.3"

        assert backup1.exists()
        assert backup2.exists()
        assert backup3.exists()


class TestCheckpointManagerOperations:
    """CheckpointManager 操作测试"""

    @pytest.fixture
    def manager(self, temp_dir):
        """创建管理器"""
        current = temp_dir / ".skillpack" / "current"
        history = temp_dir / ".skillpack" / "history"
        return CheckpointManager(
            current_dir=str(current),
            history_dir=str(history),
        )

    def test_list_checkpoints(self, manager, temp_dir):
        """测试列出检查点"""
        # 保存当前检查点
        cp = Checkpoint(task_id="list-test")
        manager.save(cp)

        # 创建历史检查点
        hist_dir = Path(manager.history_dir) / "20260121_hist"
        hist_dir.mkdir(parents=True)
        hist_cp = Checkpoint(task_id="history-task")
        (hist_dir / "checkpoint.json").write_text(
            json.dumps(hist_cp.to_dict(), indent=2)
        )

        # 列出
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) >= 1

    def test_update_phase(self, manager):
        """测试更新阶段状态"""
        cp = Checkpoint(
            task_id="phase-update-test",
            total_phases=3,
            phases=[
                PhaseCheckpoint(number=1, name="P1", status="pending"),
                PhaseCheckpoint(number=2, name="P2", status="pending"),
            ],
        )
        manager.save(cp)

        # 更新阶段
        result = manager.update_phase(1, "completed")
        assert result is True

        # 验证
        loaded = manager.load_current()
        assert loaded.phases[0].status == "completed"

    def test_mark_completed(self, manager):
        """测试标记完成"""
        cp = Checkpoint(task_id="complete-test")
        manager.save(cp)

        manager.mark_completed()

        loaded = manager.load_current()
        assert loaded.status == "completed"
        assert loaded.progress == 1.0

    def test_mark_failed(self, manager):
        """测试标记失败"""
        cp = Checkpoint(task_id="fail-test")
        manager.save(cp)

        manager.mark_failed("Test error message")

        loaded = manager.load_current()
        assert loaded.status == "failed"
        assert len(loaded.recovery.error_log) == 1

    def test_archive_current(self, manager):
        """测试归档当前检查点"""
        cp = Checkpoint(task_id="archive-test")
        manager.save(cp)

        # 添加输出文件
        (Path(manager.current_dir) / "output.md").write_text("test output")

        # 归档
        archive_path = manager.archive_current()
        assert archive_path is not None
        assert archive_path.exists()
        assert (archive_path / "checkpoint.json").exists()


class TestCheckpointManagerRecovery:
    """CheckpointManager 恢复功能测试"""

    @pytest.fixture
    def manager(self, temp_dir):
        """创建管理器"""
        current = temp_dir / ".skillpack" / "current"
        history = temp_dir / ".skillpack" / "history"
        return CheckpointManager(
            current_dir=str(current),
            history_dir=str(history),
            backup_count=3,
        )

    def test_recover_from_backup(self, manager):
        """测试从备份恢复"""
        # 保存两次创建备份
        manager.save(Checkpoint(task_id="v1"))
        manager.save(Checkpoint(task_id="v2"))

        # 损坏主文件
        checkpoint_path = Path(manager.current_dir) / "checkpoint.json"
        checkpoint_path.write_text("corrupted json {{{")

        # 加载应从备份恢复
        loaded = manager.load_current()
        assert loaded is not None
        assert loaded.task_id == "v1"

    def test_get_resumable_checkpoint(self, manager):
        """测试获取可恢复检查点"""
        cp = Checkpoint(
            task_id="resumable-test",
            status="running",
        )
        cp.recovery = RecoveryInfo(can_resume=True, resume_phase=2)
        manager.save(cp)

        result = manager.get_resumable_checkpoint()
        assert result is not None
        assert result.task_id == "resumable-test"


class TestCheckpointIntegration:
    """检查点集成测试"""

    def test_full_workflow(self, temp_dir):
        """测试完整工作流"""
        manager = CheckpointManager(
            current_dir=str(temp_dir / ".skillpack" / "current"),
            history_dir=str(temp_dir / ".skillpack" / "history"),
        )

        # 1. 创建任务
        cp = Checkpoint(
            task_id="workflow-test",
            task_description="工作流测试",
            route="PLANNED",
            total_phases=3,
            phases=[
                PhaseCheckpoint(number=1, name="规划", status="pending"),
                PhaseCheckpoint(number=2, name="实现", status="pending"),
                PhaseCheckpoint(number=3, name="审查", status="pending"),
            ],
        )
        manager.save(cp)

        # 2. 执行各阶段
        manager.update_phase(1, "completed")
        manager.update_phase(2, "running")

        # 3. 模拟中断
        loaded = manager.load_current()
        info = loaded.get_resume_info()
        assert info["resume_phase"] == 2

        # 4. 恢复并完成
        manager.update_phase(2, "completed")
        manager.update_phase(3, "completed")
        manager.mark_completed()

        # 5. 验证
        final = manager.load_current()
        assert final.status == "completed"

        # 6. 归档
        archive = manager.archive_current()
        assert archive.exists()
