"""
NornFlow Logging Module

This module provides a centralized logging system for NornFlow applications.
It implements a singleton logger that supports file-based logging with
timestamped log files and execution context tracking.

Key Features:
- Singleton pattern for consistent logging across the application
- File-based logging with automatic log file creation
- Execution context tracking for workflow and task runs
- Configurable log levels and directories

Usage:
    from nornflow.logger import logger
    
    logger.info("This is an info message")
    logger.set_execution_context("my_workflow", "workflow", "/path/to/logs")
    logger.debug("This will go to the log file")
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from nornflow.constants import NORNFLOW_DEFAULT_LOGGER


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
        
        # NullHandler as default (no output until context set)
        null_handler = logging.NullHandler()
        self._logger.addHandler(null_handler)
        
        # Execution context
        self._execution_context = None
        self._file_handler = None
    
    def set_execution_context(self, execution_name: str, execution_type: str, log_dir: str | Path | None = None) -> None:
        """
        Set the execution context for logging.
        
        This creates a timestamped log file and configures the logger to write to it.
        
        Args:
            execution_name: Name of the execution (workflow name, task name, etc.)
            execution_type: Type of execution ("workflow", "task", etc.)
            log_dir: Directory to store log files. If None, uses default.
        """
        # Remove existing file handler if present
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None
        
        # Use default if log_dir is None
        if not log_dir:
            log_dir = NORNFLOW_DEFAULT_LOGGER["directory"]
        
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{execution_name}_{timestamp}.log"
        filepath = log_path / filename
        
        # Create file handler
        self._file_handler = logging.FileHandler(filepath, encoding="utf-8")
        self._file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] [%(funcName)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S.%f"
        )
        formatter.default_msec_format = "%s.%03d"
        self._file_handler.setFormatter(formatter)
        
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


# Create the singleton instance
logger = NornFlowLogger()