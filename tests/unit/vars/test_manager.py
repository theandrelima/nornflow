import os
from pathlib import Path
from unittest.mock import patch

import pytest

from nornflow.vars.exceptions import VariableError
from nornflow.vars.manager import NornFlowVariablesManager


class TestVariableManager:
    def test_init_with_valid_dir(self, vars_dir):
        """Test initializing the manager with a valid vars directory."""
        manager = NornFlowVariablesManager(vars_dir=str(vars_dir))
        assert manager.vars_dir == Path(vars_dir)

    def test_init_with_invalid_dir(self, tmp_path):
        """Test initializing with a path that exists but isn't a directory."""
        invalid_path = tmp_path / "not_a_dir"
        invalid_path.write_text("not a directory")

        with pytest.raises(VariableError):
            NornFlowVariablesManager(vars_dir=str(invalid_path))

    def test_environment_variables_loading(self, tmp_path):
        """Test loading environment variables with NORNFLOW_VAR_ prefix."""
        with patch.dict(os.environ, {"NORNFLOW_VAR_test": "env_value"}):
            temp_vars_dir = tmp_path / "temp_vars"
            temp_vars_dir.mkdir()
            manager = NornFlowVariablesManager(vars_dir=str(temp_vars_dir))
            env_vars = manager._load_environment_variables()
            assert "test" in env_vars
            assert env_vars["test"] == "env_value"

    def test_domain_extraction_from_path(self, workflows_dir, tmp_path):
        """Test extracting domain from workflow path."""
        workflow_path = Path(workflows_dir / "networking" / "config.yaml")

        temp_vars_dir = tmp_path / "temp_vars"
        temp_vars_dir.mkdir()
        manager = NornFlowVariablesManager(vars_dir=str(temp_vars_dir), workflow_roots=[str(workflows_dir)])
        domain = manager._extract_domain_from_path(workflow_path)
        assert domain == "networking"

    def test_get_device_context_creates_new(self, basic_manager):
        """Test that get_device_context creates a new context if none exists."""
        ctx = basic_manager.get_device_context("device1")
        assert ctx.host_name == "device1"

    def test_set_runtime_variable(self, basic_manager):
        """Test setting a runtime variable for a host."""
        basic_manager.set_runtime_variable("test_var", "test_value", "device1")

        ctx = basic_manager.get_device_context("device1")
        assert "test_var" in ctx.runtime_vars
        assert ctx.runtime_vars["test_var"] == "test_value"

    def test_get_nornflow_variable_precedence(self, setup_manager):
        """Test variable precedence when getting a variable."""
        # Test precedence
        assert setup_manager.get_nornflow_variable("override_var", "test_device") == "runtime_value"
        assert setup_manager.get_nornflow_variable("workflow_var", "test_device") == "workflow_value"
        assert setup_manager.get_nornflow_variable("domain_var", "test_device") == "domain_value"
        assert setup_manager.get_nornflow_variable("global_var", "test_device") == "global_value"

    def test_jinja2_manager_initialized(self, basic_manager):
        """Test that Jinja2EnvironmentManager is properly initialized."""
        assert basic_manager._jinja2_manager is not None
        assert basic_manager._jinja2_manager.env is not None

    def test_jinja2_environment_accessible(self, basic_manager):
        """Test that Jinja2 environment is accessible through the manager."""
        env = basic_manager._jinja2_manager.env
        assert env is not None
        assert hasattr(env, 'filters')

    def test_custom_filters_registered(self, basic_manager):
        """Test that NornFlow custom filters are registered in Jinja2 environment."""
        env = basic_manager._jinja2_manager.env
        assert "is_set" in env.filters
        assert "flatten_list" in env.filters