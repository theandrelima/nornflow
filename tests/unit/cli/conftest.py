import pytest

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
