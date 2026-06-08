"""Unit tests for nornflow validate CLI and workflow validation."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from nornflow.cli.entrypoint import app
from nornflow.cli.exceptions import CLIValidateError
from nornflow.cli.validate import build_nornflow_for_validate
from nornflow.exceptions import TaskError, WorkflowError, WorkflowValidationError
from nornflow.j2 import Jinja2Service
from nornflow.models import WorkflowModel
from nornflow.nornflow import NornFlow
from nornflow.settings import NornFlowSettings


def _write_minimal_project(root: Path) -> Path:
    """Create a minimal NornFlow project tree for validate tests.

    Args:
        root: Directory that becomes the project root.

    Returns:
        Path to the generated nornflow.yaml settings file.
    """
    (root / "nornir_configs").mkdir()
    (root / "nornir_configs" / "config.yaml").write_text(
        """inventory:
  plugin: SimpleInventory
  options:
    host_file: nornir_configs/hosts.yaml
runner:
  plugin: threaded
  options:
    num_workers: 1
"""
    )
    (root / "nornir_configs" / "hosts.yaml").write_text("localhost:\n  hostname: 127.0.0.1\n")
    for dirname in ("workflows", "blueprints", "vars", "tasks", "filters", "hooks", "j2_filters"):
        (root / dirname).mkdir()
    (root / "vars" / "defaults.yaml").write_text("{}\n")

    settings_path = root / "nornflow.yaml"
    settings_path.write_text(
        f"""nornir_config_file: nornir_configs/config.yaml
local_workflows:
  - workflows
local_blueprints:
  - blueprints
vars_dir: vars
processors:
  - class: nornflow.builtins.DefaultNornFlowProcessor
