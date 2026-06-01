"""Bootstrap a NornFlow project for integration tests via init + static fixtures."""

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import yaml

FIXTURES_COMMON = Path(__file__).resolve().parent / "fixtures" / "common"


def merge_overlay(overlay_root: Path, project_root: Path) -> None:
    """Copy all files from overlay_root onto project_root, preserving relative paths.

    Args:
        overlay_root: Directory tree to merge (e.g. fixtures/common).
        project_root: Target NornFlow project root.
    """
    if not overlay_root.is_dir():
        raise FileNotFoundError(f"Fixture overlay not found: {overlay_root}")

    for src in overlay_root.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(overlay_root)
        dest = project_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def patch_nornflow_settings(settings_file: Path, updates: dict[str, object]) -> None:
    """Merge keys into an existing nornflow.yaml.

    Args:
        settings_file: Path to nornflow.yaml.
        updates: Top-level keys to set or replace.
    """
    data = yaml.safe_load(settings_file.read_text()) or {}
    data.update(updates)
    settings_file.write_text(yaml.safe_dump(data, sort_keys=True))


def run_nornflow_init(nornflow_executable: Path, project_root: Path) -> None:
    """Run ``nornflow init`` non-interactively in project_root.

    Args:
        nornflow_executable: Path to nornflow CLI (venv or dev install).
        project_root: Empty or new directory for the project.

    Raises:
        RuntimeError: When init exits non-zero.
    """
    project_root.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [str(nornflow_executable), "init"],
        cwd=str(project_root),
        input="y\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"nornflow init failed ({result.returncode}): {detail}")


def bootstrap_nornflow_project(
    project_root: Path,
    *,
    nornflow_executable: Path,
    overlay_dirs: list[Path],
    settings_patch: dict[str, object] | None = None,
    write_hosts: Callable[[Path], None] | None = None,
) -> Path:
    """Skeleton a project with init, merge static fixtures, and optional patches.

    Args:
        project_root: Target project directory.
        nornflow_executable: nornflow CLI used for init.
        overlay_dirs: Overlay trees applied in order (later wins on collision).
        settings_patch: Optional nornflow.yaml keys to merge after init.
        write_hosts: Optional callback receiving hosts.yaml path for lab inventory.

    Returns:
        Path to nornflow.yaml.
    """
    run_nornflow_init(nornflow_executable, project_root)

    for overlay in overlay_dirs:
        merge_overlay(overlay, project_root)

    settings_file = project_root / "nornflow.yaml"
    if settings_patch:
        patch_nornflow_settings(settings_file, settings_patch)

    if write_hosts:
        write_hosts(project_root / "nornir_configs" / "hosts.yaml")

    return settings_file
