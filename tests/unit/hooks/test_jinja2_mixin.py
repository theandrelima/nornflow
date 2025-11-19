from unittest.mock import MagicMock

import pytest
from nornir.core.inventory import Host
from nornir.core.task import Task

from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookError, HookValidationError


class Jinja2MixinTestHook(Hook, Jinja2ResolvableMixin):
    """Test hook combining base Hook with Jinja2ResolvableMixin."""
    hook_name = "jinja2_mixin_test_hook"
    run_once_per_task = False


class TestJinja2ResolvableMixinValidation:
    """Test suite for Jinja2ResolvableMixin validation logic."""

    def test_validate_string_with_double_brace_markers_passes(self):
        """Test validation passes for string with {{ }} markers."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_validate_string_with_percent_markers_passes(self):
        """Test validation passes for string with {% %} markers."""
        hook = Jinja2MixinTestHook("{% if condition %}text{% endif %}")
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_validate_string_with_comment_markers_passes(self):
        """Test validation passes for string with {# #} markers."""
        hook = Jinja2MixinTestHook("{# comment #}")
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_validate_string_with_mixed_markers_passes(self):
        """Test validation passes for string with multiple marker types."""
        hook = Jinja2MixinTestHook("{# comment #}{{ var }}{% if x %}y{% endif %}")
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_validate_boolean_value_skips_jinja2_validation(self):
        """Test validation skips Jinja2 check for boolean values."""
        hook = Jinja2MixinTestHook(True)
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_validate_none_value_skips_jinja2_validation(self):
        """Test validation skips Jinja2 check for None value."""
        hook = Jinja2MixinTestHook(None)
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_validate_dict_value_skips_jinja2_validation(self):
        """Test validation skips Jinja2 check for dict values."""
        hook = Jinja2MixinTestHook({"key": "value"})
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)


