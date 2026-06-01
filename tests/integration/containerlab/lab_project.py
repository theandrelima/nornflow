"""Build a temporary NornFlow project for containerlab integration tests."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from tests.integration.containerlab.constants import (
    LAB_EAPI_PORT,
    LAB_EAPI_TRANSPORT,
    LAB_HOSTS,
    LAB_INTEGRATION_WORKFLOW,
    LAB_READONLY_BLUEPRINT,
    NORNFLOW_ARISTA_PACKAGE,
    NORNFLOW_ARISTA_VERSION,
)


@dataclass(frozen=True)
class LabEnvironment:
    """Paths for a session-scoped containerlab test environment.

    Attributes:
        root: Top-level temp directory (venv + project).
        venv_dir: Path to the dedicated virtual environment.
        project_root: Generated NornFlow project directory.
        settings_file: Path to generated nornflow.yaml.
        python: Python executable inside the lab venv.
        nornflow_cli: nornflow CLI entrypoint inside the lab venv.
        runner_script: lab_runner.py used for subprocess execution.
    """

    root: Path
    venv_dir: Path
    project_root: Path
    settings_file: Path
    python: Path
    nornflow_cli: Path
    runner_script: Path


def repo_root() -> Path:
    """Return the nornflow repository root (parent of tests/)."""
    return Path(__file__).resolve().parents[3]


def _write_hosts_yaml(path: Path, username: str, password: str) -> None:
    """Write static Nornir hosts with eAPI connection data.

    Args:
        path: Destination hosts.yaml path.
        username: Device login user from NORNFLOW_LAB_USER.
        password: Device login password from NORNFLOW_LAB_PASSWORD.
    """
    hosts: dict[str, dict[str, object]] = {}
    for name, spec in LAB_HOSTS.items():
        hosts[name] = {
            "hostname": spec["hostname"],
            "username": username,
            "password": password,
            "groups": list(spec["groups"]),
            "data": {
                "eapi_transport": LAB_EAPI_TRANSPORT,
                "eapi_port": LAB_EAPI_PORT,
            },
        }
    path.write_text(yaml.safe_dump(hosts, sort_keys=True))


def _write_nornir_tree(project_root: Path) -> Path:
    """Write Nornir config and inventory under nornir_configs/.

    Args:
        project_root: Root of the generated project.

    Returns:
        Path to config.yaml.
    """
    config_dir = project_root / "nornir_configs"
    inventory_dir = config_dir / "inventory"
    inventory_dir.mkdir(parents=True, exist_ok=True)

    (inventory_dir / "groups.yaml").write_text(
        yaml.safe_dump(
            {
                "eos": {},
                "spines": {},
                "leafs": {},
            },
            sort_keys=True,
        )
    )
    (inventory_dir / "defaults.yaml").write_text("{}\n")

    config_file = config_dir / "config.yaml"
    config_file.write_text(
        """\
inventory:
  plugin: SimpleInventory
  options:
    host_file: 'nornir_configs/inventory/hosts.yaml'
    group_file: 'nornir_configs/inventory/groups.yaml'
    defaults_file: 'nornir_configs/inventory/defaults.yaml'
runner:
  plugin: threaded
  options:
    num_workers: 4
"""
    )
    return config_file


def _write_local_blueprint(project_root: Path) -> Path:
    """Write a minimal local blueprint using package read-only getters.

    Args:
        project_root: Root of the generated project.

    Returns:
        Path to the blueprint YAML file.
    """
    blueprints_dir = project_root / "blueprints"
    blueprints_dir.mkdir(parents=True, exist_ok=True)
    blueprint_file = blueprints_dir / LAB_READONLY_BLUEPRINT
    blueprint_file.write_text(
        """\
description: >
  Read-only snapshot for containerlab: version facts and LLDP neighbors.
  Uses store_as to store results in runtime variables.

tasks:
  - name: nornflow_arista.get_facts
    store_as:
      facts: result

  - name: nornflow_arista.get_lldp_neighbors
    args:
      detail: true
    store_as:
      lldp_neighbors: result
"""
    )
    return blueprint_file


def _write_lab_integration_workflow(project_root: Path) -> Path:
    """Write a workflow exercising vars, j2 filters, hooks, and a local blueprint.

    Args:
        project_root: Root of the generated project.

    Returns:
        Path to the workflow YAML file.
    """
    workflows_dir = project_root / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    workflow_file = workflows_dir / LAB_INTEGRATION_WORKFLOW
    workflow_file.write_text(
        """\
