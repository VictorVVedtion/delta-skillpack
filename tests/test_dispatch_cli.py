"""
测试 dispatch.py CLI 调用路径 (v5.4.2)

针对 _call_codex_cli 和 _call_gemini_cli 的完整覆盖测试。
使用 subprocess mock 避免真实 CLI 调用。
"""

import json
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from skillpack.dispatch import (
    ModelDispatcher,
    ModelType,
    ExecutionMode,
    TaskStatus,
    DispatchResult,
    get_dispatcher,
)
from skillpack.models import SkillpackConfig, CLIConfig


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def dispatcher(config_factory):
    """配置为 CLI 优先模式的 ModelDispatcher"""
    config = config_factory()
    return ModelDispatcher(config)


@pytest.fixture
def mcp_dispatcher(config_factory):
    """配置为 MCP 模式的 ModelDispatcher"""
    config = config_factory()
    config.cli.prefer_cli_over_mcp = False
    return ModelDispatcher(config)


@pytest.fixture
def real_cli_dispatcher():
    """配置为真实 CLI 调用的 dispatcher（禁用 mock 模式）"""
    config = SkillpackConfig()
    dispatcher = ModelDispatcher(config)
    dispatcher._mock_mode = False  # 强制禁用 mock
    return dispatcher


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run 返回成功"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Task completed successfully"
    mock_result.stderr = ""
    return mock_result


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess.run 返回失败"""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error: command failed"
    return mock_result


# =============================================================================
# Codex CLI Tests
# =============================================================================

class TestCallCodexCli:
    """测试 _call_codex_cli 方法"""

    def test_codex_cli_success(self, real_cli_dispatcher, mock_subprocess_success):
        """测试 Codex CLI 成功执行"""
        with patch('subprocess.run', return_value=mock_subprocess_success):
            result = real_cli_dispatcher._call_codex_cli("Test prompt")

        assert result.success is True
        assert result.model == ModelType.CODEX
        assert result.mode == ExecutionMode.CLI
        assert result.status == TaskStatus.COMPLETED
        assert "Task completed successfully" in result.output

    def test_codex_cli_failure_with_error_parsing(self, real_cli_dispatcher):
        """测试 Codex CLI 失败并解析错误类型"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: permission denied"

        with patch('subprocess.run', return_value=mock_result):
            result = real_cli_dispatcher._call_codex_cli("Test prompt")

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.error_type == "PERMISSION_ERROR"
        assert result.error_suggestion is not None

    def test_codex_cli_timeout(self, real_cli_dispatcher):
        """测试 Codex CLI 超时"""
        timeout_error = subprocess.TimeoutExpired(cmd=["codex"], timeout=600)
        timeout_error.stdout = b"Partial output before timeout"

        with patch('subprocess.run', side_effect=timeout_error):
            result = real_cli_dispatcher._call_codex_cli("Long running task")

        assert result.success is False
        assert result.status == TaskStatus.TIMEOUT
        assert result.error_type == "TIMEOUT_ERROR"
        assert "超时" in result.error
        assert result.error_suggestion is not None

    def test_codex_cli_timeout_no_partial_output(self, real_cli_dispatcher):
        """测试 Codex CLI 超时无部分输出"""
        timeout_error = subprocess.TimeoutExpired(cmd=["codex"], timeout=600)
        # No stdout attribute

        with patch('subprocess.run', side_effect=timeout_error):
            result = real_cli_dispatcher._call_codex_cli("Long running task")

        assert result.success is False
        assert result.status == TaskStatus.TIMEOUT
        assert result.output == ""

    def test_codex_cli_not_found(self, real_cli_dispatcher):
        """测试 Codex CLI 未安装"""
        with patch('subprocess.run', side_effect=FileNotFoundError("codex not found")):
            result = real_cli_dispatcher._call_codex_cli("Test prompt")

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.error_type == "COMMAND_NOT_FOUND"
        assert "未找到" in result.error

    def test_codex_cli_generic_exception(self, real_cli_dispatcher):
        """测试 Codex CLI 其他异常"""
        with patch('subprocess.run', side_effect=RuntimeError("Unexpected error")):
            result = real_cli_dispatcher._call_codex_cli("Test prompt")

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert "执行失败" in result.error

    def test_codex_cli_with_context_files(self, real_cli_dispatcher, mock_subprocess_success, temp_dir):
        """测试 Codex CLI 带文件上下文"""
        # 创建测试文件
        test_file = temp_dir / "test.py"
        test_file.write_text("def hello(): pass")

        with patch('subprocess.run', return_value=mock_subprocess_success):
            result = real_cli_dispatcher._call_codex_cli(
                "Analyze this code",
                context_files=[str(test_file)]
            )

        assert result.success is True

    def test_codex_cli_custom_sandbox(self, real_cli_dispatcher, mock_subprocess_success):
        """测试 Codex CLI 自定义沙箱模式"""
        with patch('subprocess.run', return_value=mock_subprocess_success) as mock_run:
            result = real_cli_dispatcher._call_codex_cli(
                "Dangerous operation",
                sandbox="danger-full-access"
            )

        assert result.success is True
        # 检查命令中包含正确的沙箱参数
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "-s" in cmd or "danger-full-access" in cmd

    def test_codex_cli_error_in_stdout(self, real_cli_dispatcher):
        """测试错误信息在 stdout 中的情况"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Build error: rate limit exceeded for API calls"
        mock_result.stderr = "Exit code: 1"

        with patch('subprocess.run', return_value=mock_result):
            result = real_cli_dispatcher._call_codex_cli("Build project")

        assert result.success is False
        assert result.error_type == "RATE_LIMIT"


# =============================================================================
# Gemini CLI Tests
# =============================================================================

class TestCallGeminiCli:
    """测试 _call_gemini_cli 方法"""

    def test_gemini_cli_success(self, real_cli_dispatcher, mock_subprocess_success):
        """测试 Gemini CLI 成功执行"""
        with patch('subprocess.run', return_value=mock_subprocess_success):
            result = real_cli_dispatcher._call_gemini_cli("Test prompt")

        assert result.success is True
        assert result.model == ModelType.GEMINI
        assert result.mode == ExecutionMode.CLI
        assert result.status == TaskStatus.COMPLETED

    def test_gemini_cli_failure(self, real_cli_dispatcher):
        """测试 Gemini CLI 失败"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "authentication failed"

        with patch('subprocess.run', return_value=mock_result):
            result = real_cli_dispatcher._call_gemini_cli("Test prompt")

        assert result.success is False
        assert result.error_type == "AUTH_ERROR"

    def test_gemini_cli_timeout(self, real_cli_dispatcher):
        """测试 Gemini CLI 超时"""
        timeout_error = subprocess.TimeoutExpired(cmd=["gemini"], timeout=600)
        timeout_error.stdout = "Partial"

        with patch('subprocess.run', side_effect=timeout_error):
            result = real_cli_dispatcher._call_gemini_cli("Long task")

        assert result.status == TaskStatus.TIMEOUT
        assert result.error_type == "TIMEOUT_ERROR"

    def test_gemini_cli_not_found(self, real_cli_dispatcher):
        """测试 Gemini CLI 未安装"""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = real_cli_dispatcher._call_gemini_cli("Test")

        assert result.error_type == "COMMAND_NOT_FOUND"
        assert "gemini-cli" in result.error_suggestion.lower()

    def test_gemini_cli_generic_exception(self, real_cli_dispatcher):
        """测试 Gemini CLI 其他异常"""
        with patch('subprocess.run', side_effect=OSError("System error")):
            result = real_cli_dispatcher._call_gemini_cli("Test")

        assert result.success is False
        assert result.status == TaskStatus.FAILED

    def test_gemini_cli_with_context_files(self, real_cli_dispatcher, mock_subprocess_success):
        """测试 Gemini CLI 使用 @ 语法注入文件"""
        with patch('subprocess.run', return_value=mock_subprocess_success) as mock_run:
            result = real_cli_dispatcher._call_gemini_cli(
                "Review code",
                context_files=["src/main.py", "src/utils.py"]
            )

        assert result.success is True

    def test_gemini_cli_no_sandbox(self, real_cli_dispatcher, mock_subprocess_success):
        """测试 Gemini CLI 禁用沙箱"""
        with patch('subprocess.run', return_value=mock_subprocess_success) as mock_run:
            result = real_cli_dispatcher._call_gemini_cli("Test", sandbox=False)

        assert result.success is True
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "-s" not in cmd


