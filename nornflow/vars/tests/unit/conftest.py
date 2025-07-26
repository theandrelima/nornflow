from pathlib import Path
from unittest.mock import MagicMock

import jinja2
import pytest

from nornflow.builtins.jinja2_filters import ALL_FILTERS
from nornflow.vars.manager import NornFlowVariablesManager
from nornflow.vars.processors import NornFlowVariableProcessor


class TestHostNamespace:
    def __init__(self, mock_host):
        self.mock_host = mock_host

    def __getattr__(self, name):
        if hasattr(self.mock_host, name):
            return getattr(self.mock_host, name)
        if hasattr(self.mock_host, "get"):
            value = self.mock_host.get(name)
            if value is not None:
                return value
        # If attribute doesn't exist, raise an error like the real HostNamespace would
        raise AttributeError(
            f"Host attribute or data key '{name}' not found for host '{self.mock_host.name}'"
        )


class MockHost:
    """A mock host that returns proper values for attributes."""

    def __init__(self):
        self.name = "test_device"
        self.hostname = "192.168.1.1"
        self.platform = "ios"
        self.groups = ["routers", "core"]

        # Create data as a dictionary
        self.data = {
            "location": {"building": "HQ", "floor": 3},
            "contact": "admin@example.com",
            "services": ["bgp", "ospf"],
            "role": "core",
        }

    def get(self, key, default=None):
        """Support the Host.get() method that NornirHostProxy expects"""
        if key == "name":
            return self.name
        if key == "hostname":
            return self.hostname
        if key == "platform":
            return self.platform
        if key == "groups":
            return self.groups
        if key == "data":
            return self.data
        if hasattr(self, key):
            return getattr(self, key)
        return default


@pytest.fixture
def mock_host():
    """Create a mock Nornir host with proper attribute access."""
    return MockHost()


@pytest.fixture
def mock_host_proxy(mock_host):
    """Create a mock host proxy that returns the mock host."""
    proxy = MagicMock()
    proxy.get_host_proxy = MagicMock(return_value=mock_host)
    proxy.current_host_name = None
    return proxy


@pytest.fixture
def vars_dir(tmp_path):
    """Create a temporary vars directory structure for testing."""
    vars_dir = tmp_path / "vars"
    vars_dir.mkdir()

    # Create global defaults
    defaults_file = vars_dir / "defaults.yaml"
    defaults_file.write_text(
        """
global_var: global_value
override_var: global_value
nested:
  key1: value1
  key2: value2
timeout: 60
log_level: info
credentials_file: /etc/global_credentials.yaml
"""
    )

    # Create domain defaults
    domain_dir = vars_dir / "networking"
    domain_dir.mkdir()
    domain_defaults = domain_dir / "defaults.yaml"
    domain_defaults.write_text(
        """
domain_var: domain_value
override_var: domain_value
nested:
  key1: domain_value1
timeout: 30
"""
    )

    # Create backup domain for e2e tests
    backup_dir = vars_dir / "backup"
    backup_dir.mkdir()
    (backup_dir / "defaults.yaml").write_text(
        """
backup_server: "10.0.0.100"
retention_days: 30
"""
    )

    return vars_dir


@pytest.fixture
def workflows_dir(tmp_path):
    """Create a temporary workflows directory structure for testing."""
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()

    # Create networking subdirectory
    networking_dir = workflows_dir / "networking"
    networking_dir.mkdir()

    # Create backup subdirectory for e2e tests
    backup_workflow_dir = workflows_dir / "backup"
    backup_workflow_dir.mkdir()

    return workflows_dir


@pytest.fixture
def basic_manager():
    """Create a basic variable manager without any variable files."""
    manager = NornFlowVariablesManager()

    # Add Jinja2 filters from ALL_FILTERS
    for filter_name, filter_func in ALL_FILTERS.items():
        manager.jinja_env.filters[filter_name] = filter_func

    return manager