workflow:
  name: Containerlab integration workflow
  description: >
    Exercises workflow vars, package j2 filters, builtin hooks (if, single, store_as),
    a local blueprint, and read-only nornflow_arista tasks against live cEOS.
  vars:
    lab_active: true
  tasks:
    - name: nornflow.echo
      args:
        msg: >-
          {{ host.name }}: vlans={{ '10,20-22' | nornflow_arista.eos_vlan_expand | join(',') }}
          intf={{ 'gi0/1' | nornflow_arista.eos_intf_canonical }}
      if: "{{ lab_active }}"

    - blueprint: """
        + LAB_READONLY_BLUEPRINT
        + """
      single: true

    - name: nornflow.set
      args:
        lab_checked: "{{ host.name }}-ok"
        lab_vlans: "{{ '10,20-22' | nornflow_arista.eos_vlan_expand | join(',') }}"
      if: "{{ lab_active }}"

    - name: nornflow_arista.get_facts
      store_as:
        final_facts: result
      if: "{{ lab_active }}"
"""
    )
    return workflow_file


def _write_nornflow_settings(project_root: Path, nornir_config_file: Path) -> Path:
    """Write nornflow.yaml for a package-only temp project.

    Args:
        project_root: Root of the generated project.
        nornir_config_file: Path to the Nornir config file.

    Returns:
        Path to nornflow.yaml.
    """
    settings_file = project_root / "nornflow.yaml"
    settings = {
        "nornir_config_file": str(nornir_config_file.relative_to(project_root)),
        "packages": [NORNFLOW_ARISTA_PACKAGE],
        "local_tasks": [],
        "local_workflows": ["workflows"],
        "local_filters": [],
        "local_hooks": [],
        "local_blueprints": ["blueprints"],
        "local_j2_filters": [],
        "logger": {
            "directory": ".nornflow/logs",
            "level": "INFO",
        },
    }
    settings_file.write_text(yaml.safe_dump(settings, sort_keys=True))
    return settings_file


def build_lab_project(project_root: Path, username: str, password: str) -> Path:
    """Create the on-disk NornFlow project layout.

    Args:
        project_root: Directory where nornflow.yaml and Nornir files are written.
        username: Device login user.
        password: Device login password.

    Returns:
        Path to the generated nornflow.yaml file.
    """
    project_root.mkdir(parents=True, exist_ok=True)
    config_file = _write_nornir_tree(project_root)
    _write_hosts_yaml(project_root / "nornir_configs" / "inventory" / "hosts.yaml", username, password)
    _write_local_blueprint(project_root)
    _write_lab_integration_workflow(project_root)
    return _write_nornflow_settings(project_root, config_file)


def _run_command(args: list[str], *, cwd: Path | None = None) -> None:
    """Run a subprocess and raise on non-zero exit.

    Args:
        args: Command argv.
        cwd: Optional working directory.

    Raises:
        RuntimeError: When the command exits with a non-zero status.
    """
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{detail}")


def provision_lab_environment(root: Path, username: str, password: str) -> LabEnvironment:
    """Create venv, install packages, and write the temp NornFlow project.

    Args:
        root: Session temp directory.
        username: Lab device username.
        password: Lab device password.

    Returns:
        LabEnvironment with paths needed to run lab_runner phases.
    """
    venv_dir = root / "venv"
    project_root = root / "project"
    checkout = repo_root()
    runner_script = Path(__file__).resolve().parent / "lab_runner.py"

    _run_command(["uv", "venv", str(venv_dir)])
    python = venv_dir / "bin" / "python"
    _run_command(
        [
            "uv",
            "pip",
            "install",
            "-e",
            str(checkout),
            f"nornflow-arista=={NORNFLOW_ARISTA_VERSION}",
            "--python",
            str(python),
        ]
    )

    settings_file = build_lab_project(project_root, username, password)

    return LabEnvironment(
        root=root,
        venv_dir=venv_dir,
        project_root=project_root,
        settings_file=settings_file,
        python=python,
        nornflow_cli=venv_dir / "bin" / "nornflow",
        runner_script=runner_script,
    )


def destroy_lab_environment(lab: LabEnvironment) -> None:
    """Remove the session temp tree.

    Args:
        lab: Environment returned by provision_lab_environment.
    """
    if lab.root.exists():
        shutil.rmtree(lab.root)
