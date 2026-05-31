"""Phase C: live lab workflow with vars, j2 filters, hooks, blueprint, and package tasks."""

from tests.integration.containerlab.conftest import run_lab_workflow
from tests.integration.containerlab.lab_project import LabEnvironment


def test_integration_workflow_on_live_lab(lab_environment: LabEnvironment) -> None:
    """lab_integration.yaml runs echo, blueprint (single+store_as), set, and get_facts on cEOS."""
    result = run_lab_workflow(lab_environment)
    assert result.returncode == 0, "nornflow run lab_integration.yaml failed (see output above)"
