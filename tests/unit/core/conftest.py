from unittest.mock import Mock, patch

import pytest
from nornir.core import Nornir
from nornir.core.processor import Processor

from nornflow.models import WorkflowModel
from nornflow.nornflow import NornFlow
from nornflow.settings import NornFlowSettings
from tests.unit.core.test_processors_utils import TestProcessor


@pytest.fixture
def valid_workflow_dict(request):
    """Get a valid workflow dictionary with a unique task name."""
    return {
        "workflow": {
            "name": f"Test Workflow {request.function.__name__}",
            "description": "A test workflow",
            "inventory_filters": {"hosts": ["host1", "host2"], "groups": ["group1"]},
            "tasks": [{"name": f"{request.function.__name__}_task", "args": {"arg1": ["value1", "value2"]}}],
        }
    }


@pytest.fixture
def invalid_workflow_dict():
    """Get an invalid workflow dictionary (missing tasks)."""
    return {
        "workflow": {
            "name": "Test Workflow",
            "description": "A test workflow",
            "inventory_filters": {"hosts": [], "groups": []},
        }
    }


@pytest.fixture
def valid_workflow_file(tmp_path, request):
    """Create a temporary valid workflow file with a unique task name."""
    workflow_file = tmp_path / "valid_workflow.yaml"
    workflow_file.write_text(
        f"""
workflow:
  name: Test Workflow {request.function.__name__}
  description: A test workflow
  inventory_filters:
    hosts: []
    groups: []
  tasks:
    - name: {request.function.__name__}_task
      args:
        arg1: value1
"""
    )
    return workflow_file


@pytest.fixture
def invalid_workflow_file(tmp_path):
    """Create a temporary invalid workflow file."""
    workflow_file = tmp_path / "invalid_workflow.yaml"
    workflow_file.write_text(
        """
workflow:
  name: Test Workflow
  description: A test workflow
  inventory_filters:
    hosts: []
    groups: []
"""
    )
    return workflow_file


@pytest.fixture
def valid_workflow(valid_workflow_dict):
    """Create a valid workflow object."""
    return WorkflowModel.create(valid_workflow_dict)


@pytest.fixture
def task_content():
    """Return the content of a basic Nornir task."""
    return """
from nornir.core.task import Task, Result

def hello_world(task: Task) -> Result:
    \"\"\"Say hello world\"\"\"
    return Result(host=task.host, result="Hello World!")
"""


@pytest.fixture
def basic_settings(tmp_path, task_content):
    """Create basic settings with a tasks directory containing one task."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "task1.py").write_text(task_content)
    return NornFlowSettings(
        nornir_config_file="dummy_config.yaml",
        local_tasks=[str(tasks_dir)]
    )


@pytest.fixture
def basic_nornflow(basic_settings):
    """Create a basic NornFlow instance."""
    with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
        nf = NornFlow(nornflow_settings=basic_settings)
        nf._nornir_manager = Mock()
        return nf


@pytest.fixture
def mock_processor():
    """Create a mock Processor instance for testing."""
    return Mock(spec=Processor)


@pytest.fixture
def mock_nornir():
    """Create a mock Nornir instance for testing."""
    mock = Mock(spec=Nornir)
    mock.data = Mock()
    mock.data.failed_hosts = set()
    mock.filter.return_value = mock
    mock.with_processors.return_value = mock
    return mock


@pytest.fixture
def mock_init_nornir(mock_nornir):
    """Patch InitNornir to return our mock Nornir instance."""
    with patch("nornflow.nornir_manager.InitNornir", return_value=mock_nornir) as mock_init:
        yield mock_init


@pytest.fixture
def test_processor():
    """Create a TestProcessor instance."""
    return TestProcessor(name="TestProcessor")


@pytest.fixture
def test_processor_config():
    """Create a processor configuration dict for TestProcessor."""
    return {
        "class": "tests.unit.core.test_processors_utils.TestProcessor",
        "args": {"name": "ConfiguredProcessor", "verbose": True},
    }


@pytest.fixture
def test_processor2_config():
    """Create a processor configuration dict for TestProcessor2."""
    return {"class": "tests.unit.core.test_processors_utils.TestProcessor2", "args": {"name": "Processor2"}}


@pytest.fixture
def workflow_with_processors(valid_workflow_dict, test_processor_config):
    """Create a valid workflow with processor configuration."""
    workflow_dict = valid_workflow_dict.copy()
    workflow_dict["workflow"]["processors"] = [test_processor_config]
    return workflow_dict