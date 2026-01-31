"""
NornFlow Logging Module

This module provides a centralized logging system for NornFlow applications.
It implements a singleton logger that supports synchronous file-based logging with
timestamped log files and execution context tracking.

Key Features:
- Singleton pattern for consistent logging across the application
- Synchronous file logging with automatic log file creation
- Custom formatter for precise timestamps with microseconds
- Execution context tracking for workflow and task runs
- Configurable log levels and directories

Usage:
    from nornflow.logger import logger

    logger.info("This is an info message")
    logger.set_execution_context("my_workflow", "workflow", "/path/to/logs", "INFO")
    logger.debug("This will go to the log file")
"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from nornflow.constants import NORNFLOW_DEFAULT_LOGGER, PROTECTED_KEYWORDS

REDACTED = "***REDACTED***"


def _get_sanitize_pattern() -> re.Pattern:
    """Get or build the compiled regex pattern for sensitive data detection."""
    if not hasattr(_get_sanitize_pattern, "_pattern"):
        keywords = "|".join(re.escape(kw) for kw in PROTECTED_KEYWORDS)
        _get_sanitize_pattern._pattern = re.compile(  # noqa: SLF001
            rf"({keywords})(\s*[:=]\s*)(['\"]?)(\S+?)(\3)(?=\s|,|}}|\]|$)", re.IGNORECASE
        )
    return _get_sanitize_pattern._pattern  # noqa: SLF001


def sanitize_log_message(message: str) -> str:
    """Sanitize sensitive data from a log message.

    Args:
        message: The log message to sanitize.

    Returns:
        Message with sensitive values replaced by REDACTED.
    """
    if not isinstance(message, str):
        return message
    return _get_sanitize_pattern().sub(rf"\1\2\3{REDACTED}\5", message)


def sanitize_filename(name: str) -> str:
    """Sanitize a string for safe use as a filename.

    Prevents path traversal attacks and invalid filename characters.

    Args:
        name: The raw name to sanitize.

    Returns:
        A safe filename string containing only alphanumeric chars, dots,
        hyphens, and underscores.
    """
    if not name:
        return "unnamed"

    sanitized = name.replace("/", "_").replace("\\", "_")
    sanitized = sanitized.replace("..", "_")
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip("_. ")

    if not sanitized:
        return "unnamed"

    return sanitized


class MicrosecondFormatter(logging.Formatter):
    """Custom formatter with microsecond timestamps and sensitive data sanitization."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        """Format the time with microseconds support."""
        ct = datetime.fromtimestamp(record.created)  # noqa: DTZ006
        s = ct.strftime(datefmt) if datefmt else ct.isoformat()
        return s

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with sanitized message."""
        record.msg = sanitize_log_message(str(record.msg))
        if record.args:
            record.args = tuple(
                sanitize_log_message(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        return super().format(record)


class NornFlowLogger:
    """
    Singleton logger class for NornFlow.

    This class manages a single logger instance that can be configured
    to write to files based on execution context.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # Core logger
        self._logger = logging.getLogger("nornflow")
        self._logger.setLevel(logging.DEBUG)

        # Console handler for ERROR level and above (always active for visibility)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.ERROR)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)

        # Execution context
        self._execution_context = None
        self._file_handler = None

    def set_execution_context(
        self,
        execution_name: str,
        execution_type: str,
        log_dir: str | Path | None = None,
        log_level: str = "INFO",
    ) -> None:
        """
        Set the execution context for logging.

        This creates a timestamped log file and configures the logger to write to it.

        Args:
            execution_name: Name of the execution (workflow name, task name, etc.)
            execution_type: Type of execution ("workflow", "task", etc.)
            log_dir: Directory to store log files. If None, uses default.
            log_level: Logging level (e.g., "DEBUG", "INFO").
        """
        # Remove existing file handler if present
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

        # Use default if log_dir is None
        if not log_dir:
            log_dir = NORNFLOW_DEFAULT_LOGGER["directory"]

        # Set logger level
        level = getattr(logging, log_level.upper(), logging.INFO)
        self._logger.setLevel(level)

        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename with sanitized execution name
        safe_name = sanitize_filename(execution_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.log"
        filepath = log_path / filename

        # Create file handler
        self._file_handler = logging.FileHandler(filepath, encoding="utf-8")
        self._file_handler.setLevel(level)

        # Create file formatter with microsecond timestamps
        self._file_handler.setFormatter(
            MicrosecondFormatter("%(asctime)s [%(levelname)s] [%(name)s] - %(message)s")
        )

        # Add file handler to logger
        self._logger.addHandler(self._file_handler)

        # Store execution context
        self._execution_context = {
            "execution_name": execution_name,
            "execution_type": execution_type,
            "log_dir": str(log_dir),
            "log_file": str(filepath),
            "start_time": datetime.now(),
        }

        # Log the start of execution
        self.info(f"Started {execution_type} execution: {execution_name}")

    def update_execution_context(
        self,
        execution_name: str | None = None,
        execution_type: str | None = None,
        log_dir: str | Path | None = None,
        log_level: str | None = None,
    ) -> None:
        """Update the execution context for logging by renaming the existing file and updating the handler.

        Args:
            execution_name: New execution name (optional).
            execution_type: New execution type (optional).
            log_dir: New log directory (optional).
            log_level: New log level (optional).
        """
        if not self._file_handler or not self._execution_context:
            return

        updated = False
        old_filepath = Path(self._execution_context["log_file"])

        if execution_name or execution_type:
            self._execution_context["execution_name"] = execution_name or self._execution_context.get(
                "execution_name", "unknown"
            )
            self._execution_context["execution_type"] = execution_type or self._execution_context.get(
                "execution_type", "unknown"
            )
            updated = True

        if log_level:
            level = getattr(logging, log_level.upper(), logging.INFO)
            self._logger.setLevel(level)
            self._file_handler.setLevel(level)
            updated = True

        if log_dir or updated:
            new_log_path = Path(log_dir or self._execution_context["log_dir"])
            new_log_path.mkdir(parents=True, exist_ok=True)
            safe_name = sanitize_filename(self._execution_context["execution_name"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{safe_name}_{timestamp}.log"
            new_filepath = new_log_path / new_filename

            # Close the handler, try to rename, then reopen
            self._file_handler.close()
            try:
                old_filepath.rename(new_filepath)
                actual_filepath = new_filepath
            except OSError:
                # If rename fails, keep using the old file
                actual_filepath = old_filepath

            self._file_handler.baseFilename = str(actual_filepath)
            self._file_handler.stream = actual_filepath.open("a", encoding="utf-8")

            self._execution_context["log_dir"] = str(new_log_path)
            self._execution_context["log_file"] = str(actual_filepath)
            updated = True

    def clear_execution_context(self) -> None:
        """
        Clear the current execution context and stop file logging.
        """
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

        if self._execution_context:
            execution_time = datetime.now() - self._execution_context["start_time"]
            self.info(f"Completed execution in {execution_time.total_seconds():.2f} seconds")

        self._execution_context = None

    def get_execution_context(self) -> dict[str, Any] | None:
        """
        Get the current execution context.

        Returns:
            Current execution context dict or None if not set
        """
        return self._execution_context

    def debug(self, message: str, *args: object, **kwargs) -> None:
        """Log a debug message."""
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: object, **kwargs) -> None:
        """Log an info message."""
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: object, **kwargs) -> None:
        """Log a warning message."""
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: object, **kwargs) -> None:
        """Log an error message."""
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: object, **kwargs) -> None:
        """Log a critical message."""
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args: object, **kwargs) -> None:
        """Log an exception with traceback."""
        self._logger.exception(message, *args, **kwargs)


# Create the singleton instance
logger = NornFlowLogger()
