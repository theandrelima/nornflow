"""Fixtures and gates for opt-in containerlab integration tests."""

import os
import subprocess
from collections.abc import Iterator

import pytest

from tests.integration.containerlab.constants import LAB_INTEGRATION_WORKFLOW
from tests.integration.containerlab.lab_project import (
    LabEnvironment,
    destroy_lab_environment,
    provision_lab_environment,
)

SKIP_REASON = "Set NORNFLOW_LAB=1 to run containerlab integration tests"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply containerlab marker and skip gate to tests in this directory."""
    lab_enabled = os.environ.get("NORNFLOW_LAB") == "1"
    for item in items:
        if "/containerlab/" not in str(item.path):
            continue
        item.add_marker(pytest.mark.containerlab)
        if not lab_enabled:
            item.add_marker(pytest.mark.skip(reason=SKIP_REASON))


def _require_lab_credentials() -> tuple[str, str]:
    """Return lab credentials from the environment.

    Returns:
        Tuple of username and password.

    Raises:
        pytest.Failed: When NORNFLOW_LAB=1 but credentials are missing.
    """
    username = os.environ.get("NORNFLOW_LAB_USER", "").strip()
    password = os.environ.get("NORNFLOW_LAB_PASSWORD", "").strip()
    if not username or not password:
        pytest.fail("NORNFLOW_LAB_USER and NORNFLOW_LAB_PASSWORD are required when NORNFLOW_LAB=1")
    return username, password


@pytest.fixture(scope="session")
def lab_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[LabEnvironment]:
    """Phase A: provision isolated venv + temp project; tear down after the session.

    Yields:
        LabEnvironment with venv, project paths, and lab_runner location.
    """
    if os.environ.get("NORNFLOW_LAB") != "1":
        pytest.skip(SKIP_REASON)

    username, password = _require_lab_credentials()
    lab_root = tmp_path_factory.mktemp("nornflow_containerlab")
    lab = provision_lab_environment(lab_root, username, password)
    yield lab
    destroy_lab_environment(lab)


def run_nornflow_cli(
    lab: LabEnvironment,
    cli_args: list[str],
    *,
    stream: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a nornflow CLI command inside the lab venv.

    Args:
        lab: Session lab environment.
        cli_args: Arguments after global options (e.g. ``['show', '--tasks']``).
        stream: When True, inherit stdout/stderr for live CLI output.

    Returns:
        Completed subprocess result.
    """
    command = [str(lab.nornflow_cli), "--settings", str(lab.settings_file), *cli_args]
    return subprocess.run(
        command,
        cwd=str(lab.project_root),
        capture_output=not stream,
        text=True,
        check=False,
    )


def run_lab_phase(lab: LabEnvironment, phase: str) -> subprocess.CompletedProcess[str | None]:
    """Execute a lab_runner phase inside the lab venv.

    Args:
        lab: Session lab environment.
        phase: ``phase-b`` (in-process catalog validation).

    Returns:
        Completed subprocess result.
    """
    command = [str(lab.python), str(lab.runner_script), phase, str(lab.settings_file)]
    return subprocess.run(
        command,
        cwd=str(lab.project_root),
        capture_output=True,
        text=True,
        check=False,
    )


def run_lab_workflow(lab: LabEnvironment, workflow: str = LAB_INTEGRATION_WORKFLOW) -> subprocess.CompletedProcess[str | None]:
    """Run a workflow via the real ``nornflow run`` CLI with live output.

    Args:
        lab: Session lab environment.
        workflow: Workflow filename under the temp project's workflows/ directory.

    Returns:
        Completed subprocess result (stdout/stderr are None when streamed live).
    """
    return run_nornflow_cli(lab, ["run", workflow], stream=True)
