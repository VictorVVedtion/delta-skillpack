"""Structured logging with Rich integration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from rich.console import Console
from rich.logging import RichHandler

LogLevel = Literal["debug", "info", "warning", "error"]

# Module-level logger
_logger: logging.Logger | None = None
_console: Console | None = None


def get_console() -> Console:
    """Get or create the shared Rich console."""
    global _console
    if _console is None:
        _console = Console(stderr=True)
    return _console


def get_logger() -> logging.Logger:
    """Get the skillpack logger (creates if needed)."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger("skillpack")
        _logger.setLevel(logging.DEBUG)
        # Prevent duplicate handlers
        if not _logger.handlers:
            _logger.addHandler(logging.NullHandler())
    return _logger


def setup_logging(
    level: LogLevel = "info",
    log_file: Path | None = None,
    rich_tracebacks: bool = True,
) -> logging.Logger:
    """Configure logging with Rich handler.

    Args:
        level: Log level (debug, info, warning, error)
        log_file: Optional file path to write logs
        rich_tracebacks: Enable Rich traceback formatting

    Returns:
        Configured logger instance
    """
    logger = get_logger()
    console = get_console()

    # Clear existing handlers
    logger.handlers.clear()

    # Map string level to logging constant
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    log_level = level_map.get(level, logging.INFO)
    logger.setLevel(log_level)

    # Rich console handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=rich_tracebacks,
        tracebacks_show_locals=level == "debug",
        markup=True,
    )
    rich_handler.setLevel(log_level)
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)

    # Optional file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always capture all levels to file
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger


class SkillLogger:
    """Structured logger with context support."""

    def __init__(self, name: str = "skillpack"):
        self._logger = logging.getLogger(name)
        self._context: dict[str, Any] = {}

    def bind(self, **kwargs: Any) -> SkillLogger:
        """Create a new logger with additional context."""
        new_logger = SkillLogger(self._logger.name)
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def _format_message(self, msg: str) -> str:
        """Format message with context."""
        if not self._context:
            return msg
        ctx_str = " ".join(f"[dim]{k}={v}[/dim]" for k, v in self._context.items())
        return f"{msg} {ctx_str}"

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._context.update(kwargs)
        self._logger.debug(self._format_message(msg), extra={"markup": True})

    def info(self, msg: str, **kwargs: Any) -> None:
        self._context.update(kwargs)
        self._logger.info(self._format_message(msg), extra={"markup": True})

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._context.update(kwargs)
        self._logger.warning(self._format_message(msg), extra={"markup": True})

    def error(self, msg: str, **kwargs: Any) -> None:
        self._context.update(kwargs)
        self._logger.error(self._format_message(msg), extra={"markup": True})

    def exception(self, msg: str, **kwargs: Any) -> None:
        self._context.update(kwargs)
        self._logger.exception(self._format_message(msg), extra={"markup": True})

    # Convenience methods for skill execution logging
    def skill_start(self, skill: str, run_id: str, variants: int) -> None:
        self.info(
            f"[bold cyan]Starting[/] skill=[green]{skill}[/] "
            f"run_id=[yellow]{run_id}[/] variants={variants}"
        )

    def skill_complete(
        self, skill: str, run_id: str, success: int, failed: int, duration_ms: int
    ) -> None:
        status = "[green]SUCCESS[/]" if failed == 0 else f"[yellow]PARTIAL[/] ({failed} failed)"
        self.info(
            f"[bold]Completed[/] skill=[green]{skill}[/] "
            f"run_id=[yellow]{run_id}[/] {status} duration={duration_ms}ms"
        )

    def variant_start(self, variant: int) -> None:
        self.debug(f"Executing variant {variant}")

    def variant_complete(self, variant: int, success: bool, duration_ms: int) -> None:
        status = "[green]OK[/]" if success else "[red]FAIL[/]"
        self.debug(f"Variant {variant} {status} ({duration_ms}ms)")

    def git_checkpoint(self, branch: str, stashed: bool) -> None:
        stash_info = " (stashed)" if stashed else ""
        self.debug(f"Git checkpoint: branch=[cyan]{branch}[/]{stash_info}")

    def engine_execute(self, engine: str, timeout: int) -> None:
        self.debug(f"Engine [bold]{engine}[/] executing (timeout={timeout}s)")

    def pipeline_step(self, step: int, total: int, skill: str) -> None:
        self.info(f"[bold]Pipeline[/] [{step}/{total}] → [cyan]{skill}[/]")


# Global logger instance
log = SkillLogger()


def init_logging(level: LogLevel = "info", log_file: Path | None = None) -> SkillLogger:
    """Initialize logging and return the global logger.

    This should be called once at application startup.
    """
    setup_logging(level=level, log_file=log_file)
    return log
