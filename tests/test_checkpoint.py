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
