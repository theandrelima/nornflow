import pytest
from unittest.mock import MagicMock

from nornflow.vars.exceptions import VariableResolutionError


class TestVariableResolution:
    def test_resolve_string_simple(self, setup_manager):
        """Test resolving a simple string template."""
        result = setup_manager.resolve_string("Value: {{ global_var }}", "test_device")
        assert result == "Value: global_value"
    
    def test_resolve_string_with_host(self, setup_manager, mock_host_proxy):
        """Test resolving a string with host attributes."""
        result = setup_manager.resolve_string("Host {{ host.name }} at {{ host.hostname }}", "test_device")
        assert result == "Host test_device at 192.168.1.1"
    
    def test_resolve_string_with_complex_var(self, setup_manager):
        """Test resolving a string with complex variable access."""
        result = setup_manager.resolve_string("{{ complex_var.key }} and {{ complex_var.list[1] }}", "test_device")
        assert result == "value and 2"
    
    def test_resolve_string_with_nested_dict(self, setup_manager):
        """Test resolving a string with nested dictionary access."""
        result = setup_manager.resolve_string("{{ nested.key1 }} and {{ nested.key2 }}", "test_device")
        assert result == "domain_value1 and value2"
    
    def test_resolve_string_with_jinja_logic(self, setup_manager):
        """Test resolving a string with Jinja2 logic."""
        template = """
        {% if global_var == 'global_value' %}
        Correct global value
        {% else %}
        Wrong global value
        {% endif %}
        """
        result = setup_manager.resolve_string(template, "test_device")
        assert "Correct global value" in result
    
    def test_resolve_string_undefined_var(self, setup_manager):
        """Test resolving a string with undefined variable raises error."""
        with pytest.raises(VariableResolutionError):
            setup_manager.resolve_string("{{ undefined_var }}", "test_device")
    
    def test_resolve_data_dict(self, setup_manager):
        """Test resolving a dictionary with templates."""
        data = {
            "key1": "{{ global_var }}",
            "key2": "{{ workflow_var }}",
            "nested": {
                "subkey": "{{ runtime_var }}"
            }
        }
        result = setup_manager.resolve_data(data, "test_device")
        assert result["key1"] == "global_value"
        assert result["key2"] == "workflow_value"
        assert result["nested"]["subkey"] == "runtime_value"
    
    def test_resolve_data_list(self, setup_manager):
        """Test resolving a list with templates."""
        data = ["{{ global_var }}", "{{ workflow_var }}", "{{ runtime_var }}"]
        result = setup_manager.resolve_data(data, "test_device")
        assert result == ["global_value", "workflow_value", "runtime_value"]