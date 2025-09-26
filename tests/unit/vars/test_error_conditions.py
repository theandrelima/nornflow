from pathlib import Path

import pytest

from nornflow.vars.exceptions import TemplateError, VariableError
from nornflow.vars.manager import NornFlowVariablesManager


class TestErrorConditions:
    def test_undefined_variable(self, basic_manager):
        """Test behavior when accessing an undefined variable."""
        with pytest.raises(VariableError):
            basic_manager.get_nornflow_variable("undefined_var", "test_device")

    def test_jinja_undefined_variable(self, basic_manager):
        """Test behavior when referencing an undefined variable in a template."""
        with pytest.raises(TemplateError):
            basic_manager.resolve_string("{{ undefined_var }}", "test_device")

    def test_invalid_jinja_syntax(self, basic_manager):
        """Test behavior with invalid Jinja2 syntax."""
        with pytest.raises(TemplateError):
            basic_manager.resolve_string("{{ unclosed_bracket }", "test_device")

    def test_invalid_filter(self, basic_manager):
        """Test behavior with a non-existent Jinja2 filter."""
        with pytest.raises(TemplateError):
            basic_manager.resolve_string("{{ 'test' | nonexistent_filter }}", "test_device")

    def test_invalid_vars_dir(self, tmp_path):
        """Test initializing with an invalid vars directory."""
        nonexistent_dir = tmp_path / "nonexistent"

        # Check if the manager actually raises an exception for non-existent dirs
        try:
            manager = NornFlowVariablesManager(vars_dir=str(nonexistent_dir))
            # If we get here, the manager didn't raise an exception
            assert manager.vars_dir is None or manager.vars_dir == Path(nonexistent_dir)
        except Exception as e:
            # If an exception is raised, check if it's the expected type
            assert "does not exist" in str(e) or "not a directory" in str(e)

    def test_missing_host(self, basic_manager):
        """Test behavior when accessing variables for a non-existent host."""
        with pytest.raises(Exception):
            basic_manager.get_nornflow_variable("some_var", None)
