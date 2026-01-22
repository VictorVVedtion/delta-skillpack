"""
测试 logging.py 日志配置模块
"""

import json
import logging
import pytest
from pathlib import Path

from skillpack.logging import (
    LogLevel,
    LoggingConfig,
    SkillpackLogger,
    JSONFormatter,
    ColoredFormatter,
    get_logger,
    configure_logging,
)


class TestLogLevel:
    """测试日志级别"""

    def test_all_levels_exist(self):
        """测试所有级别存在"""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        assert LogLevel.CRITICAL.value == "critical"

    def test_to_logging_level(self):
        """测试转换为 logging 模块级别"""
        assert LogLevel.DEBUG.to_logging_level() == logging.DEBUG
        assert LogLevel.INFO.to_logging_level() == logging.INFO
        assert LogLevel.WARNING.to_logging_level() == logging.WARNING
        assert LogLevel.ERROR.to_logging_level() == logging.ERROR
        assert LogLevel.CRITICAL.to_logging_level() == logging.CRITICAL


class TestLoggingConfig:
    """测试日志配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.console_enabled is True
        assert config.file_enabled is True
        assert config.max_size_mb == 10
        assert config.backup_count == 3

    def test_custom_config(self):
        """测试自定义配置"""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            console_enabled=False,
            file_path="/tmp/test.log",
            json_format=True,
        )
        assert config.level == LogLevel.DEBUG
        assert config.console_enabled is False
        assert config.file_path == "/tmp/test.log"
        assert config.json_format is True


class TestJSONFormatter:
    """测试 JSON 格式化器"""

    def test_format_basic_record(self):
        """测试基本记录格式化"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "timestamp" in data
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"

    def test_format_with_extra_fields(self):
        """测试带额外字段的记录"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Task log",
            args=(),
            exc_info=None,
        )
        record.task_id = "task-123"
        record.route = "DIRECT"
        record.phase = 1

        result = formatter.format(record)
        data = json.loads(result)

        assert data["task_id"] == "task-123"
        assert data["route"] == "DIRECT"
        assert data["phase"] == 1


class TestColoredFormatter:
    """测试彩色格式化器"""

    def test_format_with_colors(self):
        """测试带颜色格式化"""
        formatter = ColoredFormatter("%(levelname)s %(message)s", use_colors=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        # 应包含 ANSI 颜色代码
        assert "\033[" in result

    def test_format_without_colors(self):
        """测试无颜色格式化"""
        formatter = ColoredFormatter("%(levelname)s %(message)s", use_colors=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        # 不应包含 ANSI 颜色代码
        assert "\033[" not in result


class TestSkillpackLogger:
    """测试 Skillpack 日志管理器"""

    def test_singleton(self):
        """测试单例模式"""
        logger1 = SkillpackLogger()
        logger2 = SkillpackLogger()
        assert logger1 is logger2

    def test_configure_with_defaults(self):
        """测试使用默认配置"""
        logger = SkillpackLogger()
        logger.configure()
        assert logger._config is not None
        assert logger._config.level == LogLevel.INFO

    def test_configure_with_custom_config(self):
        """测试使用自定义配置"""
        logger = SkillpackLogger()
        config = LoggingConfig(level=LogLevel.DEBUG)
        logger.configure(config)
        assert logger._config.level == LogLevel.DEBUG

    def test_log_methods(self, caplog):
        """测试日志方法"""
        logger = get_logger()
        logger.configure(LoggingConfig(console_enabled=False, file_enabled=False))

        # 添加临时处理器以捕获日志
        logger._logger.addHandler(logging.NullHandler())

        # 调用应该不会抛出异常
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_task_log(self):
        """测试任务日志"""
        logger = get_logger()
        logger.configure(LoggingConfig(console_enabled=False, file_enabled=False))
        logger._logger.addHandler(logging.NullHandler())

        # 应该不会抛出异常
        logger.task_log(
            message="Task started",
            task_id="task-123",
            route="DIRECT",
            phase=1,
        )


class TestFileLogging:
    """测试文件日志"""

    def test_file_handler_creates_directory(self, temp_dir):
        """测试文件处理器创建目录"""
        log_path = temp_dir / "logs" / "test.log"
        config = LoggingConfig(
            console_enabled=False,
            file_enabled=True,
            file_path=str(log_path),
        )

        logger = get_logger()
        logger.configure(config)

        # 目录应该被创建
        assert log_path.parent.exists()

    def test_file_handler_writes_log(self, temp_dir):
        """测试文件处理器写入日志"""
        log_path = temp_dir / "test.log"
        config = LoggingConfig(
            console_enabled=False,
            file_enabled=True,
            file_path=str(log_path),
            level=LogLevel.DEBUG,
        )

        logger = get_logger()
        logger.configure(config)
        logger.info("Test log message")

        # 强制刷新
        for handler in logger._logger.handlers:
            handler.flush()

        # 验证日志被写入
        assert log_path.exists()
        content = log_path.read_text()
        assert "Test log message" in content


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_get_logger(self):
        """测试 get_logger"""
        logger = get_logger()
        assert isinstance(logger, SkillpackLogger)

    def test_configure_logging(self, temp_dir):
        """测试 configure_logging"""
        log_path = temp_dir / "app.log"
        logger = configure_logging(
            level="debug",
            console=False,
            file=True,
            file_path=str(log_path),
            json_format=True,
        )

        assert logger._config.level == LogLevel.DEBUG
        assert logger._config.json_format is True

    def test_configure_logging_invalid_level(self):
        """测试无效日志级别"""
        with pytest.raises(ValueError):
            configure_logging(level="invalid")
