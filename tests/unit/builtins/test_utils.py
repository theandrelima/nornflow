import json
from unittest.mock import MagicMock

import pytest

from nornflow.builtins.utils import (
    build_set_task_report,
    format_value_for_display,
    get_resolved_runtime_values,
    get_task_vars_manager,
)
from nornflow.exceptions import ProcessorError


class TestGetTaskVarsManager:
    """Test get_task_vars_manager function."""

    def test_finds_vars_manager_in_first_processor(self, mock_processor_with_vars_manager):
        """Test finding vars_manager in the first processor."""
        mock_task = MagicMock()
        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        result = get_task_vars_manager(mock_task)

        assert result is mock_processor_with_vars_manager.vars_manager

    def test_finds_vars_manager_in_second_processor(self, mock_processor_with_vars_manager):
        """Test finding vars_manager in a later processor."""
        mock_processor1 = MagicMock(spec=[])
        
        mock_task = MagicMock()
        mock_task.nornir.processors = [mock_processor1, mock_processor_with_vars_manager]

        result = get_task_vars_manager(mock_task)

        assert result is mock_processor_with_vars_manager.vars_manager

    def test_raises_exception_when_no_vars_manager_found(self):
        """Test raises ProcessorError when no processor has vars_manager."""
        mock_processor1 = MagicMock(spec=[])
        mock_processor2 = MagicMock(spec=[])

        mock_task = MagicMock()
        mock_task.nornir.processors = [mock_processor1, mock_processor2]

        with pytest.raises(ProcessorError, match="Could not find NornFlowVariableProcessor"):
            get_task_vars_manager(mock_task)

    def test_raises_exception_when_processors_list_empty(self):
        """Test raises ProcessorError when processors list is empty."""
        mock_task = MagicMock()
        mock_task.nornir.processors = []

        with pytest.raises(ProcessorError, match="Could not find NornFlowVariableProcessor"):
            get_task_vars_manager(mock_task)


class TestFormatValueForDisplay:
    """Test format_value_for_display function."""

    def test_format_string_value(self):
        """Test formatting a string value with quotes."""
        result = format_value_for_display("hello world")
        assert result == '"hello world"'

    def test_format_empty_string(self):
        """Test formatting an empty string."""
        result = format_value_for_display("")
        assert result == '""'

    def test_format_string_with_special_chars(self):
        """Test formatting a string with special characters."""
        result = format_value_for_display("hello\nworld\ttab")
        assert result == '"hello\nworld\ttab"'

    def test_format_dict_value(self):
        """Test formatting a dictionary as JSON."""
        input_dict = {"key1": "value1", "key2": 123}
        result = format_value_for_display(input_dict)
        
        expected = json.dumps(input_dict, indent=2, ensure_ascii=False)
        assert result == expected

    def test_format_nested_dict(self):
        """Test formatting a nested dictionary."""
        input_dict = {
            "outer": {
                "inner": "value",
                "number": 42
            }
        }
        result = format_value_for_display(input_dict)
        
        expected = json.dumps(input_dict, indent=2, ensure_ascii=False)
        assert result == expected

    def test_format_list_value(self):
        """Test formatting a list as JSON."""
        input_list = [1, 2, 3, "four"]
        result = format_value_for_display(input_list)
        
        expected = json.dumps(input_list, indent=2, ensure_ascii=False)
        assert result == expected

    def test_format_nested_list(self):
        """Test formatting a nested list."""
        input_list = [[1, 2], [3, 4], ["a", "b"]]
        result = format_value_for_display(input_list)
        
        expected = json.dumps(input_list, indent=2, ensure_ascii=False)
        assert result == expected

    def test_format_integer_value(self):
        """Test formatting an integer."""
        result = format_value_for_display(42)
        assert result == "42"

    def test_format_float_value(self):
        """Test formatting a float."""
        result = format_value_for_display(3.14159)
        assert result == "3.14159"

    def test_format_boolean_true(self):
        """Test formatting boolean True."""
        result = format_value_for_display(True)
        assert result == "True"

    def test_format_boolean_false(self):
        """Test formatting boolean False."""
        result = format_value_for_display(False)
        assert result == "False"

    def test_format_none_value(self):
        """Test formatting None."""
        result = format_value_for_display(None)
        assert result == "None"

    def test_format_non_serializable_object(self):
        """Test formatting a non-JSON-serializable object falls back to str()."""
        class CustomObject:
            def __str__(self):
                return "CustomObject instance"
        
        obj = CustomObject()
        result = format_value_for_display(obj)
        assert result == "CustomObject instance"

    def test_format_dict_with_non_serializable_value(self):
        """Test formatting a dict containing non-serializable values."""
        class NonSerializable:
            def __str__(self):
                return "NonSerializable"
        
        input_dict = {"key": NonSerializable()}
        result = format_value_for_display(input_dict)
        
        assert "NonSerializable" in result

    def test_format_empty_dict(self):
        """Test formatting an empty dictionary."""
        result = format_value_for_display({})
        assert result == "{}"

    def test_format_empty_list(self):
        """Test formatting an empty list."""
        result = format_value_for_display([])
        assert result == "[]"


