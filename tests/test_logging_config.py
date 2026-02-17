"""Test suite for logging_config module.

This module tests the centralized logging configuration functionality,
including log level parsing, file path handling, and logging setup.
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from logging_config import (
    ensure_log_directory,
    get_log_file_path,
    get_log_level,
    get_logger,
    setup_logging,
)


class TestGetLogLevel:
    """Tests for get_log_level function."""

    def test_default_log_level_is_info(self):
        """Test that default log level is INFO when env var not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            level = get_log_level()
            assert level == logging.INFO

    def test_debug_level_from_env(self):
        """Test that DEBUG level is returned when LOG_LEVEL=DEBUG."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            level = get_log_level()
            assert level == logging.DEBUG

    def test_warning_level_from_env(self):
        """Test that WARNING level is returned when LOG_LEVEL=WARNING."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            level = get_log_level()
            assert level == logging.WARNING

    def test_error_level_from_env(self):
        """Test that ERROR level is returned when LOG_LEVEL=ERROR."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            level = get_log_level()
            assert level == logging.ERROR

    def test_critical_level_from_env(self):
        """Test that CRITICAL level is returned when LOG_LEVEL=CRITICAL."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "CRITICAL"}):
            level = get_log_level()
            assert level == logging.CRITICAL

    def test_invalid_level_defaults_to_info(self):
        """Test that invalid log level defaults to INFO."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            level = get_log_level()
            assert level == logging.INFO

    def test_case_insensitive_level(self):
        """Test that log level is case insensitive."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            level = get_log_level()
            assert level == logging.DEBUG


