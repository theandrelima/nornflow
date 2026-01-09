import logging
import logging.handlers
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from nornflow.constants import NORNFLOW_DEFAULT_LOGGER

# Thread-safe queue for async logging
_log_queue = queue.Queue()
_listener = None
_listener_thread = None

class NornFlowLogger:
    """
    Singleton logger for NornFlow with lazy initialization and async support.

    This logger manages file-based logging with execution context tracking.
    It uses a queue-based async approach for performance and supports
    configuration via NornFlowSettings.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # Core logger
        self._logger = logging.getLogger('nornflow')
        self._logger.setLevel(logging.DEBUG)  # Set to lowest level, filter via handlers

        # NullHandler as default (no output until context set)
        null_handler = logging.NullHandler()
        self._logger.addHandler(null_handler)

        # Execution context
        self._execution_context = {}
        self._file_handler = None
        self._queue_handler = None

        # Async setup
        self._setup_async_logging()

    def _setup_async_logging(self):
        """Set up async logging with queue handler and listener."""
        global _listener, _listener_thread

        # Queue handler for main thread
        self._queue_handler = logging.handlers.QueueHandler(_log_queue)
        self._logger.addHandler(self._queue_handler)

        # Listener in background thread
        if _listener is None:
            _listener = logging.handlers.QueueListener(_log_queue)
            _listener_thread = threading.Thread(target=_listener.start, daemon=True)
            _listener_thread.start()

    def set_execution_context(self, execution_name: str, execution_type: str, log_dir: str | None = None):
        """
        Establish execution context and configure file logging.

        Args:
            execution_name: Name of the execution (workflow/task name).
            execution_type: Type of execution ('workflow', 'task', etc.).
            log_dir: Directory for log files (from settings).
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"{execution_name}_{timestamp}.log"

        log_dir = log_dir or NORNFLOW_DEFAULT_LOGGER["directory"]
        log_path = Path(log_dir) / log_filename

        # Create directory if needed
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # Fallback to stderr
            error_handler = logging.StreamHandler()
            error_handler.setFormatter(self._get_formatter())
            self._logger.addHandler(error_handler)
            self._logger.error(f"Failed to create log directory {log_dir}: {e}")
            return

        # File handler
        try:
            self._file_handler = logging.FileHandler(log_path, encoding='utf-8')
            self._file_handler.setFormatter(self._get_formatter())
            _listener.addHandler(self._file_handler)
        except Exception as e:
            # Fallback to stderr
            error_handler = logging.StreamHandler()
            error_handler.setFormatter(self._get_formatter())
            self._logger.addHandler(error_handler)
            self._logger.error(f"Failed to create log file {log_path}: {e}")

        # Update context
        self._execution_context = {
            'execution_name': execution_name,
            'execution_type': execution_type,
            'log_dir': log_dir,
            'log_path': str(log_path),
            'start_time': datetime.now(),
        }

    def _get_formatter(self) -> logging.Formatter:
        """Get the standard log formatter."""
        return logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%f'
        )

    def get_execution_context(self) -> dict[str, Any]:
        """Get current execution context."""
        return self._execution_context.copy()

    def clear_execution_context(self):
        """Clear execution context and close handlers."""
        if self._file_handler:
            _listener.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None
        self._execution_context = {}

    # Delegate logging methods
    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        self._logger.exception(message, *args, **kwargs)

# Global logger instance
logger = NornFlowLogger()