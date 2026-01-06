import pytest
from pathlib import Path

from nornflow.blueprints.resolver import BlueprintResolver


@pytest.fixture
def blueprint_resolver() -> BlueprintResolver:
    """Provides a BlueprintResolver instance for blueprint tests."""
    return BlueprintResolver()


@pytest.fixture
def mock_blueprints_catalog(tmp_path: Path) -> dict[str, Path]:
    """Provides a mock blueprint catalog with sample files."""
    catalog = {}
    # Create a sample blueprint file
    blueprint_dir = tmp_path / "blueprints"
    blueprint_dir.mkdir()
    sample_blueprint = blueprint_dir / "sample.yaml"
    sample_blueprint.write_text("""
tasks:
  - name: sample_task
    task: netmiko_send_command
    command_string: "show version"
""")
    catalog["sample"] = sample_blueprint
    return catalog


@pytest.fixture
def mock_vars_dir(tmp_path: Path) -> Path:
    """Provides a mock vars directory with defaults."""
    vars_dir = tmp_path / "vars"
    vars_dir.mkdir()
    defaults_file = vars_dir / "defaults.yaml"
    defaults_file.write_text("default_var: value")
    return vars_dir


@pytest.fixture
def mock_workflow_path(tmp_path: Path) -> Path:
    """Provides a mock workflow path."""
    workflow_file = tmp_path / "workflow.yaml"
    workflow_file.write_text("workflow: {}")
    return workflow_file


@pytest.fixture
def mock_workflow_roots(tmp_path: Path) -> list[str]:
    """Provides mock workflow roots."""
    return [str(tmp_path / "workflows")]


@pytest.fixture
def mock_cli_vars() -> dict[str, str]:
    """Provides mock CLI variables."""
    return {"cli_var": "cli_value"}