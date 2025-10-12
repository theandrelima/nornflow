from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nornflow.builtins.jinja2_filters import ALL_FILTERS
from nornflow.vars.manager import NornFlowVariablesManager
from nornflow.vars.processors import NornFlowVariableProcessor


class MockHost:
    """Minimal host model for variable-system unit tests."""

    def __init__(self) -> None:
        self.name = "test_device"
        self.hostname = "192.168.1.1"
        self.platform = "ios"
        self.groups = ["routers", "core"]
        self.data: dict[str, object] = {
            "location": {"building": "HQ", "floor": 3},
            "contact": "admin@example.com",
            "services": ["bgp", "ospf"],
            "role": "core",
        }

    def get(self, key: str, default: object | None = None) -> object | None:
        return getattr(self, key, default)


class _SimpleHostProxy:
    """
    Lightweight proxy that mimics the real Nornir host proxy.

    - Delegates attributes present on the wrapped ``MockHost``.  
    - Returns a fresh ``MagicMock`` for unknown attributes so templates can
      still use Jinja2 ``default`` safely.
    """

    def __init__(self, host: MockHost) -> None:
        self._host = host
        self.current_host_name: str | None = None

    def get_host_proxy(self, _host_name: str) -> "_SimpleHostProxy":
        return self

    def __getattr__(self, item: str) -> object:
        try:
            return getattr(self._host, item)
        except AttributeError:
            return MagicMock(name=item)


# --------------------------------------------------------------------------- fixtures
@pytest.fixture()
def mock_host() -> MockHost:
    return MockHost()


@pytest.fixture()
def mock_host_proxy(mock_host: MockHost) -> _SimpleHostProxy:
    return _SimpleHostProxy(mock_host)


@pytest.fixture()
def vars_dir(tmp_path) -> Path:
    vars_root = tmp_path / "vars"
    vars_root.mkdir()

    (vars_root / "defaults.yaml").write_text(
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

    networking = vars_root / "networking"
    networking.mkdir()
    (networking / "defaults.yaml").write_text(
        """
domain_var: domain_value
override_var: domain_value
nested:
  key1: domain_value1
  key2: value2
timeout: 30
"""
    )

    backup = vars_root / "backup"
    backup.mkdir()
    (backup / "defaults.yaml").write_text(
        """
backup_server: "10.0.0.100"
retention_days: 30
"""
    )

    return vars_root


@pytest.fixture()
def workflows_dir(tmp_path) -> Path:
    workflows_root = tmp_path / "workflows"
    workflows_root.mkdir()
    (workflows_root / "networking").mkdir()
    (workflows_root / "backup").mkdir()
    return workflows_root


@pytest.fixture()
def basic_manager(tmp_path) -> NornFlowVariablesManager:
    temp_vars_dir = tmp_path / "temp_vars"
    temp_vars_dir.mkdir()
    manager = NornFlowVariablesManager(vars_dir=str(temp_vars_dir))
    for name, func in ALL_FILTERS.items():
        manager.jinja_env.filters[name] = func
    return manager


@pytest.fixture()
def setup_manager(
    vars_dir: Path,
    workflows_dir: Path,
    mock_host_proxy: _SimpleHostProxy,
) -> NornFlowVariablesManager:
    manager = NornFlowVariablesManager(
        vars_dir=str(vars_dir),
        cli_vars={
            "dry_run": True,
            "credentials_file": "/etc/cli_credentials.yaml",
        },
        inline_workflow_vars={
            "backup_type": "full",
            "override_var": "workflow_value",
            "workflow_var": "workflow_value",
        },
        workflow_path=workflows_dir / "networking" / "config.yaml",
        workflow_roots=[str(workflows_dir)],
    )

    manager.nornir_host_proxy = mock_host_proxy

    manager.set_runtime_variable("runtime_var", "runtime_value", "test_device")
    manager.set_runtime_variable("command_output", "Config backup complete", "test_device")
    manager.set_runtime_variable("override_var", "runtime_value", "test_device")
    manager.set_runtime_variable("complex_var", {"key": "value", "list": [1, 2, 3]}, "test_device")

    for name, func in ALL_FILTERS.items():
        manager.jinja_env.filters[name] = func

    with patch.dict(
        "os.environ",
        {
            "NORNFLOW_VAR_credentials_file": "/etc/credentials.yaml",
            "NORNFLOW_VAR_log_format": "json",
        },
    ):
        yield manager


@pytest.fixture()
def setup_processor(setup_manager: NornFlowVariablesManager) -> NornFlowVariableProcessor:
    return NornFlowVariableProcessor(setup_manager)


@pytest.fixture()
def mock_task() -> MagicMock:
    task = MagicMock()
    task.name = "test_task"
    task.params = {"param1": "{{ host.name }}", "param2": 123}
    task.host = MagicMock()
    task.host.name = "test_device"
    return task


@pytest.fixture()
def mock_result() -> MagicMock:
    result = MagicMock()
    result.result = "Router configuration backup"
    result.failed = False
    return result
