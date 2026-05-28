"""Phase B: nornflow show CLI against loaded catalogs (no device I/O)."""

import subprocess

import pytest

from tests.integration.containerlab.conftest import run_nornflow_cli
from tests.integration.containerlab.lab_project import (
    LAB_INTEGRATION_WORKFLOW,
    LAB_READONLY_BLUEPRINT,
    LabEnvironment,
)


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout or ''}\n{result.stderr or ''}"


@pytest.mark.parametrize(
    ("cli_args", "needles"),
    [
        (
            ["show", "--tasks"],
            ["nornflow.set", "nornflow_arista.get_facts"],
        ),
        (
            ["show", "--filters"],
            ["nornflow.groups"],
        ),
        (
            ["show", "--workflows"],
            [LAB_INTEGRATION_WORKFLOW, "nornflow_arista.daily_snapshot.yaml"],
        ),
        (
            ["show", "--blueprints"],
            [LAB_READONLY_BLUEPRINT, "nornflow_arista.state_snapshot.yaml"],
        ),
        (
            ["show", "--j2-filters"],
            ["nornflow_arista.eos_vlan_expand", "nornflow_arista.eos_intf_canonical"],
        ),
        (
            ["show", "--hooks"],
            ["nornflow.if", "nornflow.single", "nornflow.set_to"],
        ),
    ],
)
def test_show_individual_catalogs(
    lab_environment: LabEnvironment,
    cli_args: list[str],
    needles: list[str],
) -> None:
    """Each nornflow show catalog flag exits zero and lists expected qualified assets."""
    result = run_nornflow_cli(lab_environment, cli_args)
    output = _combined_output(result)
    assert result.returncode == 0, output
    for needle in needles:
        assert needle in output, f"Expected {needle!r} in show output for {cli_args}"


def test_show_all_catalogs(lab_environment: LabEnvironment) -> None:
    """nornflow show --catalogs lists builtins and nornflow_arista assets together."""
    result = run_nornflow_cli(lab_environment, ["show", "--catalogs"])
    output = _combined_output(result)
    assert result.returncode == 0, output
    for needle in (
        "nornflow.set",
        "nornflow_arista.get_facts",
        "nornflow_arista.eos_vlan_expand",
        "nornflow.if",
        LAB_INTEGRATION_WORKFLOW,
        LAB_READONLY_BLUEPRINT,
    ):
        assert needle in output, f"Expected {needle!r} in show --catalogs output"