class TestGetLogFilePath:
    """Tests for get_log_file_path function."""

    def test_default_log_file_path(self):
        """Test default log file path when env var not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            path = get_log_file_path()
            assert path == "logs/app.log"

    def test_custom_log_file_path(self):
        """Test custom log file path from env var."""
        with mock.patch.dict(os.environ, {"LOG_FILE": "/var/log/myapp.log"}):
            path = get_log_file_path()
            assert path == "/var/log/myapp.log"

    def test_none_disables_file_logging(self):
        """Test that LOG_FILE=none disables file logging."""
        with mock.patch.dict(os.environ, {"LOG_FILE": "none"}):
            path = get_log_file_path()
            assert path is None

    def test_null_disables_file_logging(self):
        """Test that LOG_FILE=null disables file logging."""
        with mock.patch.dict(os.environ, {"LOG_FILE": "null"}):
            path = get_log_file_path()
            assert path is None

    def test_disabled_disables_file_logging(self):
        """Test that LOG_FILE=disabled disables file logging."""
        with mock.patch.dict(os.environ, {"LOG_FILE": "disabled"}):
            path = get_log_file_path()
            assert path is None

    def test_empty_string_disables_file_logging(self):
        """Test that empty LOG_FILE disables file logging."""
        with mock.patch.dict(os.environ, {"LOG_FILE": ""}):
            path = get_log_file_path()
            assert path is None

    def test_case_insensitive_disable(self):
        """Test that disable values are case insensitive."""
        with mock.patch.dict(os.environ, {"LOG_FILE": "NONE"}):
            path = get_log_file_path()
            assert path is None


class TestEnsureLogDirectory:
    """Tests for ensure_log_directory function."""

    def test_creates_directory_if_not_exists(self, tmp_path):
        """Test that directory is created if it doesn't exist."""
        log_dir = tmp_path / "new_logs"
        log_file = log_dir / "app.log"

        assert not log_dir.exists()
        ensure_log_directory(str(log_file))
        assert log_dir.exists()

    def test_does_not_fail_if_directory_exists(self, tmp_path):
        """Test that function doesn't fail if directory already exists."""
        log_dir = tmp_path / "existing_logs"
        log_dir.mkdir()
        log_file = log_dir / "app.log"

        ensure_log_directory(str(log_file))  # Should not raise

    def test_creates_nested_directories(self, tmp_path):
        """Test that nested directories are created."""
        log_dir = tmp_path / "a" / "b" / "c"
        log_file = log_dir / "app.log"

        ensure_log_directory(str(log_file))
        assert log_dir.exists()

    def test_handles_file_without_directory(self, tmp_path):
        """Test handling of file path without parent directory."""
        log_file = tmp_path / "app.log"

        # Should not raise even though parent is tmp_path (which exists)
        ensure_log_directory(str(log_file))


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_returns_root_logger(self):
        """Test that setup_logging returns the root logger."""
        logger = setup_logging(log_level=logging.INFO, log_file=None)
        assert logger.name == "root"

    def test_configures_log_level(self):
        """Test that log level is properly configured."""
        logger = setup_logging(log_level=logging.DEBUG, log_file=None)
        assert logger.level == logging.DEBUG

    def test_creates_console_handler(self):
        """Test that console handler is created."""
        logger = setup_logging(log_level=logging.INFO, log_file=None)
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(console_handlers) == 1

    def test_creates_file_handler_when_log_file_provided(self, tmp_path):
        """Test that file handler is created when log file path provided."""
        log_file = tmp_path / "test.log"
        logger = setup_logging(log_level=logging.INFO, log_file=str(log_file))

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert file_handlers[0].baseFilename == str(log_file)

    def test_no_file_handler_when_log_file_none(self):
        """Test that no file handler is created when log_file is None."""
        # Mock environment to ensure no default log file is used
        with mock.patch.dict(os.environ, {"LOG_FILE": "none"}, clear=True):
            logger = setup_logging(log_level=logging.INFO, log_file=None)

            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
            assert len(file_handlers) == 0

    def test_clears_existing_handlers(self):
        """Test that existing handlers are cleared to avoid duplicates."""
        # Setup logging twice
        logger1 = setup_logging(log_level=logging.INFO, log_file=None)
        initial_handler_count = len(logger1.handlers)

        logger2 = setup_logging(log_level=logging.DEBUG, log_file=None)
        final_handler_count = len(logger2.handlers)

        # Should have same number of handlers (not doubled)
        assert final_handler_count == initial_handler_count

    def test_formatter_is_configured(self):
        """Test that formatter is properly configured on handlers."""
        logger = setup_logging(log_level=logging.INFO, log_file=None)

        for handler in logger.handlers:
            assert handler.formatter is not None

    def test_custom_log_format(self):
        """Test that custom log format is applied."""
        custom_format = "%(levelname)s - %(message)s"
        logger = setup_logging(
            log_level=logging.INFO,
            log_file=None,
            log_format=custom_format
        )

        for handler in logger.handlers:
            assert handler.formatter._fmt == custom_format

    def test_custom_date_format(self):
        """Test that custom date format is applied."""
        custom_date_format = "%d/%m/%Y"
        logger = setup_logging(
            log_level=logging.INFO,
            log_file=None,
            date_format=custom_date_format
        )

        for handler in logger.handlers:
            assert handler.formatter.datefmt == custom_date_format

    def test_rotating_file_handler_configuration(self, tmp_path):
        """Test rotating file handler configuration."""
        log_file = tmp_path / "test.log"
        max_bytes = 1024 * 1024  # 1MB
        backup_count = 3

        logger = setup_logging(
            log_level=logging.INFO,
            log_file=str(log_file),
            max_bytes=max_bytes,
            backup_count=backup_count
        )

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1

        handler = file_handlers[0]
        assert handler.maxBytes == max_bytes
        assert handler.backupCount == backup_count

    def test_handles_file_handler_error_gracefully(self, tmp_path):
        """Test that file handler errors are handled gracefully."""
        # Create a path that can't be written to (simulated by mocking)
        with mock.patch('logging_config.ensure_log_directory', side_effect=PermissionError("Access denied")):
            # Should not raise, should log error to console
            logger = setup_logging(log_level=logging.INFO, log_file="/some/path")
            assert logger is not None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_with_given_name(self):
        """Test that get_logger returns a logger with the specified name."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"

    def test_returns_same_logger_for_same_name(self):
        """Test that get_logger returns the same logger instance for the same name."""
        logger1 = get_logger("my_module")
        logger2 = get_logger("my_module")
        assert logger1 is logger2

    def test_returns_different_loggers_for_different_names(self):
        """Test that get_logger returns different loggers for different names."""
        logger1 = get_logger("module_a")
        logger2 = get_logger("module_b")
        assert logger1 is not logger2

    def test_returns_child_of_root_logger(self):
        """Test that returned logger is a child of the root logger."""
        logger = get_logger("child.module")
        assert logger.parent is logging.getLogger()


class TestIntegration:
    """Integration tests for logging_config module."""

    def test_full_logging_setup_with_env_vars(self, tmp_path, caplog):
        """Test full logging setup using environment variables."""
        log_file = tmp_path / "integration.log"

        env_vars = {
            "LOG_LEVEL": "DEBUG",
            "LOG_FILE": str(log_file)
        }

        with mock.patch.dict(os.environ, env_vars):
            with caplog.at_level(logging.DEBUG):
                logger = setup_logging()
                logger.info("Integration test message")

        # Verify log file was created and contains message
        assert log_file.exists()
        content = log_file.read_text()
        assert "Integration test message" in content

    def test_logging_output_format(self, tmp_path):
        """Test that log output follows expected format."""
        log_file = tmp_path / "format_test.log"

        logger = setup_logging(
            log_level=logging.INFO,
            log_file=str(log_file),
            log_format="%(levelname)s | %(message)s"
        )

        logger.warning("Test warning")

        # Verify format in output
        content = log_file.read_text()
        assert "WARNING | Test warning" in content

    def test_multiple_log_levels(self, tmp_path):
        """Test that different log levels work correctly."""
        log_file = tmp_path / "levels.log"

        logger = setup_logging(log_level=logging.WARNING, log_file=str(log_file))

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        content = log_file.read_text()

        # Debug and info should not be present
        assert "Debug message" not in content
        assert "Info message" not in content

        # Warning and error should be present
        assert "Warning message" in content
        assert "Error message" in content

    def test_module_logger_integration(self, tmp_path):
        """Test module logger works with configured root logger."""
        log_file = tmp_path / "module.log"

        # Setup root logger
        setup_logging(log_level=logging.INFO, log_file=str(log_file))

        # Get module logger and use it
        module_logger = get_logger("my_test_module")
        module_logger.info("Module logger test")

        # Verify message was logged
        content = log_file.read_text()
        assert "Module logger test" in content
