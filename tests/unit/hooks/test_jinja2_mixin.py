from unittest.mock import MagicMock

import pytest
from nornir.core.inventory import Host

from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookError


class Jinja2MixinTestHook(Hook, Jinja2ResolvableMixin):
    """Helper hook class for testing Jinja2ResolvableMixin."""
    hook_name = "jinja2_mixin_test_hook"


class TestJinja2ResolvableMixin:
    """Test suite for Jinja2ResolvableMixin."""

    def test_is_jinja2_expression_true(self):
        """Test _is_jinja2_expression returns True for strings with markers."""
        hook = Jinja2MixinTestHook("{{ var }}")
        assert hook._is_jinja2_expression("{{ var }}") is True
        assert hook._is_jinja2_expression("{% if x %}y{% endif %}") is True

    def test_is_jinja2_expression_false(self):
        """Test _is_jinja2_expression returns False for plain strings."""
        hook = Jinja2MixinTestHook("plain string")
        assert hook._is_jinja2_expression("plain string") is False
        assert hook._is_jinja2_expression(123) is False
        assert hook._is_jinja2_expression(None) is False

    def test_to_bool_conversion(self):
        """Test _to_bool conversion logic."""
        hook = Jinja2MixinTestHook()
        
        # Boolean inputs
        assert hook._to_bool(True) is True
        assert hook._to_bool(False) is False
        
        # String inputs (truthy)
        assert hook._to_bool("yes") is True
        assert hook._to_bool("true") is True
        assert hook._to_bool("on") is True
        assert hook._to_bool("1") is True
        
        # String inputs (falsy)
        assert hook._to_bool("no") is False
        assert hook._to_bool("false") is False
        assert hook._to_bool("off") is False
        assert hook._to_bool("0") is False
        assert hook._to_bool("random") is False
        
        # Other inputs
        assert hook._to_bool(1) is True
        assert hook._to_bool(0) is False

    def test_validate_jinja2_string_valid(self):
        """Test validation passes for valid Jinja2 string."""
        hook = Jinja2MixinTestHook("{{ var }}")
        mock_task_model = MagicMock()
        
        # Should not raise
        hook.execute_hook_validations(mock_task_model)

    def test_extract_host_from_task_success(self):
        """Test extracting host from task inventory."""
        hook = Jinja2MixinTestHook()
        mock_task = MagicMock()
        mock_host = MagicMock(spec=Host)
        mock_task.nornir.inventory.hosts = {"host1": mock_host}
        
        result = hook._extract_host_from_task(mock_task)
        assert result == mock_host

    def test_extract_host_from_task_empty_inventory(self):
        """Test extracting host raises error when inventory is empty."""
        hook = Jinja2MixinTestHook()
        mock_task = MagicMock()
        mock_task.nornir.inventory.hosts = {}
        
        with pytest.raises(HookError, match="Cannot extract host from task with empty inventory"):
            hook._extract_host_from_task(mock_task)

    def test_resolve_jinja2_with_vars_manager(self):
        """Test Jinja2 resolution when vars_manager is available."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_vars_manager = MagicMock()
        # FIX: Mock resolve_string, not device_context.resolve_value
        mock_vars_manager.resolve_string.return_value = "resolved_value"
        
        hook._current_context = {"vars_manager": mock_vars_manager}
        
        result = hook._resolve_jinja2("{{ variable }}", mock_host)
        
        assert result == "resolved_value"
        mock_vars_manager.resolve_string.assert_called_with("{{ variable }}", "router1")

    def test_resolve_jinja2_without_vars_manager_raises_error(self):
        """Test Jinja2 resolution raises HookError when vars_manager is missing."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        mock_host = MagicMock(spec=Host)
        hook._current_context = {}
        
        # FIX: Update regex to match actual error message
        with pytest.raises(HookError, match="Variables manager not available in context"):
            hook._resolve_jinja2("{{ variable }}", mock_host)

    def test_resolve_jinja2_with_none_context_raises_error(self):
        """Test Jinja2 resolution raises HookError when context is None."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        mock_host = MagicMock(spec=Host)
        hook._current_context = None
        
        # FIX: Update regex to match actual error message
        with pytest.raises(HookError, match="Variables manager not available in context"):
            hook._resolve_jinja2("{{ variable }}", mock_host)

    def test_get_resolved_value_resolves_jinja2_with_provided_host(self):
        """Test resolves Jinja2 when host is provided."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_task = MagicMock()
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_vars_manager = MagicMock()
        # FIX: Mock resolve_string
        mock_vars_manager.resolve_string.return_value = "resolved"
        
        hook._current_context = {"vars_manager": mock_vars_manager}
        
        result = hook.get_resolved_value(mock_task, host=mock_host)
        
        assert result == "resolved"
        mock_vars_manager.resolve_string.assert_called_with("{{ variable }}", "router1")

    def test_get_resolved_value_extracts_host_when_not_provided(self):
        """Test extracts host from task when host not provided."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_task = MagicMock()
        mock_task.nornir.inventory.hosts = {"router1": mock_host}
        
        mock_vars_manager = MagicMock()
        # FIX: Mock resolve_string
        mock_vars_manager.resolve_string.return_value = "resolved"
        
        hook._current_context = {"vars_manager": mock_vars_manager}
        
        result = hook.get_resolved_value(mock_task)
        
        assert result == "resolved"
        mock_vars_manager.resolve_string.assert_called_with("{{ variable }}", "router1")

    def test_get_resolved_value_returns_default_when_empty(self):
        """Test returns default value when hook value is empty."""
        hook = Jinja2MixinTestHook(None)
        mock_task = MagicMock()
        
        result = hook.get_resolved_value(mock_task, default="default")
        assert result == "default"

    def test_get_resolved_value_returns_raw_value_when_not_jinja(self):
        """Test returns raw value when not a Jinja2 expression."""
        hook = Jinja2MixinTestHook("raw_value")
        mock_task = MagicMock()
        
        result = hook.get_resolved_value(mock_task)
        assert result == "raw_value"

    def test_get_resolved_value_as_bool(self):
        """Test returns boolean converted value."""
        hook = Jinja2MixinTestHook("yes")
        mock_task = MagicMock()
        
        result = hook.get_resolved_value(mock_task, as_bool=True)
        assert result is True

    def test_get_resolved_value_jinja_as_bool(self):
        """Test returns boolean converted resolved Jinja2 value."""
        hook = Jinja2MixinTestHook("{{ var }}")
        mock_task = MagicMock()
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_vars_manager = MagicMock()
        mock_vars_manager.resolve_string.return_value = "false"
        
        hook._current_context = {"vars_manager": mock_vars_manager}
        
        result = hook.get_resolved_value(mock_task, host=mock_host, as_bool=True)
        assert result is False
