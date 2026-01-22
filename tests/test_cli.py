"""
测试 CLI 命令
"""

import json
import pytest
from pathlib import Path
import tempfile
import shutil
from click.testing import CliRunner

from skillpack.cli import cli


class TestCLI:
    """CLI 测试"""

    def setup_method(self):
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_do_command_explain_mode(self):
        """测试 --explain 模式"""
        result = self.runner.invoke(cli, ["do", "fix typo", "--explain"])

        assert result.exit_code == 0
        assert "简单" in result.output or "直接执行" in result.output

    def test_do_command_complex_task(self):
        """测试复杂任务路由"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, [
                "do", "build complete authentication system", "--explain"
            ])

            assert result.exit_code == 0
            assert "Ralph" in result.output or "复杂" in result.output

    def test_do_command_ui_task(self):
        """测试 UI 任务路由"""
        result = self.runner.invoke(cli, [
            "do", "create login page component", "--explain"
        ])

        assert result.exit_code == 0
        assert "UI" in result.output

    def test_do_command_quick_mode(self):
        """测试 --quick 模式"""
        result = self.runner.invoke(cli, [
            "do", "build CMS", "--quick", "--explain"
        ])

        assert result.exit_code == 0
        assert "直接执行" in result.output

    def test_do_command_deep_mode(self):
        """测试 --deep 模式"""
        result = self.runner.invoke(cli, [
            "do", "fix typo", "--deep", "--explain"
        ])

        assert result.exit_code == 0
        assert "RALPH" in result.output or "Ralph" in result.output or "复杂" in result.output

    def test_status_command_no_task(self):
        """测试无任务时的 status 命令"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "没有" in result.output

    def test_init_command(self):
        """测试 init 命令"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert Path(".skillpackrc").exists()

    def test_init_command_already_exists(self):
        """测试配置已存在时的 init"""
        with self.runner.isolated_filesystem():
            # 先创建配置
            Path(".skillpackrc").write_text("{}")

            # 拒绝覆盖
            result = self.runner.invoke(cli, ["init"], input="n\n")
            assert result.exit_code == 0

    def test_history_command_no_history(self):
        """测试无历史时的 history 命令"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["history"])

            assert result.exit_code == 0
            assert "没有" in result.output

    def test_version(self):
        """测试版本显示"""
        result = self.runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "5.4.2" in result.output


