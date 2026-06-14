"""Phase B: nornflow validate CLI against lab fixture workflows (no device I/O)."""

import subprocess

import pytest

from tests.integration.containerlab.conftest import run_nornflow_cli
from tests.integration.containerlab.constants import (
    LAB_VALIDATE_BAD_ARGS_WORKFLOW,
    LAB_VALIDATE_BAD_TASK_WORKFLOW,
    LAB_VALIDATE_BLUEPRINT_LOOP_WORKFLOW,
    LAB_VALIDATE_OK_WORKFLOW,
)
from tests.integration.containerlab.lab_project import LabEnvironment


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout or ''}\n{result.stderr or ''}"


def test_validate_ok_workflow(lab_environment: LabEnvironment) -> None:
    """Valid lab workflow passes static validation."""
    result = run_nornflow_cli(lab_environment, ["validate", LAB_VALIDATE_OK_WORKFLOW])
    output = _combined_output(result)
    assert result.returncode == 0, output
    assert "Validation passed" in output


@pytest.mark.parametrize(
    ("workflow", "needles"),
    [
        (LAB_VALIDATE_BAD_TASK_WORKFLOW, ["not found"]),
        (LAB_VALIDATE_BAD_ARGS_WORKFLOW, ["missing required", "argument"]),
        (LAB_VALIDATE_BLUEPRINT_LOOP_WORKFLOW, ["Circular dependency detected"]),
    ],
)
def test_validate_failure_workflows(
    lab_environment: LabEnvironment,
    workflow: str,
    needles: list[str],
) -> None:
    """Invalid lab workflows fail validate with actionable errors.

    Needles are checked individually because Rich may wrap long error messages
    across table cell rows, breaking multi-word substrings that straddle lines.
    """
    result = run_nornflow_cli(lab_environment, ["validate", workflow])
    output = _combined_output(result)
    assert result.returncode != 0, output
    for needle in needles:
        assert needle.lower() in output.lower(), f"Needle {needle!r} not found in:\n{output}"
