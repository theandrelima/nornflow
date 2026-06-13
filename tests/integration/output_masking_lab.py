"""Minimal NornFlow project layout for output masking integration tests."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from nornflow.settings import NornFlowSettings

from tests.integration.fixtures.constants import INTEGRATION_MASKING_SECRET
from tests.integration.project_bootstrap import (
    FIXTURES_COMMON,
    bootstrap_nornflow_project,
    dev_nornflow_cli,
    patch_nornflow_settings,
)

MASKING_HOST_NAME = "localhost"


@dataclass(frozen=True)
class OutputMaskingIntegrationLab:
    """Paths and settings for output masking integration tests.

    Attributes:
        root: Root directory of the generated project layout.
        settings: NornFlowSettings wired to local workflows and Nornir inventory.
        host_name: Single inventory host used in workflows.
        secret_value: Token value embedded in the masking workflow vars.
    """

    root: Path
    settings: NornFlowSettings
    host_name: str = MASKING_HOST_NAME
    secret_value: str = INTEGRATION_MASKING_SECRET


def _write_single_host_inventory(hosts_path: Path, host_name: str) -> None:
    """Write a one-host SimpleInventory file for integration tests.

    Args:
        hosts_path: Destination hosts.yaml path.
        host_name: Inventory host name.
    """
    hosts_path.write_text(f"{host_name}:\n  hostname: 127.0.0.1\n  data: {{}}\n")


def build_output_masking_integration_lab(lab_root: Path) -> OutputMaskingIntegrationLab:
    """Create a self-contained project for output masking integration tests.

    Args:
        lab_root: Directory where the temp project is created.

    Returns:
        OutputMaskingIntegrationLab with settings ready for NornFlow initialization.
    """
    try:
        nornflow_cli = dev_nornflow_cli()
    except FileNotFoundError as exc:
        pytest.skip(str(exc))

    settings_file = bootstrap_nornflow_project(
        lab_root,
        nornflow_executable=nornflow_cli,
        overlay_dirs=[FIXTURES_COMMON],
        write_hosts=lambda path: _write_single_host_inventory(path, MASKING_HOST_NAME),
    )

    patch_nornflow_settings(
        settings_file,
        {"redaction": {"enabled": True, "sensitive_names": ["credential_x"]}},
    )

    settings = NornFlowSettings.load(str(settings_file), base_dir=lab_root)

    return OutputMaskingIntegrationLab(root=lab_root, settings=settings)
