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
    NORNFLOW_ARISTA_PACKAGE,
    NORNFLOW_ARISTA_VERSION,
)
from tests.integration.project_bootstrap import (
    FIXTURES_COMMON,
    bootstrap_nornflow_project,
)

CONTAINERLAB_OVERLAY = Path(__file__).resolve().parent / "fixtures" / "overlay"


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


def write_lab_hosts_yaml(path: Path, username: str, password: str) -> None:
    """Write Nornir hosts with eAPI connection data from LAB_HOSTS.

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


def build_lab_project(
    project_root: Path,
    nornflow_cli: Path,
    username: str,
    password: str,
) -> Path:
    """Create the on-disk NornFlow project via init, fixtures, and hosts injection.

    Args:
        project_root: Directory where the project is created.
        nornflow_cli: nornflow CLI from the lab venv.
        username: Device login user.
        password: Device login password.

    Returns:
        Path to nornflow.yaml.
    """
    return bootstrap_nornflow_project(
        project_root,
        nornflow_executable=nornflow_cli,
        overlay_dirs=[FIXTURES_COMMON, CONTAINERLAB_OVERLAY],
        settings_patch={"packages": [NORNFLOW_ARISTA_PACKAGE]},
        write_hosts=lambda hosts_path: write_lab_hosts_yaml(hosts_path, username, password),
    )


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
    """Phase A: create venv, install packages, and bootstrap the temp NornFlow project.

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
    nornflow_cli = venv_dir / "bin" / "nornflow"
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

    settings_file = build_lab_project(project_root, nornflow_cli, username, password)

    return LabEnvironment(
        root=root,
        venv_dir=venv_dir,
        project_root=project_root,
        settings_file=settings_file,
        python=python,
        nornflow_cli=nornflow_cli,
        runner_script=runner_script,
    )


def destroy_lab_environment(lab: LabEnvironment) -> None:
    """Remove the session temp tree.

    Args:
        lab: Environment returned by provision_lab_environment.
    """
    if lab.root.exists():
        shutil.rmtree(lab.root)
