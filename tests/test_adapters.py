"""
适配器层测试 (v6.0)
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from skillpack.adapters import (
    VersionDetector,
    CodexAdapter,
    GeminiAdapter,
    CLIVersion,
)
from skillpack.adapters.base import FeatureStatus, AdapterCommand


class TestCLIVersion:
    """CLIVersion 测试"""

    def test_version_parsing(self):
        """版本号解析测试"""
        version = CLIVersion("codex", "0.89.0")
        assert version.major == 0
        assert version.minor == 89
        assert version.patch == 0

    def test_version_comparison_ge(self):
        """版本号比较 >= 测试"""
        version = CLIVersion("codex", "0.89.0")
        assert version >= "0.80.0"
        assert version >= "0.89.0"
        assert not version >= "0.90.0"

    def test_version_comparison_lt(self):
        """版本号比较 < 测试"""
        version = CLIVersion("codex", "0.89.0")
        assert version < "0.90.0"
        assert not version < "0.89.0"
        assert not version < "0.80.0"

    def test_has_feature(self):
        """功能检查测试"""
        version = CLIVersion("codex", "0.89.0", features={
            "skills": FeatureStatus.AVAILABLE,
            "fork": FeatureStatus.UNAVAILABLE,
        })
        assert version.has_feature("skills")
        assert not version.has_feature("fork")
        assert not version.has_feature("unknown")

    def test_feature_status(self):
        """功能状态测试"""
        version = CLIVersion("codex", "0.89.0", features={
            "skills": FeatureStatus.AVAILABLE,
        })
        assert version.feature_status("skills") == FeatureStatus.AVAILABLE
        assert version.feature_status("unknown") == FeatureStatus.UNKNOWN


class TestVersionDetector:
    """VersionDetector 测试"""

    def test_parse_version_standard(self):
        """标准版本号解析"""
        detector = VersionDetector()
        assert detector._parse_version("codex 0.89.0") == "0.89.0"
        assert detector._parse_version("0.89.0") == "0.89.0"
        assert detector._parse_version("v0.89.0") == "0.89.0"
        assert detector._parse_version("version 0.89.0") == "0.89.0"

    def test_parse_version_beta(self):
        """Beta 版本号解析"""
        detector = VersionDetector()
        assert detector._parse_version("0.89.0-beta.1") == "0.89.0-beta.1"

    def test_parse_version_invalid(self):
        """无效版本号"""
        detector = VersionDetector()
        assert detector._parse_version("no version here") == "0.0.0"

    @patch('subprocess.run')
    def test_detect_codex_success(self, mock_run):
        """检测 Codex 版本成功"""
        mock_run.return_value = MagicMock(
            stdout="codex 0.89.0",
            stderr="",
            returncode=0,
        )
        detector = VersionDetector()
        version = detector.detect_codex()
        assert version.version == "0.89.0"
        assert version.cli_name == "codex"

    @patch('subprocess.run')
    def test_detect_codex_not_found(self, mock_run):
        """Codex 未安装"""
        mock_run.side_effect = FileNotFoundError()
        detector = VersionDetector()
        version = detector.detect_codex()
        assert version.version == "0.0.0"
        assert "installed" in version.features

    @patch('subprocess.run')
    def test_detect_gemini_success(self, mock_run):
        """检测 Gemini 版本成功"""
        mock_run.return_value = MagicMock(
            stdout="gemini-cli version 0.25.0",
            stderr="",
            returncode=0,
        )
        detector = VersionDetector()
        version = detector.detect_gemini()
        assert version.version == "0.25.0"
        assert version.cli_name == "gemini"

    def test_probe_features_codex(self):
        """Codex 功能探测"""
        detector = VersionDetector()
        version = CLIVersion("codex", "0.89.0")
        features = detector._probe_features(version, detector.CODEX_FEATURES)
        assert features["skills"] == FeatureStatus.AVAILABLE
        assert features["fork"] == FeatureStatus.AVAILABLE
        assert features["full-auto"] == FeatureStatus.AVAILABLE

    def test_probe_features_old_codex(self):
        """旧版 Codex 功能探测"""
        detector = VersionDetector()
        version = CLIVersion("codex", "0.80.0")
        features = detector._probe_features(version, detector.CODEX_FEATURES)
        assert features["skills"] == FeatureStatus.UNAVAILABLE
        assert features["full-auto"] == FeatureStatus.AVAILABLE

    def test_format_version_report(self):
        """版本报告格式化"""
        detector = VersionDetector()
        with patch.object(detector, 'detect_codex') as mock_codex:
            with patch.object(detector, 'detect_gemini') as mock_gemini:
                mock_codex.return_value = CLIVersion("codex", "0.89.0", {
                    "f1": FeatureStatus.AVAILABLE,
                    "f2": FeatureStatus.AVAILABLE,
                })
                mock_gemini.return_value = CLIVersion("gemini", "0.25.0", {
                    "f1": FeatureStatus.AVAILABLE,
                })
                report = detector.format_version_report()
                assert "0.89.0" in report
                assert "0.25.0" in report


class TestCodexAdapter:
    """CodexAdapter 测试"""

    def test_adapter_properties(self):
        """适配器属性测试"""
        version = CLIVersion("codex", "0.89.0", {
            "skills": FeatureStatus.AVAILABLE,
            "fork": FeatureStatus.AVAILABLE,
            "gpt-5.2-codex": FeatureStatus.AVAILABLE,
            "full-auto": FeatureStatus.AVAILABLE,
        })
        adapter = CodexAdapter(version)
        assert adapter.cli_name == "codex"
        assert adapter.min_supported_version == "0.80.0"
        assert adapter.is_supported()

    def test_build_exec_command_default(self):
        """构建默认执行命令"""
        version = CLIVersion("codex", "0.89.0", {
            "full-auto": FeatureStatus.AVAILABLE,
        })
        adapter = CodexAdapter(version)
        cmd = adapter.build_exec_command("fix bug")
        assert cmd.base_command == "codex"
        assert "exec" in cmd.args
        assert "--full-auto" in cmd.args

    def test_build_exec_command_read_only(self):
        """构建只读模式命令"""
        version = CLIVersion("codex", "0.89.0", {})
        adapter = CodexAdapter(version)
        cmd = adapter.build_exec_command("analyze code", sandbox="read-only")
        assert "-s" in cmd.args
        assert "read-only" in cmd.args

    def test_select_model_simple(self):
        """简单任务模型选择"""
        version = CLIVersion("codex", "0.89.0", {
            "gpt-5.2-codex": FeatureStatus.AVAILABLE,
        })
        adapter = CodexAdapter(version)
        model = adapter.select_model(1000, "simple", "DIRECT")
        assert model == "gpt-5.2-codex"

    def test_select_model_architect(self):
        """ARCHITECT 任务模型选择"""
        version = CLIVersion("codex", "0.89.0", {
            "gpt-5.2-codex": FeatureStatus.AVAILABLE,
        })
        adapter = CodexAdapter(version)
        model = adapter.select_model(150000, "architect", "ARCHITECT")
        assert model == "gpt-5.1-codex-max"

    def test_needs_upgrade(self):
        """升级检查"""
        old_version = CLIVersion("codex", "0.80.0", {})
        adapter = CodexAdapter(old_version)
        assert adapter.needs_upgrade()

        new_version = CLIVersion("codex", "0.89.0", {})
        adapter2 = CodexAdapter(new_version)
        assert not adapter2.needs_upgrade()


class TestGeminiAdapter:
    """GeminiAdapter 测试"""

    def test_adapter_properties(self):
        """适配器属性测试"""
        version = CLIVersion("gemini", "0.25.0", {
            "sandbox": FeatureStatus.AVAILABLE,
            "yolo": FeatureStatus.AVAILABLE,
        })
        adapter = GeminiAdapter(version)
        assert adapter.cli_name == "gemini"
        assert adapter.min_supported_version == "0.15.0"
        assert adapter.is_supported()

    def test_build_exec_command_default(self):
        """构建默认执行命令"""
        version = CLIVersion("gemini", "0.25.0", {
            "sandbox": FeatureStatus.AVAILABLE,
            "yolo": FeatureStatus.AVAILABLE,
        })
        adapter = GeminiAdapter(version)
        cmd = adapter.build_exec_command("create UI component")
        assert cmd.base_command == "gemini"
        assert "-s" in cmd.args
        assert "--yolo" in cmd.args

    def test_build_ui_command(self):
        """构建 UI 命令"""
        version = CLIVersion("gemini", "0.25.0", {
            "sandbox": FeatureStatus.AVAILABLE,
            "yolo": FeatureStatus.AVAILABLE,
            "file-context": FeatureStatus.AVAILABLE,
        })
        adapter = GeminiAdapter(version)
        cmd = adapter.build_ui_command(
            "create button component",
            context_files=["src/Button.tsx"],
        )
        assert "@src/Button.tsx" in cmd.args[0]

    def test_select_model_simple_ui(self):
        """简单 UI 模型选择"""
        version = CLIVersion("gemini", "0.25.0", {
            "gemini-3-flash": FeatureStatus.AVAILABLE,
            "gemini-3-pro": FeatureStatus.AVAILABLE,
        })
        adapter = GeminiAdapter(version)
        model = adapter.select_model(3, False)
        assert model == "gemini-3-flash"

    def test_select_model_complex_ui(self):
        """复杂 UI 模型选择"""
        version = CLIVersion("gemini", "0.25.0", {
            "gemini-3-flash": FeatureStatus.AVAILABLE,
            "gemini-3-pro": FeatureStatus.AVAILABLE,
        })
        adapter = GeminiAdapter(version)
        model = adapter.select_model(8, False)
        assert model == "gemini-3-pro"