# =============================================================================
# MCP Mode Tests
# =============================================================================

class TestMCPMode:
    """测试 MCP 调用模式"""

    def test_codex_mcp_returns_params(self, mcp_dispatcher):
        """测试 Codex MCP 模式返回正确参数"""
        # 禁用 mock 模式以测试 MCP 路径
        mcp_dispatcher._mock_mode = False

        result = mcp_dispatcher.call_codex("Test prompt")

        assert result.success is True
        assert result.mode == ExecutionMode.MCP
        assert "mcp__codex-cli__codex" in result.output

        # 验证 JSON 结构
        params = json.loads(result.output)
        assert params["tool"] == "mcp__codex-cli__codex"
        assert "prompt" in params["params"]

    def test_gemini_mcp_returns_params(self, mcp_dispatcher):
        """测试 Gemini MCP 模式返回正确参数"""
        mcp_dispatcher._mock_mode = False

        result = mcp_dispatcher.call_gemini("Test prompt")

        assert result.success is True
        assert result.mode == ExecutionMode.MCP

        params = json.loads(result.output)
        assert params["tool"] == "mcp__gemini-cli__ask-gemini"

    def test_codex_mcp_with_context(self, mcp_dispatcher, temp_dir):
        """测试 Codex MCP 带文件上下文"""
        mcp_dispatcher._mock_mode = False

        test_file = temp_dir / "code.py"
        test_file.write_text("print('hello')")

        result = mcp_dispatcher.call_codex(
            "Review code",
            context_files=[str(test_file)]
        )

        assert result.success is True
        params = json.loads(result.output)
        assert "相关文件" in params["params"]["prompt"]