class TestJinja2ResolvableMixinIsJinja2Expression:
    """Test suite for _is_jinja2_expression method."""

    def test_string_with_double_braces_is_jinja2(self):
        """Test string with {{ }} is recognized as Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression("{{ var }}") is True

    def test_string_with_percent_braces_is_jinja2(self):
        """Test string with {% %} is recognized as Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression("{% if x %}{% endif %}") is True

    def test_string_with_comment_braces_is_jinja2(self):
        """Test string with {# #} is recognized as Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression("{# comment #}") is True

    def test_string_with_partial_markers_is_jinja2(self):
        """Test string with incomplete but present markers is recognized."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression("text {{ incomplete") is True

    def test_plain_string_is_not_jinja2(self):
        """Test plain string without markers is not Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression("plain text") is False

    def test_empty_string_is_not_jinja2(self):
        """Test empty string is not Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression("") is False

    def test_none_is_not_jinja2(self):
        """Test None is not Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression(None) is False

    def test_integer_is_not_jinja2(self):
        """Test integer is not Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression(123) is False

    def test_list_is_not_jinja2(self):
        """Test list is not Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression(["a", "b"]) is False

    def test_dict_is_not_jinja2(self):
        """Test dict is not Jinja2."""
        hook = Jinja2MixinTestHook(None)
        assert hook._is_jinja2_expression({"key": "value"}) is False


class TestJinja2ResolvableMixinToBool:
    """Test suite for _to_bool method."""

    def test_true_boolean_returns_true(self):
        """Test True boolean returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool(True) is True

    def test_false_boolean_returns_false(self):
        """Test False boolean returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool(False) is False

    def test_string_true_lowercase_returns_true(self):
        """Test 'true' string returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("true") is True

    def test_string_true_uppercase_returns_true(self):
        """Test 'TRUE' string returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("TRUE") is True

    def test_string_true_mixedcase_returns_true(self):
        """Test 'TrUe' string returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("TrUe") is True

    def test_string_yes_returns_true(self):
        """Test 'yes' string returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("yes") is True

    def test_string_y_returns_true(self):
        """Test 'y' string returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("y") is True

    def test_string_on_returns_true(self):
        """Test 'on' string returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("on") is True

    def test_string_1_returns_true(self):
        """Test '1' string returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("1") is True

    def test_string_false_returns_false(self):
        """Test 'false' string returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("false") is False

    def test_string_no_returns_false(self):
        """Test 'no' string returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("no") is False

    def test_string_n_returns_false(self):
        """Test 'n' string returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("n") is False

    def test_string_off_returns_false(self):
        """Test 'off' string returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("off") is False

    def test_string_0_returns_false(self):
        """Test '0' string returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("0") is False

    def test_string_random_text_returns_false(self):
        """Test random string returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("random") is False

    def test_integer_1_returns_true(self):
        """Test integer 1 returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool(1) is True

    def test_integer_0_returns_false(self):
        """Test integer 0 returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool(0) is False

    def test_integer_42_returns_true(self):
        """Test non-zero integer returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool(42) is True

    def test_empty_string_returns_false(self):
        """Test empty string returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool("") is False

    def test_none_returns_false(self):
        """Test None returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool(None) is False

    def test_empty_list_returns_false(self):
        """Test empty list returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool([]) is False

    def test_non_empty_list_returns_true(self):
        """Test non-empty list returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool([1, 2, 3]) is True

    def test_empty_dict_returns_false(self):
        """Test empty dict returns False."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool({}) is False

    def test_non_empty_dict_returns_true(self):
        """Test non-empty dict returns True."""
        hook = Jinja2MixinTestHook(None)
        assert hook._to_bool({"key": "value"}) is True


class TestJinja2ResolvableMixinExtractHost:
    """Test suite for _extract_host_from_task method."""

    def test_extract_host_from_task_with_hosts(self):
        """Test extracting host from task with populated inventory."""
        hook = Jinja2MixinTestHook(None)
        
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_task = MagicMock()
        mock_task.nornir.inventory.hosts = {"router1": mock_host}

        result = hook._extract_host_from_task(mock_task)
        
        assert result == mock_host

    def test_extract_host_from_task_with_empty_inventory_raises_error(self):
        """Test extracting host from task with empty inventory raises HookError."""
        hook = Jinja2MixinTestHook(None)
        
        mock_task = MagicMock()
        mock_task.nornir.inventory.hosts = {}

        with pytest.raises(HookError, match="Cannot extract host from task with empty inventory"):
            hook._extract_host_from_task(mock_task)

    def test_extract_host_returns_first_host_when_multiple(self):
        """Test that first host is returned when multiple hosts exist."""
        hook = Jinja2MixinTestHook(None)
        
        mock_host1 = MagicMock(spec=Host)
        mock_host1.name = "router1"
        mock_host2 = MagicMock(spec=Host)
        mock_host2.name = "router2"
        
        mock_task = MagicMock()
        mock_task.nornir.inventory.hosts = {"router1": mock_host1, "router2": mock_host2}

        result = hook._extract_host_from_task(mock_task)
        
        assert result in [mock_host1, mock_host2]


class TestJinja2ResolvableMixinResolveJinja2:
    """Test suite for _resolve_jinja2 method."""

    def test_resolve_jinja2_with_vars_manager(self):
        """Test Jinja2 resolution when vars_manager is available."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_device_context = MagicMock()
        mock_device_context.resolve_value.return_value = "resolved_value"
        
        mock_vars_manager = MagicMock()
        mock_vars_manager.get_device_context.return_value = mock_device_context
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        result = hook._resolve_jinja2("{{ variable }}", mock_host)
        
        assert result == "resolved_value"
        mock_vars_manager.get_device_context.assert_called_once_with("router1")
        mock_device_context.resolve_value.assert_called_once_with("{{ variable }}")

    def test_resolve_jinja2_without_vars_manager_raises_error(self):
        """Test Jinja2 resolution raises HookError when vars_manager is missing."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        hook._current_context = {}

        with pytest.raises(HookError, match="vars_manager not available in hook context"):
            hook._resolve_jinja2("{{ variable }}", mock_host)

    def test_resolve_jinja2_with_none_context_raises_error(self):
        """Test Jinja2 resolution raises HookError when context is None."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        hook._current_context = None

        with pytest.raises(HookError, match="vars_manager not available in hook context"):
            hook._resolve_jinja2("{{ variable }}", mock_host)


class TestJinja2ResolvableMixinGetResolvedValue:
    """Test suite for get_resolved_value method."""

    def test_get_resolved_value_returns_default_when_value_is_none(self):
        """Test returns default when hook value is None."""
        hook = Jinja2MixinTestHook(None)
        mock_task = MagicMock()

        result = hook.get_resolved_value(mock_task, default="default_value")
        
        assert result == "default_value"

    def test_get_resolved_value_returns_default_when_value_is_empty_string(self):
        """Test returns default when hook value is empty string."""
        hook = Jinja2MixinTestHook("")
        mock_task = MagicMock()

        result = hook.get_resolved_value(mock_task, default="default_value")
        
        assert result == "default_value"

    def test_get_resolved_value_returns_default_when_value_is_false(self):
        """Test returns default when hook value is False."""
        hook = Jinja2MixinTestHook(False)
        mock_task = MagicMock()

        result = hook.get_resolved_value(mock_task, default="default_value")
        
        assert result == "default_value"

    def test_get_resolved_value_returns_static_value_when_not_jinja2(self):
        """Test returns static value when value is not Jinja2."""
        hook = Jinja2MixinTestHook(True)
        mock_task = MagicMock()

        result = hook.get_resolved_value(mock_task)
        
        assert result is True

    def test_get_resolved_value_resolves_jinja2_with_provided_host(self):
        """Test resolves Jinja2 when host is provided."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_task = MagicMock()
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_device_context = MagicMock()
        mock_device_context.resolve_value.return_value = "resolved"
        
        mock_vars_manager = MagicMock()
        mock_vars_manager.get_device_context.return_value = mock_device_context
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        result = hook.get_resolved_value(mock_task, host=mock_host)
        
        assert result == "resolved"

    def test_get_resolved_value_extracts_host_when_not_provided(self):
        """Test extracts host from task when host not provided."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_task = MagicMock()
        mock_task.nornir.inventory.hosts = {"router1": mock_host}
        
        mock_device_context = MagicMock()
        mock_device_context.resolve_value.return_value = "resolved"
        
        mock_vars_manager = MagicMock()
        mock_vars_manager.get_device_context.return_value = mock_device_context
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        result = hook.get_resolved_value(mock_task)
        
        assert result == "resolved"

    def test_get_resolved_value_converts_to_bool_when_requested(self):
        """Test converts result to boolean when as_bool=True."""
        hook = Jinja2MixinTestHook("{{ variable }}")
        
        mock_task = MagicMock()
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        mock_device_context = MagicMock()
        mock_device_context.resolve_value.return_value = "yes"
        
        mock_vars_manager = MagicMock()
        mock_vars_manager.get_device_context.return_value = mock_device_context
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        result = hook.get_resolved_value(mock_task, host=mock_host, as_bool=True)
        
        assert result is True

    def test_get_resolved_value_bool_conversion_on_static_value(self):
        """Test converts static value to boolean when as_bool=True."""
        hook = Jinja2MixinTestHook("yes")
        mock_task = MagicMock()

        result = hook.get_resolved_value(mock_task, as_bool=True)
        
        assert result is True