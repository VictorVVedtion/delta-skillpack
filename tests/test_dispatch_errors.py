"""
测试 dispatch.py 错误解析功能 (v5.4.1)
"""

import pytest

from skillpack.dispatch import (
    parse_error,
    format_error_message,
    TaskStatus,
    DispatchResult,
    ModelType,
    ExecutionMode,
)


class TestParseError:
    """测试错误解析"""

    def test_permission_error(self):
        error_type, suggestion = parse_error("operation not permitted")
        assert error_type == "PERMISSION_ERROR"
        assert suggestion is not None
        assert "sudo" in suggestion.lower() or "chown" in suggestion.lower()

    def test_permission_denied(self):
        error_type, suggestion = parse_error("Permission denied: /etc/passwd")
        assert error_type == "PERMISSION_ERROR"

    def test_command_not_found(self):
        error_type, suggestion = parse_error("codex: command not found")
        assert error_type == "COMMAND_NOT_FOUND"
        assert "PATH" in suggestion

    def test_network_error(self):
        error_type, suggestion = parse_error("connection refused to api.openai.com")
        assert error_type == "NETWORK_ERROR"

    def test_rate_limit(self):
        error_type, suggestion = parse_error("Error: rate limit exceeded")
        assert error_type == "RATE_LIMIT"
        assert "重试" in suggestion or "配额" in suggestion

    def test_auth_error(self):
        error_type, suggestion = parse_error("authentication failed: invalid token")
        assert error_type == "AUTH_ERROR"

    def test_timeout_error(self):
        error_type, suggestion = parse_error("request timed out after 30s")
        assert error_type == "TIMEOUT_ERROR"

    def test_disk_error(self):
        error_type, suggestion = parse_error("no space left on device")
        assert error_type == "DISK_ERROR"

    def test_memory_error(self):
        error_type, suggestion = parse_error("cannot allocate memory")
        assert error_type == "RESOURCE_ERROR"

    def test_unknown_error(self):
        error_type, suggestion = parse_error("some random error message")
        assert error_type == "UNKNOWN_ERROR"
        assert suggestion is None

    def test_empty_error(self):
        error_type, suggestion = parse_error("")
        assert error_type is None
        assert suggestion is None

    def test_none_error(self):
        error_type, suggestion = parse_error(None)
        assert error_type is None
        assert suggestion is None

    def test_case_insensitive(self):
        error_type, _ = parse_error("PERMISSION DENIED")
        assert error_type == "PERMISSION_ERROR"

        error_type, _ = parse_error("Connection Refused")
        assert error_type == "NETWORK_ERROR"


class TestFormatErrorMessage:
    """测试错误消息格式化"""

    def test_basic_error(self):
        msg = format_error_message("Something went wrong")
        assert "错误:" in msg
        assert "Something went wrong" in msg

    def test_error_with_type(self):
        msg = format_error_message(
            "Permission denied",
            error_type="PERMISSION_ERROR"
        )
        assert "类型:" in msg
        assert "PERMISSION_ERROR" in msg

    def test_error_with_suggestion(self):
        msg = format_error_message(
            "Command not found",
            error_type="COMMAND_NOT_FOUND",
            suggestion="安装 CLI 工具"
        )
        assert "建议:" in msg
        assert "安装 CLI 工具" in msg


class TestTaskStatus:
    """测试任务状态枚举"""

    def test_all_statuses_exist(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.TIMEOUT.value == "timeout"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestDispatchResultWithStatus:
    """测试带状态的 DispatchResult"""

    def test_success_result(self):
        result = DispatchResult(
            success=True,
            output="task completed",
            model=ModelType.CODEX,
            mode=ExecutionMode.CLI,
            status=TaskStatus.COMPLETED
        )
        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.error_type is None

    def test_failed_result_with_error_info(self):
        result = DispatchResult(
            success=False,
            output="",
            error="permission denied",
            model=ModelType.CODEX,
            mode=ExecutionMode.CLI,
            status=TaskStatus.FAILED,
            error_type="PERMISSION_ERROR",
            error_suggestion="使用 sudo"
        )
        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.error_type == "PERMISSION_ERROR"
        assert result.error_suggestion == "使用 sudo"

    def test_timeout_result(self):
        result = DispatchResult(
            success=False,
            output="partial output...",
            error="CLI timeout (600s)",
            model=ModelType.GEMINI,
            mode=ExecutionMode.CLI,
            status=TaskStatus.TIMEOUT,
            error_type="TIMEOUT_ERROR"
        )
        assert result.status == TaskStatus.TIMEOUT
        assert result.output == "partial output..."


class TestRealWorldErrors:
    """测试真实世界错误场景"""

    def test_go_build_cache_error(self):
        """Go 构建缓存权限错误"""
        error = "/Users/vvedition/Library/Caches/go-build/...: operation not permitted"
        error_type, suggestion = parse_error(error)
        assert error_type == "PERMISSION_ERROR"
        assert suggestion is not None

    def test_npm_permission_error(self):
        """NPM 全局安装权限错误"""
        error = "npm ERR! Error: EACCES: permission denied, mkdir '/usr/local/lib/node_modules'"
        error_type, suggestion = parse_error(error)
        assert error_type == "PERMISSION_ERROR"

    def test_api_rate_limit(self):
        """API 限流错误"""
        error = "openai.RateLimitError: Rate limit reached for gpt-4"
        error_type, suggestion = parse_error(error)
        assert error_type == "RATE_LIMIT"

    def test_network_timeout(self):
        """网络超时"""
        error = "requests.exceptions.ConnectTimeout: Connection to api.anthropic.com timed out"
        error_type, suggestion = parse_error(error)
        assert error_type == "TIMEOUT_ERROR"
