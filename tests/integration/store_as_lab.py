"""Minimal NornFlow project layout for store_as integration tests."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from nornflow.settings import NornFlowSettings

from tests.integration.fixtures.constants import (
    STORE_AS_ECHO_MESSAGE,
    STORE_AS_FAILURE_MARKER,
    WORKFLOW_STORE_AS_FAILURE,
    WORKFLOW_STORE_AS_RESULT_PATH,
    WORKFLOW_STORE_AS_SIMPLE,
)
from tests.integration.project_bootstrap import (
    FIXTURES_COMMON,
    bootstrap_nornflow_project,
    dev_nornflow_cli,
)

STORE_AS_HOST_NAME = "localhost"

WORKFLOW_SIMPLE_MODE = WORKFLOW_STORE_AS_SIMPLE
WORKFLOW_RESULT_PATH = WORKFLOW_STORE_AS_RESULT_PATH
WORKFLOW_FAILURE_PATH = WORKFLOW_STORE_AS_FAILURE


@dataclass(frozen=True)
class StoreAsIntegrationLab:
    """Paths and settings for store_as workflow integration tests.

    Attributes:
        root: Root directory of the generated project layout.
        settings: NornFlowSettings wired to local workflows and Nornir inventory.
        host_name: Single inventory host used in workflows.
    """

    root: Path
    settings: NornFlowSettings
    host_name: str = STORE_AS_HOST_NAME


def _write_single_host_inventory(hosts_path: Path, host_name: str) -> None:
    """Write a one-host SimpleInventory file for integration tests.

    Args:
        hosts_path: Destination hosts.yaml path.
        host_name: Inventory host name.
    """
    hosts_path.write_text(f"{host_name}:\n  hostname: 127.0.0.1\n  data: {{}}\n")


def build_store_as_integration_lab(lab_root: Path) -> StoreAsIntegrationLab:
    """Create a self-contained project for store_as integration tests.

    Args:
        lab_root: Directory where the temp project is created.

    Returns:
        StoreAsIntegrationLab with settings ready for NornFlow initialization.
    """
    try:
        nornflow_cli = dev_nornflow_cli()
    except FileNotFoundError as exc:
        pytest.skip(str(exc))

    settings_file = bootstrap_nornflow_project(
        lab_root,
        nornflow_executable=nornflow_cli,
        overlay_dirs=[FIXTURES_COMMON],
        write_hosts=lambda path: _write_single_host_inventory(path, STORE_AS_HOST_NAME),
    )

    settings = NornFlowSettings.load(str(settings_file), base_dir=lab_root)

    return StoreAsIntegrationLab(root=lab_root, settings=settings)


__all__ = [
    "STORE_AS_ECHO_MESSAGE",
    "STORE_AS_FAILURE_MARKER",
    "STORE_AS_HOST_NAME",
    "StoreAsIntegrationLab",
    "WORKFLOW_FAILURE_PATH",
    "WORKFLOW_RESULT_PATH",
    "WORKFLOW_SIMPLE_MODE",
    "build_store_as_integration_lab",
]
