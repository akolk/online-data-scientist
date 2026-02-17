"""Centralized logging configuration for the Online Data Scientist application.

This module provides a centralized logging setup with configurable log levels,
structured output, and support for both console and file handlers. It ensures
consistent logging across all modules in the application.

Usage:
    Import and call setup_logging() at application startup:
    
    from logging_config import setup_logging
    setup_logging()
    
    Then use logging in other modules:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Your message here")

Configuration:
    Set the LOG_LEVEL environment variable to control logging verbosity:
    - DEBUG: Detailed information for debugging
    - INFO: General information (default)
    - WARNING: Only warnings and errors
    - ERROR: Only errors
    - CRITICAL: Only critical errors
    
    Set LOG_FILE to specify a log file path (default: logs/app.log)
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
)

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

DEFAULT_LOG_LEVEL = "INFO"

DEFAULT_LOG_FILE = "logs/app.log"

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB

DEFAULT_BACKUP_COUNT = 5


def get_log_level() -> int:
    """Get the log level from environment variable.
    
    Returns:
        int: Logging level constant (e.g., logging.DEBUG)
    """
    level_name = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    return getattr(logging, level_name, logging.INFO)


def get_log_file_path() -> Optional[str]:
    """Get the log file path from environment variable.
    
    Returns:
        str or None: Path to log file, or None if logging to file is disabled
    """
    log_file = os.getenv("LOG_FILE", DEFAULT_LOG_FILE)
    
    # Allow disabling file logging by setting LOG_FILE to empty string or "none"
    if not log_file or log_file.lower() in ("none", "null", "disabled"):
        return None
    
    return log_file


def ensure_log_directory(log_file: str) -> None:
    """Ensure the log directory exists.
    
    Args:
        log_file: Path to the log file
    """
    log_path = Path(log_file)
    if log_path.parent:
        log_path.parent.mkdir(parents=True, exist_ok=True)


def setup_logging(
    log_level: Optional[int] = None,
    log_format: Optional[str] = None,
    date_format: Optional[str] = None,
    log_file: Optional[str] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT
) -> logging.Logger:
    """Setup centralized logging configuration.
    
    Configures the root logger with console and optional file handlers.
    Uses rotating file handlers to prevent disk space issues.
    
    Args:
        log_level: Logging level (default: from LOG_LEVEL env var or INFO)
        log_format: Format string for log messages
        date_format: Format string for timestamps
        log_file: Path to log file (default: from LOG_FILE env var or logs/app.log)
        max_bytes: Maximum bytes per log file before rotation
        backup_count: Number of backup log files to keep
    
    Returns:
        Logger: The configured root logger
    
    Example:
        >>> logger = setup_logging()
        >>> logger.info("Application started")
        
        >>> # Custom configuration
        >>> logger = setup_logging(
        ...     log_level=logging.DEBUG,
        ...     log_file="/var/log/myapp.log"
        ... )
    """
    # Use defaults if not provided
    level = log_level if log_level is not None else get_log_level()
    fmt = log_format or DEFAULT_LOG_FORMAT
    dt_fmt = date_format or DEFAULT_DATE_FORMAT
    file_path = log_file if log_file is not None else get_log_file_path()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(fmt, datefmt=dt_fmt)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if file_path:
        try:
            ensure_log_directory(file_path)
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            # Log to console if file handler fails
            console_handler.error(f"Failed to setup file logging to {file_path}: {e}")
    
    # Log configuration details at debug level
    root_logger.debug(
        f"Logging configured: level={logging.getLevelName(level)}, "
        f"file={file_path}, format='{fmt}'"
    )
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    This is a convenience function that returns a logger with the given name.
    setup_logging() should be called before using loggers.
    
    Args:
        name: The name for the logger (typically __name__)
    
    Returns:
        Logger: A configured logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(name)


# Example usage when run directly
if __name__ == "__main__":
    # Setup logging with default configuration
    logger = setup_logging(log_level=logging.DEBUG)
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Get module-specific logger
    module_logger = get_logger("test_module")
    module_logger.info("Module-specific logger test")
