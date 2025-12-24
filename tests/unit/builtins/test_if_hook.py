from unittest.mock import MagicMock, patch

import pytest
from nornir.core.inventory import Host
from nornir.core.task import Result, Task

from nornflow.builtins.hooks import IfHook
from nornflow.hooks.exceptions import HookValidationError


class TestIfHook:
    """Test suite for IfHook conditional execution."""

    def test_hook_name_registration(self):
        """Test that hook has correct name for registration."""
        assert IfHook.hook_name == "if"

    def test_run_once_per_task_flag(self):
        """Test that hook evaluates per host, not once per task."""
        assert IfHook.run_once_per_task is False

    def test_requires_deferred_templates_flag(self):
        """Test that hook declares requirement for deferred template processing."""
        assert IfHook.requires_deferred_templates is True

    def test_init_with_filter_value(self):
        """Test hook initialization with filter configuration."""
        hook = IfHook({"platform": "ios"})
        assert hook.value == {"platform": "ios"}

    def test_init_with_jinja_value(self):
        """Test hook initialization with Jinja2 expression."""
        hook = IfHook("{{ host.platform == 'ios' }}")
        assert hook.value == "{{ host.platform == 'ios' }}"

    def test_init_without_value(self):
        """Test hook initialization without a value."""
        hook = IfHook()
        assert hook.value is None

    def test_execute_hook_validations_valid_filter_dict(self):
        """Test validation passes for valid filter dictionary."""
        hook = IfHook({"platform": "ios"})
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_valid_jinja_string(self):
        """Test validation passes for valid Jinja2 expression."""
        hook = IfHook("{{ host.platform == 'ios' }}")
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_invalid_multiple_filters(self):
        """Test validation fails for dict with multiple filter keys."""
        hook = IfHook({"platform": "ios", "site": "dc1"})
        mock_task_model = MagicMock()

        with pytest.raises(HookValidationError, match="if must specify exactly one filter"):
            hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_invalid_empty_string(self):
        """Test validation fails for empty string."""
        hook = IfHook("")
        mock_task_model = MagicMock()
        mock_task_model.name = "test_task"

        with pytest.raises(HookValidationError, match="Task 'test_task': if value cannot be empty string"):
            hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_invalid_type(self):
        """Test validation fails for invalid value type."""
        hook = IfHook(123)
        mock_task_model = MagicMock()

        with pytest.raises(HookValidationError, match="if value must be a dict \\(Nornir filter\\) or string \\(Jinja2 expression\\)"):
            hook.execute_hook_validations(mock_task_model)

    def test_task_started_applies_decorator(self):
        """Test that task_started applies the skip decorator to the task function."""
        hook = IfHook("{{ true }}")
        mock_task = MagicMock(spec=Task)
        mock_task.name = "test_task"
        original_func = MagicMock()
        mock_task.task = original_func

        hook.task_started(mock_task)

        assert mock_task.task != original_func
        assert hasattr(mock_task.task, '__wrapped__')

    def test_task_started_no_value_does_nothing(self):
        """Test that task_started does nothing when value is None."""
        hook = IfHook(None)
        mock_task = MagicMock(spec=Task)
        mock_task.name = "test_task"
        original_func = MagicMock()
        mock_task.task = original_func

        hook.task_started(mock_task)

        assert mock_task.task == original_func

    @patch('nornflow.builtins.hooks.if_hook.logger')
    def test_task_instance_started_filter_condition_skip(self, mock_logger, mock_task, mock_host, mock_filters_catalog):
        """Test task_instance_started sets skip flag when filter condition fails."""
        hook = IfHook({"platform": "ios"})
        
        mock_filter_func = MagicMock(return_value=False)
        mock_filters_catalog["platform"] = (mock_filter_func, ["value"])
        
        hook._current_context = {"filters_catalog": mock_filters_catalog}

        hook.task_instance_started(mock_task, mock_host)

        assert mock_host.data['nornflow_skip_flag'] is True
        mock_filter_func.assert_called_once_with(mock_host, value="ios")

    @patch('nornflow.builtins.hooks.if_hook.logger')
    def test_task_instance_started_filter_condition_continue(self, mock_logger, mock_task, mock_host, mock_filters_catalog):
        """Test task_instance_started doesn't set skip flag when filter condition passes."""
        hook = IfHook({"platform": "ios"})
        
        mock_filter_func = MagicMock(return_value=True)
        mock_filters_catalog["platform"] = (mock_filter_func, ["value"])
        
        hook._current_context = {"filters_catalog": mock_filters_catalog}

        hook.task_instance_started(mock_task, mock_host)

        assert 'nornflow_skip_flag' not in mock_host.data
        mock_filter_func.assert_called_once_with(mock_host, value="ios")

    def test_task_instance_started_filter_missing_catalog_raises_error(self, mock_task, mock_host):
        """Test task_instance_started raises error when filters_catalog is missing."""
        hook = IfHook({"platform": "ios"})
        
        hook._current_context = {}

        with pytest.raises(HookValidationError, match="Failed to evaluate condition"):
            hook.task_instance_started(mock_task, mock_host)

    def test_task_instance_started_filter_unknown_filter_raises_error(self, mock_task, mock_host, mock_filters_catalog):
        """Test task_instance_started raises error when filter is not in catalog."""
        hook = IfHook({"unknown_filter": "value"})
        
        mock_filters_catalog["platform"] = (MagicMock(), ["value"])
        hook._current_context = {"filters_catalog": mock_filters_catalog}

        with pytest.raises(HookValidationError, match="Filter 'unknown_filter' not found"):
            hook.task_instance_started(mock_task, mock_host)

    @patch('nornflow.builtins.hooks.if_hook.logger')
    def test_task_instance_started_jinja_condition_skip(self, mock_logger, mock_task, mock_host, mock_vars_manager, mock_device_context):
        """Test task_instance_started sets skip flag when Jinja2 condition evaluates to False."""
        hook = IfHook("{{ host.platform == 'ios' }}")
        
        with patch.object(hook, 'get_resolved_value', return_value=False):
            hook.task_instance_started(mock_task, mock_host)
            
            assert mock_host.data['nornflow_skip_flag'] is True

    @patch('nornflow.builtins.hooks.if_hook.logger')
    def test_task_instance_started_jinja_condition_continue(self, mock_logger, mock_task, mock_host, mock_vars_manager, mock_device_context):
        """Test task_instance_started doesn't set skip flag when Jinja2 condition evaluates to True."""
        hook = IfHook("{{ host.platform == 'ios' }}")
        
        with patch.object(hook, 'get_resolved_value', return_value=True):
            hook.task_instance_started(mock_task, mock_host)
            
            assert 'nornflow_skip_flag' not in mock_host.data

    def test_task_instance_started_jinja_missing_vars_manager_raises_error(self, mock_task, mock_host):
        """Test task_instance_started raises error when vars_manager is missing."""
        hook = IfHook("{{ true }}")
        
        hook._current_context = {}

        with patch.object(hook, 'get_resolved_value', side_effect=Exception("vars_manager not available")):
            with pytest.raises(HookValidationError, match="Failed to evaluate condition.*vars_manager not available"):
                hook.task_instance_started(mock_task, mock_host)

    def test_task_instance_started_jinja_invalid_expression_raises_error(self, mock_task, mock_host, mock_vars_manager, mock_device_context):
        """Test task_instance_started handles non-boolean Jinja2 expression results."""
        hook = IfHook("{{ not_boolean }}")
        
        with patch.object(hook, 'get_resolved_value', return_value=True):
            hook.task_instance_started(mock_task, mock_host)
            
            assert 'nornflow_skip_flag' not in mock_host.data

    def test_skip_if_condition_flagged_decorator_skip(self):
        """Test skip_if_condition_flagged decorator returns skipped result when flag is set."""
        from nornflow.builtins.hooks.if_hook import skip_if_condition_flagged
        
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_nornir = MagicMock()
        mock_nornir.processors = []
        
        mock_task.host = mock_host
        mock_task.nornir = mock_nornir
        mock_host.data = {'nornflow_skip_flag': True}
        
        @skip_if_condition_flagged
        def dummy_task(task):
            return Result(host=task.host, result="should not run")
        
        result = dummy_task(mock_task)
        
        assert result.skipped is True
        assert result.result is None
        assert result.changed is False
        assert result.failed is False
        assert 'nornflow_skip_flag' not in mock_host.data

    def test_skip_if_condition_flagged_decorator_continue(self):
        """Test skip_if_condition_flagged decorator executes task when flag is not set."""
        from nornflow.builtins.hooks.if_hook import skip_if_condition_flagged
        
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_nornir = MagicMock()
        mock_nornir.processors = []
        
        mock_task.host = mock_host
        mock_task.nornir = mock_nornir
        mock_host.data = {}
        
        @skip_if_condition_flagged
        def dummy_task(task):
            return Result(host=task.host, result="executed")
        
        result = dummy_task(mock_task)
        
        assert result.result == "executed"

    def test_skip_if_condition_flagged_decorator_with_deferred_params(self):
        """Test skip_if_condition_flagged decorator resolves deferred params when processor available."""
        from nornflow.builtins.hooks.if_hook import skip_if_condition_flagged
        
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_processor = MagicMock()
        mock_nornir = MagicMock()
        
        mock_processor.resolve_deferred_params.return_value = {"resolved": "param"}
        mock_nornir.processors = [mock_processor]
        
        mock_task.host = mock_host
        mock_task.nornir = mock_nornir
        mock_host.data = {}
        
        @skip_if_condition_flagged
        def dummy_task(task, **kwargs):
            return Result(host=task.host, result=kwargs)
        
        result = dummy_task(mock_task)
        
        assert result.result == {"resolved": "param"}
        mock_processor.resolve_deferred_params.assert_called_once_with(mock_task, mock_host)

    def test_skip_if_condition_flagged_decorator_immediate_mode(self):
        """Test skip_if_condition_flagged decorator uses kwargs when no deferred params."""
        from nornflow.builtins.hooks.if_hook import skip_if_condition_flagged
        
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_processor = MagicMock()
        mock_nornir = MagicMock()
        
        mock_processor.resolve_deferred_params.return_value = None  # No deferred params
        mock_nornir.processors = [mock_processor]
        
        mock_task.host = mock_host
        mock_task.nornir = mock_nornir
        mock_host.data = {}
        
        @skip_if_condition_flagged
        def dummy_task(task, **kwargs):
            return Result(host=task.host, result=kwargs)
        
        result = dummy_task(mock_task, original="param")
        
        assert result.result == {"original": "param"}
        mock_processor.resolve_deferred_params.assert_called_once_with(mock_task, mock_host)

    def test_skip_if_condition_flagged_decorator_with_empty_deferred_params(self):
        """Test skip_if_condition_flagged decorator uses empty dict when deferred params resolve to empty."""
        from nornflow.builtins.hooks.if_hook import skip_if_condition_flagged
        
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_processor = MagicMock()
        mock_nornir = MagicMock()
        
        mock_processor.resolve_deferred_params.return_value = {}  # Empty deferred params
        mock_nornir.processors = [mock_processor]
        
        mock_task.host = mock_host
        mock_task.nornir = mock_nornir
        mock_host.data = {}
        
        @skip_if_condition_flagged
        def dummy_task(task, **kwargs):
            return Result(host=task.host, result=kwargs)
        
        result = dummy_task(mock_task, original="param")
        
        assert result.result == {}  # Should use empty dict, not kwargs
        mock_processor.resolve_deferred_params.assert_called_once_with(mock_task, mock_host)

    def test_should_execute_always_returns_true(self):
        """Test that hook executes for every host (run_once_per_task=False)."""
        hook = IfHook("{{ true }}")
        mock_task = MagicMock()

        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True

    def test_context_property_returns_empty_when_no_context(self):
        """Test context property returns empty dict when no context is set."""
        hook = IfHook("{{ true }}")
        
        context = hook.context
        assert context == {}

    def test_other_processor_methods_do_nothing(self):
        """Test that other processor methods have no implementation."""
        hook = IfHook("{{ true }}")
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()

        hook.task_completed(mock_task, mock_result)
        hook.task_instance_completed(mock_task, mock_host, mock_result)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)