# =============================================================================
# Progress Callback Tests
# =============================================================================

class TestProgressCallbacks:
    """测试进度回调功能"""

    def test_progress_callback_invoked(self, real_cli_dispatcher, mock_subprocess_success):
        """测试进度回调被正确调用"""
        progress_calls = []

        def callback(message: str, progress: float):
            progress_calls.append((message, progress))

        real_cli_dispatcher.set_progress_callback(callback)

        with patch('subprocess.run', return_value=mock_subprocess_success):
            real_cli_dispatcher._call_codex_cli("Test")

        # 应该有多次进度回调
        assert len(progress_calls) >= 2
        # 检查完成回调
        assert any("完成" in msg for msg, _ in progress_calls)

    def test_progress_callback_on_gemini(self, real_cli_dispatcher, mock_subprocess_success):
        """测试 Gemini 进度回调"""
        progress_calls = []

        real_cli_dispatcher.set_progress_callback(lambda m, p: progress_calls.append((m, p)))

        with patch('subprocess.run', return_value=mock_subprocess_success):
            real_cli_dispatcher._call_gemini_cli("Test")

        assert len(progress_calls) >= 2


# =============================================================================
# Context Building Tests
# =============================================================================

class TestContextBuilding:
    """测试上下文构建"""

    def test_build_prompt_with_context(self, real_cli_dispatcher, temp_dir):
        """测试构建带文件内容的 prompt"""
        # 创建测试文件
        test_file = temp_dir / "example.py"
        test_file.write_text("def foo():\n    return 42")

        result = real_cli_dispatcher._build_prompt_with_context(
            "Analyze function",
            context_files=[str(test_file)]
        )

        assert "Analyze function" in result
        assert "相关文件" in result
        assert "def foo():" in result

    def test_build_prompt_truncates_large_files(self, real_cli_dispatcher, temp_dir):
        """测试大文件截断"""
        # 创建超过限制行数的文件
        large_file = temp_dir / "large.py"
        lines = [f"line {i}" for i in range(1000)]
        large_file.write_text("\n".join(lines))

        result = real_cli_dispatcher._build_prompt_with_context(
            "Analyze",
            context_files=[str(large_file)]
        )

        assert "truncated" in result

    def test_build_prompt_handles_missing_files(self, real_cli_dispatcher):
        """测试处理不存在的文件"""
        result = real_cli_dispatcher._build_prompt_with_context(
            "Analyze",
            context_files=["/nonexistent/file.py"]
        )

        # 应该返回原始 prompt，不崩溃
        assert result == "Analyze"

    def test_build_prompt_respects_max_files(self, real_cli_dispatcher, temp_dir):
        """测试限制最大文件数"""
        # 创建超过限制数量的文件
        files = []
        for i in range(20):
            f = temp_dir / f"file_{i}.py"
            f.write_text(f"# File {i}")
            files.append(str(f))

        result = real_cli_dispatcher._build_prompt_with_context("Analyze", context_files=files)

        # 只应包含 max_context_files 数量的文件
        count = result.count("###")
        assert count <= real_cli_dispatcher.config.cli.max_context_files

    def test_build_gemini_prompt(self, real_cli_dispatcher):
        """测试 Gemini @ 语法构建"""
        result = real_cli_dispatcher._build_gemini_prompt(
            "Review code",
            context_files=["src/a.py", "src/b.py"]
        )

        assert "@src/a.py" in result
        assert "@src/b.py" in result
        assert "Review code" in result

    def test_build_gemini_prompt_no_files(self, real_cli_dispatcher):
        """测试 Gemini 无文件时"""
        result = real_cli_dispatcher._build_gemini_prompt("Just text", context_files=None)
        assert result == "Just text"

    def test_build_prompt_auto_context_disabled(self, config_factory):
        """测试禁用自动上下文"""
        config = config_factory()
        config.cli.auto_context = False
        dispatcher = ModelDispatcher(config)
        dispatcher._mock_mode = False

        result = dispatcher._build_prompt_with_context(
            "Test",
            context_files=["some/file.py"]
        )

        assert result == "Test"


