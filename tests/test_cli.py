"""
测试 CLI 命令
"""

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
        assert "Ralph" in result.output

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
        assert "1.0.0" in result.output


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