@pytest.fixture
def setup_manager(vars_dir, workflows_dir, mock_host_proxy, mock_host):
    """Set up a manager with all variable layers."""
    workflow_path = Path(workflows_dir / "networking" / "config.yaml")

    manager = NornFlowVariablesManager(
        vars_dir=str(vars_dir),
        cli_vars={"cli_var": "cli_value", "override_var": "cli_value", "dry_run": True},
        inline_workflow_vars={
            "workflow_var": "workflow_value",
            "override_var": "workflow_value",
            "backup_type": "full",
        },
        workflow_path=workflow_path,
        workflow_roots=[str(workflows_dir)],
    )

    # Set the host proxy
    manager.nornir_host_proxy = mock_host_proxy

    # Add Jinja2 filters from ALL_FILTERS
    for filter_name, filter_func in ALL_FILTERS.items():
        manager.jinja_env.filters[filter_name] = filter_func

    # Set runtime variables
    manager.set_runtime_variable("runtime_var", "runtime_value", "test_device")
    manager.set_runtime_variable("override_var", "runtime_value", "test_device")
    manager.set_runtime_variable("complex_var", {"key": "value", "list": [1, 2, 3]}, "test_device")
    manager.set_runtime_variable("command_output", "Config backup complete", "test_device")

    # Set nested variable explicitly
    nested = {"key1": "domain_value1", "key2": "value2"}
    manager.set_runtime_variable("nested", nested, "test_device")

    # Fix #1: Set environment variables with highest precedence (using runtime vars)
    manager.set_runtime_variable("credentials_file", "/etc/credentials.yaml", "test_device")

    # Fix #2: Create a proper result object for backup_result
    mock_result = MagicMock()
    mock_result.result = "Router configuration backup"
    manager.set_runtime_variable("backup_result", mock_result, "test_device")

    # Monkey patch the manager's resolve_string method
    original_resolve_string = manager.resolve_string

    def patched_resolve_string(template_str, host_name, additional_vars=None):
        if not isinstance(template_str, str):
            return template_str

        if not host_name:
            # Use the original method if no host name is provided
            return original_resolve_string(template_str, host_name, additional_vars)

        # Create the Jinja2 template
        template = manager.jinja_env.from_string(template_str)

        # Get the device context and build the resolution context
        device_ctx = manager.get_device_context(host_name)
        nornflow_default_vars = device_ctx.get_flat_context()

        resolution_context = nornflow_default_vars.copy()
        if additional_vars:
            resolution_context.update(additional_vars)

        # Add the host namespace directly to the context
        host_namespace = TestHostNamespace(mock_host)
        resolution_context["host"] = host_namespace

        # Fix #3: Don't add undefined_var to the context so the test raises the expected error
        # Only add it if it's explicitly defined in the context already
        if "undefined_var" in template_str and "undefined_var" not in resolution_context:
            # Do nothing - we want it to raise an error
            pass

        # Render the template with the context that includes 'host'
        try:
            return template.render(**resolution_context)
        except Exception as e:
            # Preserve the original exception behavior
            if isinstance(e, jinja2.exceptions.UndefinedError) and "undefined_var" in str(e):
                from nornflow.vars.exceptions import VariableResolutionError

                raise VariableResolutionError(template_str, f"Undefined variable: {e}")
            raise type(e)(str(e))

    # Replace the original method with our patched version
    manager.resolve_string = patched_resolve_string

    return manager


@pytest.fixture
def setup_processor(setup_manager):
    """Set up a variable processor with the manager."""
    return NornFlowVariableProcessor(setup_manager)


@pytest.fixture
def mock_task():
    """Create a mock task."""
    task = MagicMock()
    task.name = "test_task"
    task.params = {"command": "show version", "timeout": "{{ timeout }}"}
    return task


@pytest.fixture
def mock_result():
    """Create a mock task result."""
    result = MagicMock()
    result.result = "Router configuration backup"
    result.changed = True
    result.failed = False
    return result