"""
    )
    return settings_path


@pytest.fixture
def validate_project(tmp_path: Path) -> Path:
    """Minimal project root directory."""
    _write_minimal_project(tmp_path)
    return tmp_path


class TestBuildNornflowForValidate:
    """Tests for validate CLI assembly helper."""

    def test_missing_workflow_raises(self, validate_project: Path) -> None:
        settings = validate_project / "nornflow.yaml"
        with pytest.raises(CLIValidateError, match="not found"):
            build_nornflow_for_validate(str(settings), "missing.yaml")

    def test_non_yaml_extension_raises(self, validate_project: Path) -> None:
        settings = validate_project / "nornflow.yaml"
        bad_path = validate_project / "workflows" / "notes.txt"
        bad_path.write_text("not yaml\n")
        with pytest.raises(CLIValidateError, match="must end with"):
            build_nornflow_for_validate(str(settings), str(bad_path))


class TestValidateCLI:
    """End-to-end CLI tests for nornflow validate."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_validate_success(self, validate_project: Path, runner: CliRunner) -> None:
        workflow = validate_project / "workflows" / "ok.yaml"
        workflow.write_text(
            """workflow:
  name: ok
  tasks:
    - name: nornflow.echo
      args:
        msg: hello
"""
        )
        result = runner.invoke(
            app,
            ["--settings", str(validate_project / "nornflow.yaml"), "validate", str(workflow)],
        )
        assert result.exit_code == 0, result.output
        assert "Validation passed" in result.output

    def test_validate_success_by_catalog_name(self, validate_project: Path, runner: CliRunner) -> None:
        workflow = validate_project / "workflows" / "ok.yaml"
        workflow.write_text(
            """workflow:
  name: ok
  tasks:
    - name: nornflow.echo
      args:
        msg: hello
"""
        )
        result = runner.invoke(
            app,
            ["--settings", str(validate_project / "nornflow.yaml"), "validate", "ok.yaml"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert "Validation passed" in result.output

    def test_validate_unknown_task_fails(self, validate_project: Path, runner: CliRunner) -> None:
        workflow = validate_project / "workflows" / "bad_task.yaml"
        workflow.write_text(
            """workflow:
  name: bad task
  tasks:
    - name: nornflow.no_such_task
"""
        )
        result = runner.invoke(
            app,
            ["--settings", str(validate_project / "nornflow.yaml"), "validate", str(workflow)],
        )
        combined = (result.output + getattr(result, "stderr", "")).lower()
        assert result.exit_code == 1, result.output
        assert "validation failed" in combined or "validation error" in combined

    def test_validate_missing_args_fails(self, validate_project: Path, runner: CliRunner) -> None:
        workflow = validate_project / "workflows" / "bad_args.yaml"
        workflow.write_text(
            """workflow:
  name: bad args
  tasks:
    - name: nornflow.echo
      args: {}
"""
        )
        result = runner.invoke(
            app,
            ["--settings", str(validate_project / "nornflow.yaml"), "validate", str(workflow)],
        )
        combined = (result.output + getattr(result, "stderr", "")).lower()
        assert result.exit_code == 1, result.output
        assert "args" in combined
        assert "'msg'" in combined

    def test_validate_reports_all_task_errors(self, validate_project: Path, runner: CliRunner) -> None:
        workflow = validate_project / "workflows" / "many_errors.yaml"
        workflow.write_text(
            """workflow:
  name: many errors
  tasks:
    - name: nornflow.no_such_task
    - name: nornflow.echo
      args: {}
    - name: nornflow.echo
      args:
        message: hello
"""
        )
        result = runner.invoke(
            app,
            ["--settings", str(validate_project / "nornflow.yaml"), "validate", str(workflow)],
        )
        combined = (result.output + getattr(result, "stderr", "")).lower()
        assert result.exit_code == 1, result.output
        assert "3 validation error" in combined
        assert "catalog" in combined
        assert combined.count("args") >= 2

    def test_validate_circular_blueprint_fails(self, validate_project: Path, runner: CliRunner) -> None:
        blueprint_dir = validate_project / "blueprints"
        (blueprint_dir / "loop_a.yaml").write_text("tasks:\n  - blueprint: loop_b.yaml\n")
        (blueprint_dir / "loop_b.yaml").write_text("tasks:\n  - blueprint: loop_a.yaml\n")
        workflow = validate_project / "workflows" / "loop.yaml"
        workflow.write_text(
            """workflow:
  name: loop
  tasks:
    - blueprint: loop_a.yaml
"""
        )
        result = runner.invoke(
            app,
            ["--settings", str(validate_project / "nornflow.yaml"), "validate", str(workflow)],
            catch_exceptions=False,
        )
        assert result.exit_code == 1, result.output
        assert "circular dependency detected" in result.output.lower()


class TestNornFlowValidateWorkflow:
    """In-process validate_workflow API tests."""

    def test_validate_workflow_without_loaded_workflow_raises(self) -> None:
        settings = NornFlowSettings(nornir_config_file="dummy.yaml")
        nornflow = NornFlow(nornflow_settings=settings)
        with pytest.raises(WorkflowError, match="No workflow loaded"):
            nornflow.validate_workflow()

    def test_validate_workflow_unknown_task(self, validate_project: Path) -> None:
        settings = NornFlowSettings.load(
            str(validate_project / "nornflow.yaml"),
            base_dir=validate_project,
        )
        nornflow = NornFlow(nornflow_settings=settings)
        workflow = WorkflowModel.create(
            {
                "workflow": {
                    "name": "bad task",
                    "tasks": [{"name": "nornflow.no_such_task"}],
                }
            }
        )
        with pytest.raises(WorkflowValidationError) as exc_info:
            nornflow.validate_workflow(workflow)
        assert len(exc_info.value.issues) == 1
        assert exc_info.value.issues[0].category == "catalog"
        assert exc_info.value.issues[0].message == "Task not found in tasks catalog"

    def test_validate_workflow_checks_task_args(self, validate_project: Path) -> None:
        settings = NornFlowSettings.load(
            str(validate_project / "nornflow.yaml"),
            base_dir=validate_project,
        )
        nornflow = NornFlow(nornflow_settings=settings)
        workflow = WorkflowModel.create(
            {
                "workflow": {
                    "name": "bad args",
                    "tasks": [{"name": "nornflow.echo", "args": {}}],
                }
            }
        )
        with pytest.raises(WorkflowValidationError) as exc_info:
            nornflow.validate_workflow(workflow)
        assert len(exc_info.value.issues) == 1
        assert exc_info.value.issues[0].category == "args"


class TestJinja2ServiceReset:
    """Ensure successive NornFlow inits do not leak custom j2 filters."""

    def test_initialize_with_settings_replaces_custom_filters(self, tmp_path: Path) -> None:
        filters_a = tmp_path / "filters_a"
        filters_b = tmp_path / "filters_b"
        filters_a.mkdir()
        filters_b.mkdir()
        (filters_a / "filter_a.py").write_text(
            "def filter_a(value):\n    return f'a-{value}'\n"
        )
        (filters_b / "filter_b.py").write_text(
            "def filter_b(value):\n    return f'b-{value}'\n"
        )

        settings_a = NornFlowSettings(
            nornir_config_file="dummy.yaml",
            local_j2_filters=[str(filters_a)],
        )
        settings_b = NornFlowSettings(
            nornir_config_file="dummy.yaml",
            local_j2_filters=[str(filters_b)],
        )

        Jinja2Service.initialize_with_settings(settings_a)
        catalog = Jinja2Service().j2_filters_catalog
        assert "local.filter_a" in catalog
        assert "local.filter_b" not in catalog

        Jinja2Service.initialize_with_settings(settings_b)
        catalog = Jinja2Service().j2_filters_catalog
        assert "local.filter_b" in catalog
        assert "local.filter_a" not in catalog