class TestGetResolvedRuntimeValues:
    """Test get_resolved_runtime_values function."""

    def test_get_values_with_vars_manager(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test retrieving resolved runtime values when vars_manager exists."""
        mock_device_context.runtime_vars = {
            "var1": "value1",
            "var2": 123,
            "var3": {"nested": "dict"}
        }

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        result = get_resolved_runtime_values(mock_task, ["var1", "var2"])

        assert result == {"var1": "value1", "var2": 123}
        mock_processor_with_vars_manager.vars_manager.get_device_context.assert_called_once_with("test_host")

    def test_get_values_when_var_not_found(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test behavior when a requested variable is not in runtime_vars."""
        mock_device_context.runtime_vars = {"var1": "value1"}

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        result = get_resolved_runtime_values(mock_task, ["var1", "missing_var"])

        assert result == {
            "var1": "value1",
            "missing_var": "<value not found in runtime vars>"
        }

    def test_get_values_without_vars_manager(self):
        """Test raises ProcessorError when no vars_manager is found."""
        mock_processor = MagicMock(spec=[])

        mock_task = MagicMock()
        mock_task.host.name = "test_host"
        mock_task.nornir.processors = [mock_processor]

        with pytest.raises(ProcessorError, match="Could not find NornFlowVariableProcessor"):
            get_resolved_runtime_values(mock_task, ["var1", "var2"])

    def test_get_values_with_empty_var_names_list(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test with empty list of variable names."""
        mock_device_context.runtime_vars = {"var1": "value1"}

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        result = get_resolved_runtime_values(mock_task, [])

        assert result == {}

    def test_get_values_all_missing(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test when all requested variables are missing from runtime_vars."""
        mock_device_context.runtime_vars = {}

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        result = get_resolved_runtime_values(mock_task, ["var1", "var2"])

        assert result == {
            "var1": "<value not found in runtime vars>",
            "var2": "<value not found in runtime vars>"
        }


class TestBuildSetTaskReport:
    """Test build_set_task_report function."""

    def test_build_report_with_simple_values(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test building report with simple variable values."""
        mock_device_context.runtime_vars = {
            "var1": "value1",
            "var2": 123
        }

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        kwargs = {"var1": "{{ some_template }}", "var2": "{{ other_template }}"}

        result = build_set_task_report(mock_task, kwargs)

        assert "Set 2 variable(s) for host 'test_host':" in result
        assert '• var1 = "value1"' in result
        assert "• var2 = 123" in result

    def test_build_report_with_dict_value(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test building report with dictionary values."""
        mock_device_context.runtime_vars = {
            "config": {"interface": "eth0", "ip": "192.168.1.1"}
        }

        mock_task.host.name = "router1"
        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        kwargs = {"config": "{{ device_config }}"}

        result = build_set_task_report(mock_task, kwargs)

        assert "Set 1 variable(s) for host 'router1':" in result
        assert "• config =" in result
        assert '"interface": "eth0"' in result
        assert '"ip": "192.168.1.1"' in result

    def test_build_report_with_list_value(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test building report with list values."""
        mock_device_context.runtime_vars = {
            "interfaces": ["eth0", "eth1", "lo"]
        }

        mock_task.host.name = "switch1"
        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        kwargs = {"interfaces": "{{ device_interfaces }}"}

        result = build_set_task_report(mock_task, kwargs)

        assert "Set 1 variable(s) for host 'switch1':" in result
        assert "• interfaces =" in result
        assert '"eth0"' in result
        assert '"eth1"' in result

    def test_build_report_without_vars_manager(self):
        """Test raises ProcessorError when vars_manager is not available."""
        mock_processor = MagicMock(spec=[])

        mock_task = MagicMock()
        mock_task.host.name = "test_host"
        mock_task.nornir.processors = [mock_processor]

        kwargs = {
            "var1": "{{ template1 }}",
            "var2": {"key": "value"}
        }

        with pytest.raises(ProcessorError, match="Could not find NornFlowVariableProcessor"):
            build_set_task_report(mock_task, kwargs)

    def test_build_report_with_empty_kwargs(self):
        """Test building report with no variables to set."""
        mock_task = MagicMock()
        mock_task.host.name = "test_host"

        result = build_set_task_report(mock_task, {})

        assert result == "No variables were set (no arguments provided to 'set' task)"

    def test_build_report_with_none_kwargs(self):
        """Test building report with None as kwargs."""
        mock_task = MagicMock()
        mock_task.host.name = "test_host"

        result = build_set_task_report(mock_task, None)

        assert result == "No variables were set (no arguments provided to 'set' task)"

    def test_build_report_with_missing_variable(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test building report when variable is not found in runtime_vars."""
        mock_device_context.runtime_vars = {"var1": "value1"}

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        kwargs = {"var1": "template1", "missing_var": "template2"}

        result = build_set_task_report(mock_task, kwargs)

        assert "Set 2 variable(s) for host 'test_host':" in result
        assert '• var1 = "value1"' in result
        assert '• missing_var = "<value not found in runtime vars>"' in result

    def test_build_report_with_boolean_values(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test building report with boolean values."""
        mock_device_context.runtime_vars = {
            "enabled": True,
            "disabled": False
        }

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        kwargs = {"enabled": "{{ is_enabled }}", "disabled": "{{ is_disabled }}"}

        result = build_set_task_report(mock_task, kwargs)

        assert "• enabled = True" in result
        assert "• disabled = False" in result

    def test_build_report_with_none_value(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test building report with None value."""
        mock_device_context.runtime_vars = {"null_var": None}

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        kwargs = {"null_var": "{{ template }}"}

        result = build_set_task_report(mock_task, kwargs)

        assert "• null_var = None" in result

    def test_build_report_preserves_variable_order(self, mock_task, mock_processor_with_vars_manager, mock_device_context):
        """Test that report maintains the order of variables from kwargs."""
        mock_device_context.runtime_vars = {
            "var_c": "value_c",
            "var_a": "value_a",
            "var_b": "value_b"
        }

        mock_task.nornir.processors = [mock_processor_with_vars_manager]

        kwargs = {"var_c": "t1", "var_a": "t2", "var_b": "t3"}

        result = build_set_task_report(mock_task, kwargs)

        lines = result.split("\n")
        var_lines = [line for line in lines if "•" in line]
        
        assert "var_c" in var_lines[0]
        assert "var_a" in var_lines[1]
        assert "var_b" in var_lines[2]