"""
日志配置模块

提供可配置的日志系统，支持：
- 控制台和文件输出
- 日志级别配置
- 日志轮转
- 结构化 JSON 日志
"""

import logging
import logging.handlers
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    def to_logging_level(self) -> int:
        """转换为 logging 模块的级别"""
        mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        return mapping.get(self.value, logging.INFO)


@dataclass
class LoggingConfig:
    """日志配置"""
    level: LogLevel = LogLevel.INFO
    console_enabled: bool = True
    file_enabled: bool = True
    file_path: str = ".skillpack/skillpack.log"
    max_size_mb: int = 10
    backup_count: int = 3
    json_format: bool = False
    include_timestamp: bool = True
    include_module: bool = True


class JSONFormatter(logging.Formatter):
    """JSON 格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        if record.module:
            log_record["module"] = record.module

        if record.funcName:
            log_record["function"] = record.funcName

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "task_id"):
            log_record["task_id"] = record.task_id
        if hasattr(record, "route"):
            log_record["route"] = record.route
        if hasattr(record, "phase"):
            log_record["phase"] = record.phase

        return json.dumps(log_record, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器"""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, fmt: Optional[str] = None, use_colors: bool = True):
        super().__init__(fmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            color = self.COLORS.get(record.levelno, self.RESET)
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class SkillpackLogger:
    """Skillpack 日志管理器"""

    _instance: Optional["SkillpackLogger"] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> "SkillpackLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._logger = logging.getLogger("skillpack")
            self._config: Optional[LoggingConfig] = None

    def configure(self, config: Optional[LoggingConfig] = None) -> None:
        """
        配置日志系统。

        Args:
            config: 日志配置，None 时使用默认配置
        """
        self._config = config or LoggingConfig()

        # 清除现有处理器
        self._logger.handlers.clear()
        self._logger.setLevel(self._config.level.to_logging_level())

        # 添加控制台处理器
        if self._config.console_enabled:
            self._add_console_handler()

        # 添加文件处理器
        if self._config.file_enabled:
            self._add_file_handler()

    def _add_console_handler(self) -> None:
        """添加控制台处理器"""
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(self._config.level.to_logging_level())

        if self._config.json_format:
            handler.setFormatter(JSONFormatter())
        else:
            fmt_parts = []
            if self._config.include_timestamp:
                fmt_parts.append("%(asctime)s")
            fmt_parts.append("%(levelname)s")
            if self._config.include_module:
                fmt_parts.append("[%(module)s]")
            fmt_parts.append("%(message)s")

            fmt = " ".join(fmt_parts)
            handler.setFormatter(ColoredFormatter(fmt))

        self._logger.addHandler(handler)

    def _add_file_handler(self) -> None:
        """添加文件处理器（带轮转）"""
        log_path = Path(self._config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=self._config.max_size_mb * 1024 * 1024,
            backupCount=self._config.backup_count,
            encoding="utf-8",
        )
        handler.setLevel(self._config.level.to_logging_level())

        if self._config.json_format:
            handler.setFormatter(JSONFormatter())
        else:
            fmt = "%(asctime)s %(levelname)s [%(module)s] %(message)s"
            handler.setFormatter(logging.Formatter(fmt))

        self._logger.addHandler(handler)

    @property
    def logger(self) -> logging.Logger:
        """获取 logger 实例"""
        if self._config is None:
            self.configure()
        return self._logger

    def debug(self, message: str, **kwargs) -> None:
        """Debug 日志"""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Info 日志"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Warning 日志"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Error 日志"""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Critical 日志"""
        self.logger.critical(message, extra=kwargs)

    def task_log(
        self,
        message: str,
        task_id: str,
        route: Optional[str] = None,
        phase: Optional[int] = None,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """
        任务相关日志。

        Args:
            message: 日志消息
            task_id: 任务 ID
            route: 执行路由
            phase: 当前阶段
            level: 日志级别
        """
        extra = {"task_id": task_id}
        if route:
            extra["route"] = route
        if phase is not None:
            extra["phase"] = phase

        self.logger.log(level.to_logging_level(), message, extra=extra)


def get_logger() -> SkillpackLogger:
    """获取 Skillpack 日志管理器实例"""
    return SkillpackLogger()


def configure_logging(
    level: str = "info",
    console: bool = True,
    file: bool = True,
    file_path: str = ".skillpack/skillpack.log",
    json_format: bool = False,
) -> SkillpackLogger:
    """
    配置日志系统的便捷函数。

    Args:
        level: 日志级别 (debug, info, warning, error, critical)
        console: 是否输出到控制台
        file: 是否输出到文件
        file_path: 日志文件路径
        json_format: 是否使用 JSON 格式

    Returns:
        配置好的 logger 实例
    """
    config = LoggingConfig(
        level=LogLevel(level.lower()),
        console_enabled=console,
        file_enabled=file,
        file_path=file_path,
        json_format=json_format,
    )

    logger = get_logger()
    logger.configure(config)
    return logger
