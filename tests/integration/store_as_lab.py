"""Minimal NornFlow project layout for store_as integration tests."""

from dataclasses import dataclass
from pathlib import Path

from nornflow.settings import NornFlowSettings

STORE_AS_ECHO_MESSAGE = "LAB_STORE_AS_SIMPLE_OK"
STORE_AS_HOST_NAME = "router1"

WORKFLOW_SIMPLE_MODE = "store_as_simple_mode.yaml"
WORKFLOW_RESULT_PATH = "store_as_result_path.yaml"


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


def _write_nornir_tree(lab_root: Path, host_name: str) -> Path:
    """Write Nornir config and a one-host SimpleInventory.

    Args:
        lab_root: Lab root directory.
        host_name: Inventory host name.

    Returns:
        Path to config.yaml.
    """
    nornir_dir = lab_root / "nornir"
    nornir_dir.mkdir(parents=True, exist_ok=True)

    hosts_file = nornir_dir / "hosts.yaml"
    groups_file = nornir_dir / "groups.yaml"
    defaults_file = nornir_dir / "defaults.yaml"

    hosts_file.write_text(f"{host_name}:\n  hostname: localhost\n  data: {{}}\n")
    groups_file.write_text("{}\n")
    defaults_file.write_text("{}\n")

    config_file = nornir_dir / "config.yaml"
    config_file.write_text(
        f"""\
inventory:
  plugin: SimpleInventory
  options:
    host_file: '{hosts_file}'
    group_file: '{groups_file}'
    defaults_file: '{defaults_file}'
runner:
  plugin: threaded
  options:
    num_workers: 1
"""
    )
    return config_file


def _write_workflows(workflows_dir: Path, echo_message: str) -> None:
    """Write simple-mode and result-path store_as workflows.

    Args:
        workflows_dir: Directory registered as local_workflows.
        echo_message: Message passed to nornflow.echo (stored via store_as).
    """
    workflows_dir.mkdir(parents=True, exist_ok=True)

    (workflows_dir / WORKFLOW_SIMPLE_MODE).write_text(
        f"""\
workflow:
  name: store_as simple mode equivalence
  tasks:
    - name: nornflow.echo
      args:
        msg: "{echo_message}"
      store_as: payload_a
    - name: nornflow.echo
      args:
        msg: "{{{{ payload_a }}}}"
      store_as: echo_back_a
"""
    )

    (workflows_dir / WORKFLOW_RESULT_PATH).write_text(
        f"""\
workflow:
  name: store_as result path equivalence
  tasks:
    - name: nornflow.echo
      args:
        msg: "{echo_message}"
      store_as:
        payload_b: result
    - name: nornflow.echo
      args:
        msg: "{{{{ payload_b }}}}"
      store_as: echo_back_b
"""
    )


def build_store_as_integration_lab(lab_root: Path) -> StoreAsIntegrationLab:
    """Create a self-contained project for store_as integration tests.

    Args:
        lab_root: Directory where nornir config, workflows, and vars dir are written.

    Returns:
        StoreAsIntegrationLab with settings ready for NornFlow initialization.
    """
    lab_root.mkdir(parents=True, exist_ok=True)

    config_file = _write_nornir_tree(lab_root, STORE_AS_HOST_NAME)
    workflows_dir = lab_root / "workflows"
    _write_workflows(workflows_dir, STORE_AS_ECHO_MESSAGE)

    vars_dir = lab_root / "vars"
    vars_dir.mkdir(exist_ok=True)

    settings = NornFlowSettings(
        nornir_config_file=str(config_file),
        local_workflows=[str(workflows_dir)],
        vars_dir=str(vars_dir),
    )

    return StoreAsIntegrationLab(root=lab_root, settings=settings)
