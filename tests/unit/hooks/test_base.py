from unittest.mock import MagicMock

from nornflow.hooks.base import Hook
from nornflow.hooks.exceptions import HookConfigurationError


class TestHook:
    """Test suite for base Hook class."""

    def test_init_with_value(self):
        """Test Hook initialization with a value."""
        hook = Hook("test_value")
        assert hook.value == "test_value"

    def test_init_without_value(self):
        """Test Hook initialization without a value."""
        hook = Hook()
        assert hook.value is None

    def test_execution_tracking(self):
        """Test that hooks track execution count."""
        hook = Hook()
        assert hook._execution_count == {}
        
    def test_current_context_initial(self):
        """Test that initial context is None."""
        hook = Hook()
        assert hook._current_context is None

    def test_should_execute_default(self):
        """Test should_execute returns True by default."""
        hook = Hook()
        hook.run_once_per_task = False
        mock_task = MagicMock()
        
        # Should always return True when run_once_per_task is False
        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True

    def test_should_execute_once_per_task(self):
        """Test should_execute with run_once_per_task flag."""
        hook = Hook()
        hook.run_once_per_task = True
        mock_task = MagicMock()
        
        # First call should return True
        assert hook.should_execute(mock_task) is True
        
        # Subsequent calls with same task should return False
        assert hook.should_execute(mock_task) is False
        assert hook.should_execute(mock_task) is False
        
        # Different task should return True
        mock_task2 = MagicMock()
        assert hook.should_execute(mock_task2) is True

    def test_get_context_empty(self):
        """Test context property returns empty dict when no context set."""
        hook = Hook()
        
        context = hook.context
        assert context == {}

    def test_get_context_with_current_context(self):
        """Test context property returns current context when set."""
        hook = Hook()
        hook._current_context = {"key": "value"}
        
        context = hook.context
        assert context == {"key": "value"}

    def test_processor_methods_are_optional(self):
        """Test that all processor methods have default implementations."""
        hook = Hook()
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()
        
        # These should all execute without error
        hook.task_started(mock_task)
        hook.task_completed(mock_task, mock_result)
        hook.task_instance_started(mock_task, mock_host)
        hook.task_instance_completed(mock_task, mock_host, mock_result)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)

    def test_execute_hook_validations_default(self):
        """Test that execute_hook_validations does nothing by default."""
        hook = Hook()
        mock_task_model = MagicMock()
        
        # Should not raise
        hook.execute_hook_validations(mock_task_model)

    def test_exception_handlers_default(self):
        """Test that exception_handlers is empty by default."""
        hook = Hook()
        assert hook.exception_handlers == {}