"""Subprocess entrypoint for containerlab catalog validation (Phase B)."""

import sys
from pathlib import Path

import nornflow.builtins.hooks  # noqa: F401 — populate builtin hooks in HOOKS_CATALOG
from nornflow.constants import BUILTIN_NAMESPACE
from nornflow.hooks import HOOKS_CATALOG
from nornflow.nornflow import NornFlow
from nornflow.settings import NornFlowSettings

from tests.integration.containerlab.constants import (
    LAB_INTEGRATION_WORKFLOW,
    LAB_READONLY_BLUEPRINT,
    NORNFLOW_ARISTA_PACKAGE,
)


def _assert_key(catalog: object, key: str, label: str) -> None:
    if key not in catalog:
        raise RuntimeError(f"Expected {label} catalog key missing: {key}")


def run_phase_b(settings_file: Path) -> None:
    """Verify all relevant catalogs load with namespace-qualified assets.

    Args:
        settings_file: Path to generated nornflow.yaml.
    """
    settings = NornFlowSettings.load(str(settings_file), base_dir=settings_file.parent)
    nornflow = NornFlow(nornflow_settings=settings)

    tasks = nornflow.tasks_catalog
    _assert_key(tasks, f"{BUILTIN_NAMESPACE}.set", "tasks")
    _assert_key(tasks, f"{BUILTIN_NAMESPACE}.echo", "tasks")
    _assert_key(tasks, f"{NORNFLOW_ARISTA_PACKAGE}.get_facts", "tasks")
    _assert_key(tasks, f"{NORNFLOW_ARISTA_PACKAGE}.get_lldp_neighbors", "tasks")
    tasks.resolve("nornflow.set")
    tasks.resolve("nornflow_arista.get_facts")

    filters = nornflow.filters_catalog
    _assert_key(filters, f"{BUILTIN_NAMESPACE}.groups", "filters")
    filters.resolve("nornflow.groups")

    workflows = nornflow.workflows_catalog
    _assert_key(workflows, f"local.{LAB_INTEGRATION_WORKFLOW}", "workflows")
    _assert_key(workflows, f"{NORNFLOW_ARISTA_PACKAGE}.daily_snapshot.yaml", "workflows")

    blueprints = nornflow.blueprints_catalog
    _assert_key(blueprints, f"local.{LAB_READONLY_BLUEPRINT}", "blueprints")
    _assert_key(blueprints, f"{NORNFLOW_ARISTA_PACKAGE}.state_snapshot.yaml", "blueprints")

    j2_catalog = nornflow.j2_filters_catalog
    _assert_key(j2_catalog, f"{NORNFLOW_ARISTA_PACKAGE}.eos_vlan_expand", "j2_filters")
    _assert_key(j2_catalog, f"{NORNFLOW_ARISTA_PACKAGE}.eos_intf_canonical", "j2_filters")
    j2_catalog.resolve("nornflow_arista.eos_vlan_expand")

    for hook_name in ("if", "single", "set_to"):
        _assert_key(HOOKS_CATALOG, f"{BUILTIN_NAMESPACE}.{hook_name}", "hooks")

    print(
        "Phase B OK: tasks, filters, workflows, blueprints, j2_filters, and hooks "
        "catalogs loaded with nornflow + nornflow_arista assets"
    )


def main(argv: list[str]) -> int:
    """Dispatch a lab runner phase.

    Args:
        argv: CLI arguments (phase name, settings file path).

    Returns:
        Process exit code (0 success, 1 failure).
    """
    if len(argv) != 3:
        print(f"Usage: {argv[0]} phase-b <nornflow.yaml>", file=sys.stderr)
        return 1

    phase = argv[1]
    settings_file = Path(argv[2]).resolve()

    if phase != "phase-b":
        print(f"Unknown phase: {phase}", file=sys.stderr)
        return 1

    try:
        run_phase_b(settings_file)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
