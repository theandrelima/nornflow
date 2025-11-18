import pytest
from unittest.mock import MagicMock
from nornir.core.inventory import Host, Inventory


class MockNornir:
    """Simple mock object for Nornir that behaves like a real object for attribute checks."""
    
    def __init__(self):
        self.processors = []
        self.inventory = MagicMock()


@pytest.fixture
def mock_host():
    """Fixture providing a mock Host object."""
    host = MagicMock(spec=Host)
    host.name = "test_host"
    host.data = {}
    return host


@pytest.fixture
def mock_inventory(mock_host):
    """Fixture providing a mock Inventory with a host."""
    inventory = MagicMock(spec=Inventory)
    inventory.hosts = {mock_host.name: mock_host}
    return inventory


@pytest.fixture
def mock_nornir(mock_inventory):
    """Fixture providing a mock Nornir instance with inventory."""
    nornir = MockNornir()
    nornir.inventory = mock_inventory
    return nornir


@pytest.fixture
def mock_task(mock_nornir):
    """Fixture providing a mock task with nornir instance."""
    task = MagicMock()
    task.name = "test_task"
    task.nornir = mock_nornir
    task.host = mock_nornir.inventory.hosts["test_host"]
    return task


@pytest.fixture
def mock_device_context():
    """Fixture providing a mock device context with runtime vars."""
    context = MagicMock()
    context.runtime_vars = {}
    context.resolve_value = MagicMock(return_value="resolved")
    return context


@pytest.fixture
def mock_vars_manager(mock_device_context):
    """Fixture providing a mock VarsManager."""
    manager = MagicMock()
    manager.get_device_context = MagicMock(return_value=mock_device_context)
    manager.resolve_string = MagicMock(return_value="resolved")
    manager.resolve_data = MagicMock(return_value="resolved")
    manager.set_runtime_variable = MagicMock()
    return manager


@pytest.fixture
def mock_processor_with_vars_manager(mock_vars_manager):
    """Fixture providing a processor with vars_manager attribute."""
    processor = MagicMock()
    processor.vars_manager = mock_vars_manager
    return processor


@pytest.fixture
def mock_processor_compatible():
    """Fixture providing a processor that supports shush hook."""
    processor = MagicMock()
    processor.supports_shush_hook = True
    return processor


@pytest.fixture
def mock_processor_incompatible():
    """Fixture providing a processor that doesn't support shush hook."""
    processor = MagicMock()
    processor.supports_shush_hook = False
    return processor


@pytest.fixture
def mock_filters_catalog():
    """Fixture providing a mock filters catalog."""
    catalog = {}
    return catalog