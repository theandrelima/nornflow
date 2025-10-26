from unittest.mock import MagicMock

import pytest
from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Result, Task

from nornflow.builtins.hooks import SetToHook
from nornflow.hooks.exceptions import HookValidationError


class TestSetToHook:
    """Test suite for SetToHook."""

    def test_hook_name_registration(self):
        """Test that hook has correct name for registration."""
        assert SetToHook.hook_name == "set_to"

    def test_run_once_per_task_flag(self):
        """Test that hook runs per host, not once per task."""
        assert SetToHook.run_once_per_task is False

    def test_init_with_value(self):
        """Test hook initialization with a variable name."""
        hook = SetToHook("my_variable")
        assert hook.value == "my_variable"

    def test_init_without_value(self):
        """Test hook initialization without a value."""
        hook = SetToHook()
        assert hook.value is None

    def test_validate_task_compatibility_valid_task(self):
        """Test validation passes for compatible tasks."""
        hook = SetToHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "ping"

        # Should not raise
        hook.validate_task_compatibility(mock_task_model)

    def test_validate_task_compatibility_invalid_set_task(self):
        """Test validation fails for 'set' task."""
        hook = SetToHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "set"

        with pytest.raises(HookValidationError, match="Hook 'SetToHook' cannot be used with task 'set'"):
            hook.validate_task_compatibility(mock_task_model)

    def test_validate_task_compatibility_invalid_echo_task(self):
        """Test validation fails for 'echo' task."""
        hook = SetToHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "echo"

        with pytest.raises(HookValidationError, match="Hook 'SetToHook' cannot be used with task 'echo'"):
            hook.validate_task_compatibility(mock_task_model)

    def test_validate_task_compatibility_invalid_set_to_task(self):
        """Test validation fails for 'set_to' task."""
        hook = SetToHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "set_to"

        with pytest.raises(HookValidationError, match="Hook 'SetToHook' cannot be used with task 'set_to'"):
            hook.validate_task_compatibility(mock_task_model)

    def test_task_instance_completed_stores_result(self):
        """Test that task_instance_completed stores result in runtime variable."""
        hook = SetToHook("test_variable")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_result = MagicMock(spec=MultiResult)
        mock_vars_manager = MagicMock()
        
        # Set up the context
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_called_once_with("test_variable", mock_result, "router1")

    def test_task_instance_completed_no_value_does_nothing(self):
        """Test that task_instance_completed does nothing when value is None."""
        hook = SetToHook(None)
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_result = MagicMock(spec=MultiResult)
        mock_vars_manager = MagicMock()
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_not_called()

    def test_task_instance_completed_no_result_does_nothing(self):
        """Test that task_instance_completed does nothing when result is None."""
        hook = SetToHook("test_variable")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_vars_manager = MagicMock()
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, None)

        mock_vars_manager.set_runtime_variable.assert_not_called()

    def test_task_instance_completed_no_vars_manager_does_nothing(self):
        """Test that task_instance_completed does nothing when vars_manager is not in context."""
        hook = SetToHook("test_variable")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_result = MagicMock(spec=MultiResult)
        
        # No vars_manager in context
        hook._current_context = {}

        # Should not raise any exceptions
        hook.task_instance_completed(mock_task, mock_host, mock_result)

    def test_task_instance_completed_no_context_does_nothing(self):
        """Test that task_instance_completed handles missing context gracefully."""
        hook = SetToHook("test_variable")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_result = MagicMock(spec=MultiResult)
        
        # No context set
        hook._current_context = None

        # Should not raise any exceptions
        hook.task_instance_completed(mock_task, mock_host, mock_result)

    def test_get_context_returns_empty_when_no_context(self):
        """Test get_context returns empty dict when no context is set."""
        hook = SetToHook("test_variable")
        mock_task = MagicMock()
        
        context = hook.get_context(mock_task)
        assert context == {}

    def test_task_instance_completed_with_complex_result(self):
        """Test storing complex result objects."""
        hook = SetToHook("complex_var")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "switch1"
        
        # Create a more realistic MultiResult
        mock_result = MultiResult("test_task")
        mock_result.append(Result(host=mock_host, result={"config": "data"}, changed=True))
        
        mock_vars_manager = MagicMock()
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_called_once_with("complex_var", mock_result, "switch1")

    def test_other_processor_methods_do_nothing(self):
        """Test that other processor methods have no implementation."""
        hook = SetToHook("test_var")
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()

        # These should not raise any exceptions
        hook.task_started(mock_task)
        hook.task_completed(mock_task, mock_result)
        hook.task_instance_started(mock_task, mock_host)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)

    def test_should_execute_always_returns_true(self):
        """Test that hook executes for every host (run_once_per_task=False)."""
        hook = SetToHook("test_var")
        mock_task = MagicMock()

        # Should always return True since run_once_per_task is False
        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True

    def test_task_instance_completed_handles_string_host_name(self):
        """Test that hook works correctly with string host names."""
        hook = SetToHook("host_result")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "complex-host-name.domain.com"
        
        mock_result = MagicMock(spec=MultiResult)
        mock_vars_manager = MagicMock()
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_called_once_with(
            "host_result", mock_result, "complex-host-name.domain.com"
        )

    def test_validation_error_message_includes_incompatible_tasks(self):
        """Test that validation error message lists all incompatible tasks."""
        hook = SetToHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "set"

        with pytest.raises(HookValidationError) as exc_info:
            hook.validate_task_compatibility(mock_task_model)

        error_message = str(exc_info.value)
        assert "set" in error_message
        assert "echo" in error_message
        assert "set_to" in error_message