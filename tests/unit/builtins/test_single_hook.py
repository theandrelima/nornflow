"""Tests for SingleHook functionality."""

from unittest.mock import MagicMock, patch

import pytest

from nornflow.builtins.constants import SILENT_SKIP_FLAG
from nornflow.builtins.hooks import SingleHook
from nornflow.hooks.exceptions import HookValidationError


class TestSingleHook:
    """Test suite for SingleHook."""

    def test_hook_name_registration(self):
        """Test that hook has correct name for registration."""
        assert SingleHook.hook_name == "single"

    def test_run_once_per_task_flag(self):
        """Test that hook runs per host, not once per task."""
        assert SingleHook.run_once_per_task is False

    def test_init_with_value(self):
        """Test SingleHook initialization with a value."""
        hook = SingleHook(True)
        assert hook.value is True
        assert hook._delegate_host is None
        assert hook._lock is not None
        assert hook._active is False

    def test_init_without_value(self):
        """Test SingleHook initialization without a value."""
        hook = SingleHook()
        assert hook.value is None

    def test_execute_hook_validations_valid_bool(self, mock_task):
        """Test validation passes for valid boolean values."""
        hook = SingleHook(True)
        hook.execute_hook_validations(mock_task)

        hook = SingleHook(False)
        hook.execute_hook_validations(mock_task)

    def test_execute_hook_validations_valid_jinja2_string(self, mock_task):
        """Test validation passes for valid Jinja2 strings."""
        hook = SingleHook("{{ var }}")
        hook.execute_hook_validations(mock_task)

    def test_execute_hook_validations_invalid_types(self, mock_task):
        """Test validation raises error for invalid types."""
        hook = SingleHook([1, 2, 3])
        with pytest.raises(HookValidationError, match=r"single value must be a boolean, Jinja2 expression string, or None, got list"):
            hook.execute_hook_validations(mock_task)

        hook = SingleHook({"key": "value"})
        with pytest.raises(HookValidationError, match=r"single value must be a boolean, Jinja2 expression string, or None, got dict"):
            hook.execute_hook_validations(mock_task)

        hook = SingleHook(123)
        with pytest.raises(HookValidationError, match=r"single value must be a boolean, Jinja2 expression string, or None, got int"):
            hook.execute_hook_validations(mock_task)

    def test_execute_hook_validations_empty_string(self, mock_task):
        """Test validation raises error for empty strings."""
        hook = SingleHook("")
        with pytest.raises(HookValidationError, match="single value cannot be an empty string"):
            hook.execute_hook_validations(mock_task)

    def test_execute_hook_validations_mutual_exclusion_with_if(self, mock_task):
        """Test validation raises error when 'if' hook is also present."""
        hook = SingleHook(True)
        mock_task.hooks = {"if": {"hosts": ["host1"]}}
        with pytest.raises(HookValidationError, match="'single' and 'if' hooks cannot be used on the same task"):
            hook.execute_hook_validations(mock_task)

    def test_task_started_activates_hook(self, mock_vars_manager):
        """Test task_started activates the hook when resolved to True."""
        hook = SingleHook(True)
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_host.name = "host1"
        mock_task.nornir.inventory.hosts = {"host1": mock_host}
        hook._current_context = {"vars_manager": mock_vars_manager}

        original_func = mock_task.task
        hook.task_started(mock_task)

        assert hook._active is True
        assert hook._delegate_host is None
        assert mock_task.task != original_func

    def test_task_started_deactivates_hook(self, mock_vars_manager):
        """Test task_started deactivates the hook when resolved to False."""
        hook = SingleHook(False)
        mock_task = MagicMock()
        hook._current_context = {"vars_manager": mock_vars_manager}

        original_func = mock_task.task
        hook.task_started(mock_task)

        assert hook._active is False
        assert mock_task.task == original_func

    def test_task_started_resolves_jinja2(self, mock_vars_manager):
        """Test task_started resolves Jinja2 expressions."""
        hook = SingleHook("{{ enable_single }}")
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_host.name = "host1"
        mock_task.nornir.inventory.hosts = {"host1": mock_host}
        mock_vars_manager.resolve_string.return_value = "true"
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_started(mock_task)

        assert hook._active is True
        mock_vars_manager.resolve_string.assert_called_once()

    def test_task_instance_started_sets_delegate(self, mock_host):
        """Test task_instance_started designates the first host as delegate."""
        hook = SingleHook()
        hook._active = True
        mock_task = MagicMock()

        hook.task_instance_started(mock_task, mock_host)

        assert hook._delegate_host == mock_host.name

    def test_task_instance_started_skips_subsequent_hosts(self, mock_host):
        """Test task_instance_started flags subsequent hosts for silent skip."""
        hook = SingleHook()
        hook._active = True
        hook._delegate_host = "delegate_host"
        mock_task = MagicMock()

        hook.task_instance_started(mock_task, mock_host)

        assert mock_host.data[SILENT_SKIP_FLAG] is True

    def test_task_instance_started_inactive_does_nothing(self, mock_host):
        """Test task_instance_started does nothing when hook is inactive."""
        hook = SingleHook()
        hook._active = False
        mock_task = MagicMock()

        hook.task_instance_started(mock_task, mock_host)

        assert hook._delegate_host is None
        assert SILENT_SKIP_FLAG not in mock_host.data

    def test_task_completed_resets_state(self):
        """Test task_completed resets hook state."""
        hook = SingleHook()
        hook._active = True
        hook._delegate_host = "some_host"
        mock_result = MagicMock()

        hook.task_completed(task=MagicMock(), result=mock_result)

        assert hook._delegate_host is None
        assert hook._active is False

    def test_skip_if_silent_flagged_decorator_skips(self):
        """Test skip_if_silent_flagged decorator returns skip result when flagged.

        The decorator does NOT clean up the flag — that responsibility belongs
        to DefaultNornFlowProcessor.task_instance_completed.
        """
        from nornflow.builtins.hooks.single import skip_if_silent_flagged
        from nornir.core.task import Result

        mock_task = MagicMock()
        mock_task.host.data = {SILENT_SKIP_FLAG: True}

        decorated_func = skip_if_silent_flagged(lambda task: Result(host=task.host, result="should not run"))
        result = decorated_func(mock_task)

        assert result.skipped is True
        assert result.result is None
        assert mock_task.host.data.get(SILENT_SKIP_FLAG) is True

    def test_skip_if_silent_flagged_decorator_executes(self):
        """Test skip_if_silent_flagged decorator executes task when not flagged."""
        from nornflow.builtins.hooks.single import skip_if_silent_flagged
        from nornir.core.task import Result

        mock_task = MagicMock()
        mock_task.host.data = {}

        decorated_func = skip_if_silent_flagged(lambda task: Result(host=task.host, result="executed"))
        result = decorated_func(mock_task)

        assert result.result == "executed"

    def test_should_execute_always_returns_true(self):
        """Test that hook executes for every host (run_once_per_task=False)."""
        hook = SingleHook("{{ true }}")
        mock_task = MagicMock()

        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True

    def test_context_property_returns_empty_when_no_context(self):
        """Test context property returns empty dict when no context is set."""
        hook = SingleHook("{{ true }}")

        context = hook.context
        assert context == {}

    def test_other_processor_methods_do_nothing(self):
        """Test that other processor methods have no implementation."""
        hook = SingleHook("{{ true }}")
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()

        hook.task_completed(mock_task, mock_result)
        hook.task_instance_completed(mock_task, mock_host, mock_result)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)

    def test_multiple_hosts_only_first_becomes_delegate(self):
        """Test that only the first host calling task_instance_started becomes delegate."""
        hook = SingleHook()
        hook._active = True
        mock_task = MagicMock()

        host1 = MagicMock()
        host1.name = "host1"
        host1.data = {}

        host2 = MagicMock()
        host2.name = "host2"
        host2.data = {}

        host3 = MagicMock()
        host3.name = "host3"
        host3.data = {}

        hook.task_instance_started(mock_task, host1)
        hook.task_instance_started(mock_task, host2)
        hook.task_instance_started(mock_task, host3)

        assert hook._delegate_host == "host1"
        assert SILENT_SKIP_FLAG not in host1.data
        assert host2.data[SILENT_SKIP_FLAG] is True
        assert host3.data[SILENT_SKIP_FLAG] is True

    def test_delegate_host_does_not_get_flagged(self):
        """Test that the delegate host never receives the silent skip flag."""
        hook = SingleHook()
        hook._active = True
        mock_task = MagicMock()

        delegate = MagicMock()
        delegate.name = "delegate"
        delegate.data = {}

        hook.task_instance_started(mock_task, delegate)

        assert hook._delegate_host == "delegate"
        assert SILENT_SKIP_FLAG not in delegate.data

    def test_task_started_with_none_value_stays_inactive(self, mock_vars_manager):
        """Test task_started with None value keeps hook inactive."""
        hook = SingleHook(None)
        mock_task = MagicMock()
        hook._current_context = {"vars_manager": mock_vars_manager}

        original_func = mock_task.task
        hook.task_started(mock_task)

        assert hook._active is False
        assert mock_task.task == original_func

    def test_execute_hook_validations_no_hooks_attribute(self):
        """Test validation passes when task model has no hooks attribute."""
        hook = SingleHook(True)
        mock_task_model = MagicMock(spec=[])
        mock_task_model.name = "test_task"

        hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_hooks_without_if(self, mock_task):
        """Test validation passes when hooks dict has other hooks but not 'if'."""
        hook = SingleHook(True)
        mock_task.hooks = {"shush": True, "set_to": "my_var"}

        hook.execute_hook_validations(mock_task)

    def test_execute_hook_validations_float_rejected(self, mock_task):
        """Test validation rejects float values."""
        hook = SingleHook(1.5)
        with pytest.raises(HookValidationError, match=r"single value must be a boolean, Jinja2 expression string, or None, got float"):
            hook.execute_hook_validations(mock_task)

    def test_execute_hook_validations_whitespace_string(self, mock_task):
        """Test validation rejects whitespace-only strings."""
        hook = SingleHook("   ")
        with pytest.raises(HookValidationError, match="single value cannot be an empty string"):
            hook.execute_hook_validations(mock_task)

    def test_task_completed_can_be_called_when_already_inactive(self):
        """Test task_completed is safe to call when hook is already inactive."""
        hook = SingleHook()
        hook._active = False
        hook._delegate_host = None

        hook.task_completed(task=MagicMock(), result=MagicMock())

        assert hook._delegate_host is None
        assert hook._active is False