# =============================================================================
# Execution Log Tests
# =============================================================================

class TestExecutionLogging:
    """测试执行日志记录"""

    def test_log_execution_records_success(self, real_cli_dispatcher, mock_subprocess_success, temp_dir):
        """测试成功执行被记录"""
        # 设置临时用量存储
        real_cli_dispatcher._usage_store.path = temp_dir / "usage.jsonl"
        real_cli_dispatcher.set_context("task-1", "DIRECT", 1, "Phase 1")

        with patch('subprocess.run', return_value=mock_subprocess_success):
            real_cli_dispatcher._call_codex_cli("Test")

        log = real_cli_dispatcher.get_execution_log()
        assert len(log) == 1
        assert log[0]["success"] is True
        assert log[0]["model"] == "codex"

    def test_log_execution_records_failure(self, real_cli_dispatcher, mock_subprocess_failure, temp_dir):
        """测试失败执行被记录"""
        real_cli_dispatcher._usage_store.path = temp_dir / "usage.jsonl"

        with patch('subprocess.run', return_value=mock_subprocess_failure):
            real_cli_dispatcher._call_codex_cli("Test")

        log = real_cli_dispatcher.get_execution_log()
        assert len(log) == 1
        assert log[0]["success"] is False


# =============================================================================
# Formatting Tests
# =============================================================================

class TestFormatting:
    """测试格式化输出"""

    def test_format_phase_header(self, dispatcher):
        """测试阶段头部格式化"""
        header = dispatcher.format_phase_header(
            phase=1,
            total_phases=3,
            phase_name="Code Generation",
            route="RALPH",
            model=ModelType.CODEX,
            progress_percent=50
        )

        assert "Phase 1/3" in header
        assert "Code Generation" in header
        assert "RALPH" in header
        assert "Codex" in header
        assert "50%" in header

    def test_format_phase_header_claude(self, dispatcher):
        """测试 Claude 模型阶段头部"""
        header = dispatcher.format_phase_header(
            phase=1,
            total_phases=1,
            phase_name="Direct Execute",
            route="DIRECT",
            model=ModelType.CLAUDE,
            progress_percent=100
        )

        assert "直接执行" in header

    def test_format_phase_complete(self, dispatcher):
        """测试阶段完成格式化"""
        output = dispatcher.format_phase_complete(
            phase=1,
            model=ModelType.CODEX,
            duration_ms=5000,
            output_file="output.txt"
        )

        assert "Phase 1 完成" in output
        assert "5.0s" in output
        assert "output.txt" in output

    def test_format_phase_complete_degraded(self, dispatcher):
        """测试降级执行格式化"""
        output = dispatcher.format_phase_complete(
            phase=2,
            model=ModelType.CODEX,
            duration_ms=3000,
            output_file="output.txt",
            degraded=True,
            original_model=ModelType.GEMINI
        )

        assert "降级执行" in output
        assert "Gemini" in output
        assert "Codex" in output

    def test_build_progress_bar(self, dispatcher):
        """测试进度条构建"""
        bar_0 = dispatcher._build_progress_bar(0)
        bar_50 = dispatcher._build_progress_bar(50)
        bar_100 = dispatcher._build_progress_bar(100)

        assert "░" * 20 in bar_0
        assert "█" * 10 in bar_50
        assert "█" * 20 in bar_100


# =============================================================================
# Knowledge Base Tests
# =============================================================================

class TestKnowledgeBase:
    """测试知识库查询"""

    def test_query_knowledge_base_no_notebook(self, dispatcher):
        """测试无 notebook ID"""
        result = dispatcher.query_knowledge_base("", "query")
        assert result is None

    def test_format_knowledge_query_prompt(self, dispatcher):
        """测试知识库查询 prompt 格式化"""
        prompt = dispatcher.format_knowledge_query_prompt(
            task_description="实现用户认证功能",
            phase_name="Code Review"
        )

        assert "实现用户认证功能" in prompt
        assert "Code Review" in prompt
        assert "验收标准" in prompt


# =============================================================================
# get_dispatcher Helper Tests
# =============================================================================

class TestGetDispatcher:
    """测试便捷函数"""

    def test_get_dispatcher_returns_instance(self, config_factory):
        """测试 get_dispatcher 返回正确实例"""
        config = config_factory()
        dispatcher = get_dispatcher(config)

        assert isinstance(dispatcher, ModelDispatcher)
        assert dispatcher.config == config