class TestCLIStatusWithCheckpoint:
    """CLI status 命令测试 - 有检查点场景"""

    def test_status_with_checkpoint(self):
        """测试有 checkpoint.json 时的 status 命令"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 创建 checkpoint.json
            current_dir = Path(".skillpack/current")
            current_dir.mkdir(parents=True)

            checkpoint_data = {
                "task_id": "test-123",
                "description": "测试任务",
                "status": "in_progress",
                "progress": 0.5,
                "route": "PLANNED"
            }
            (current_dir / "checkpoint.json").write_text(
                json.dumps(checkpoint_data, ensure_ascii=False)
            )

            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "测试任务" in result.output
            assert "in_progress" in result.output
            assert "50%" in result.output

    def test_status_with_invalid_checkpoint(self):
        """测试 checkpoint.json 无效时的 status 命令"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            current_dir = Path(".skillpack/current")
            current_dir.mkdir(parents=True)

            # 写入无效 JSON
            (current_dir / "checkpoint.json").write_text("{ invalid json }")

            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "无法读取" in result.output

    def test_status_current_dir_exists_no_checkpoint(self):
        """测试 current 目录存在但无 checkpoint.json"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            current_dir = Path(".skillpack/current")
            current_dir.mkdir(parents=True)

            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "没有" in result.output


class TestCLIHistoryWithEntries:
    """CLI history 命令测试 - 有历史条目场景"""

    def test_history_with_entries(self):
        """测试有历史条目时的 history 命令"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            history_dir = Path(".skillpack/history")

            # 创建多个历史条目
            for i in range(3):
                entry_dir = history_dir / f"2024-01-0{i+1}_120000"
                entry_dir.mkdir(parents=True)
                (entry_dir / "output.txt").write_text(f"Task {i}")

            result = runner.invoke(cli, ["history"])

            assert result.exit_code == 0
            assert "任务历史" in result.output
            assert "2024-01-01" in result.output

    def test_history_empty_dir(self):
        """测试历史目录为空时的 history 命令"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            history_dir = Path(".skillpack/history")
            history_dir.mkdir(parents=True)

            result = runner.invoke(cli, ["history"])

            assert result.exit_code == 0
            assert "没有" in result.output


class TestCLIListCheckpoints:
    """CLI --list-checkpoints 测试"""

    def test_list_checkpoints_with_entries(self):
        """测试有检查点时的 --list-checkpoints"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            history_dir = Path(".skillpack/history")

            # 创建带检查点的历史条目
            for i in range(3):
                entry_dir = history_dir / f"task-{i}"
                entry_dir.mkdir(parents=True)
                checkpoint_data = {
                    "task_id": f"task-{i}",
                    "task_description": f"任务描述 {i}",  # 正确的字段名
                    "route": "PLANNED",
                    "execution": {
                        "current_phase": 1,
                        "total_phases": 3,
                        "status": "running"
                    }
                }
                (entry_dir / "checkpoint.json").write_text(
                    json.dumps(checkpoint_data, ensure_ascii=False)
                )

            result = runner.invoke(cli, ["do", "--list-checkpoints"])

            assert result.exit_code == 0
            assert "可恢复的任务" in result.output
            assert "任务描述" in result.output

    def test_list_checkpoints_no_history(self):
        """测试无历史目录时的 --list-checkpoints"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["do", "--list-checkpoints"])

            assert result.exit_code == 0
            assert "没有可恢复的任务" in result.output

    def test_list_checkpoints_no_checkpoint_files(self):
        """测试历史目录存在但无 checkpoint.json"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            history_dir = Path(".skillpack/history")
            history_dir.mkdir(parents=True)
            # 创建没有 checkpoint.json 的目录
            (history_dir / "task-1").mkdir()

            result = runner.invoke(cli, ["do", "--list-checkpoints"])

            assert result.exit_code == 0
            assert "没有可恢复的任务" in result.output

    def test_list_checkpoints_invalid_json(self):
        """测试检查点文件无效 JSON"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            history_dir = Path(".skillpack/history")
            entry_dir = history_dir / "task-invalid"
            entry_dir.mkdir(parents=True)
            (entry_dir / "checkpoint.json").write_text("{ invalid }")

            result = runner.invoke(cli, ["do", "--list-checkpoints"])

            assert result.exit_code == 0
            # 无效的 JSON 会被跳过，但仍显示可恢复任务标题
            assert "可恢复的任务" in result.output


class TestCLIDoExecution:
    """CLI do 命令执行测试"""

    def test_do_execution_success(self):
        """测试任务执行成功"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 执行简单任务（非 quiet 模式）
            result = runner.invoke(cli, ["do", "fix typo"])

            assert result.exit_code == 0
            assert "任务完成" in result.output

    def test_do_no_description(self):
        """测试无任务描述时的错误"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["do"])

            assert result.exit_code == 0
            assert "需要提供任务描述" in result.output

    def test_do_resume(self):
        """测试 --resume 参数"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["do", "--resume"])

            assert result.exit_code == 0
            assert "恢复" in result.output


class TestCLIInitOverwrite:
    """CLI init 命令覆盖测试"""

    def test_init_with_yes_flag(self):
        """测试 --yes 标志跳过确认"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 先创建配置
            Path(".skillpackrc").write_text('{"version": "old"}')

            # 使用 --yes 标志
            result = runner.invoke(cli, ["init", "--yes"])

            assert result.exit_code == 0
            assert "配置文件已创建" in result.output

            # 验证内容被覆盖
            import json
            data = json.loads(Path(".skillpackrc").read_text())
            assert data["version"] == "5.4"


class TestCLIIntegration:
    """CLI 集成测试"""

    def test_full_execution_flow(self):
        """测试完整执行流程"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 初始化
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            # 执行简单任务
            result = runner.invoke(cli, ["do", "fix typo", "--quiet"])
            assert result.exit_code == 0

            # 检查状态
            result = runner.invoke(cli, ["status"])
            # 可能有历史记录了
            assert result.exit_code == 0
