"""Phase C: store_as failure-path workflow (write_file fails, conditional echo follows)."""

from tests.integration.containerlab.conftest import run_nornflow_cli
from tests.integration.containerlab.constants import (
    LAB_STORE_AS_FAILURE_MARKER,
    LAB_STORE_AS_FAILURE_WORKFLOW,
)
from tests.integration.containerlab.lab_project import LabEnvironment


def test_store_as_stores_failed_flag_and_enables_conditional_followup(
    lab_environment: LabEnvironment,
) -> None:
    """store_as captures Result.failed on failure; if-hook echo proves the var is set."""
    result = run_nornflow_cli(
        lab_environment,
        ["run", LAB_STORE_AS_FAILURE_WORKFLOW],
        stream=False,
    )
    output = f"{result.stdout or ''}{result.stderr or ''}"
    assert LAB_STORE_AS_FAILURE_MARKER in output, (
        "Expected conditional echo after store_as stored step_failed from failed write_file"
    )
