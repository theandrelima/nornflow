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
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from nornflow.constants import NORNFLOW_DEFAULT_LOGGER


class MicrosecondFormatter(logging.Formatter):
    """Custom formatter to include microseconds in timestamps using datetime."""
    
    def formatTime(self, record, datefmt=None):
        """Format the time with microseconds support."""
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.isoformat()
        return s


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
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Core logger
        self._logger = logging.getLogger('nornflow')
        self._logger.setLevel(logging.DEBUG)
        
        # Console handler for ERROR level and above (always active for visibility)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.ERROR)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)
        
        # Execution context
        self._execution_context = None
        self._file_handler = None
    
    def set_execution_context(self, execution_name: str, execution_type: str, log_dir: str | Path | None = None, log_level: str = "INFO") -> None:
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
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{execution_name}_{timestamp}.log"
        filepath = log_path / filename
        
        # Create file handler
        self._file_handler = logging.FileHandler(filepath, encoding="utf-8")
        self._file_handler.setLevel(level)
        
        # Create file formatter with conditional funcName
        self._file_handler.setFormatter(ConditionalFuncNameFormatter())
        
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
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """Log an info message."""
        self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """Log an error message."""
        self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Log a critical message."""
        self._logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs) -> None:
        """Log an exception with traceback."""
        self._logger.exception(message, *args, **kwargs)


class ConditionalFuncNameFormatter(MicrosecondFormatter):
    """
    Custom formatter that conditionally includes funcName only if it's not a logger wrapper method.
    """
    
    LOGGER_METHODS = {'debug', 'info', 'warning', 'error', 'critical', 'exception'}
    
    def format(self, record):
        if record.funcName in self.LOGGER_METHODS:
            self._style._fmt = "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s"
        else:
            self._style._fmt = "%(asctime)s [%(levelname)s] [%(name)s] [%(funcName)s] - %(message)s"
        return super().format(record)


# Create the singleton instance
logger = NornFlowLogger()
