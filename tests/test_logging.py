"""Unit tests for skillpack.logging module."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

from skillpack.logging import (
    SkillLogger,
    get_console,
    get_logger,
    init_logging,
    log,
    setup_logging,
)


class TestGetConsole:
    """Tests for get_console function."""

    def test_returns_console(self):
        console = get_console()
        assert console is not None

    def test_returns_same_instance(self):
        c1 = get_console()
        c2 = get_console()
        assert c1 is c2


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self):
        logger = get_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "skillpack"

    def test_returns_same_instance(self):
        l1 = get_logger()
        l2 = get_logger()
        assert l1 is l2


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_sets_log_level(self):
        logger = setup_logging(level="debug")
        assert logger.level == logging.DEBUG

        logger = setup_logging(level="warning")
        assert logger.level == logging.WARNING

    def test_creates_file_handler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging(level="info", log_file=log_file)

            # Write a log message
            logger.info("Test message")

            # File should be created
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content

    def test_clears_existing_handlers(self):
        logger = setup_logging(level="info")
        initial_handlers = len(logger.handlers)

        # Setup again
        logger = setup_logging(level="debug")

        # Should not accumulate handlers
        assert len(logger.handlers) == initial_handlers


class TestSkillLogger:
    """Tests for SkillLogger class."""

    def test_bind_creates_new_logger(self):
        logger = SkillLogger()
        bound = logger.bind(skill="plan", run_id="123")

        assert bound is not logger
        assert bound._context["skill"] == "plan"
        assert bound._context["run_id"] == "123"

    def test_bind_preserves_parent_context(self):
        logger = SkillLogger()
        bound1 = logger.bind(skill="plan")
        bound2 = bound1.bind(run_id="123")

        assert bound2._context["skill"] == "plan"
        assert bound2._context["run_id"] == "123"

    def test_format_message_without_context(self):
        logger = SkillLogger()
        msg = logger._format_message("Test message")
        assert msg == "Test message"

    def test_format_message_with_context(self):
        logger = SkillLogger()
        bound = logger.bind(skill="plan")
        msg = bound._format_message("Test message")
        assert "skill=plan" in msg
        assert "Test message" in msg

    def test_log_methods_exist(self):
        logger = SkillLogger()
        assert callable(logger.debug)
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)
        assert callable(logger.exception)

    def test_skill_start_formats_correctly(self):
        logger = SkillLogger()
        # Just verify it doesn't raise
        with patch.object(logger, "info") as mock_info:
            logger.skill_start("plan", "run_123", 5)
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "plan" in call_args
            assert "run_123" in call_args
            assert "5" in call_args

    def test_skill_complete_formats_correctly(self):
        logger = SkillLogger()
        with patch.object(logger, "info") as mock_info:
            logger.skill_complete("plan", "run_123", 4, 1, 5000)
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "plan" in call_args
            assert "5000" in call_args

    def test_git_checkpoint_formats_correctly(self):
        logger = SkillLogger()
        with patch.object(logger, "debug") as mock_debug:
            logger.git_checkpoint("skill/plan/123", True)
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args[0][0]
            assert "skill/plan/123" in call_args
            assert "stashed" in call_args

    def test_pipeline_step_formats_correctly(self):
        logger = SkillLogger()
        with patch.object(logger, "info") as mock_info:
            logger.pipeline_step(2, 3, "implement")
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "2/3" in call_args
            assert "implement" in call_args


class TestGlobalLog:
    """Tests for global log instance."""

    def test_log_is_skill_logger(self):
        assert isinstance(log, SkillLogger)

    def test_init_logging_returns_logger(self):
        result = init_logging(level="info")
        assert isinstance(result, SkillLogger)


class TestLoggingIntegration:
    """Integration tests for logging in context."""

    def test_log_to_file_integration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "skill.log"
            init_logging(level="debug", log_file=log_file)

            # Use the global logger
            log.info("Integration test message")
            log.skill_start("test", "run_001", 3)

            # Verify file contents
            content = log_file.read_text()
            assert "Integration test message" in content

    def test_quiet_mode_respects_level(self):
        # When quiet, effective level should be warning
        logger = setup_logging(level="warning")
        assert logger.level == logging.WARNING
