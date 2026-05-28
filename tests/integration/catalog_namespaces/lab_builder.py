"""Build a self-contained NornFlow project lab for namespace integration tests."""

from dataclasses import dataclass
from pathlib import Path

from nornflow.packages.descriptor import PackageDescriptor
from nornflow.settings import NornFlowSettings

PKG_ALPHA = "nornflow_integ_pkg_alpha"
PKG_BETA = "nornflow_integ_pkg_beta"

SHARED_TASK = "integ_shared"
PKG_ONLY_TASK = "pkg_only_shared"
ECHO_TASK = "echo"

SHARED_FILTER = "integ_shared"
PKG_ONLY_FILTER = "pkg_only_shared"
GROUPS_FILTER = "groups"

SHARED_HOOK = "integ_shared"
PKG_ONLY_HOOK = "pkg_only_shared"

SHARED_J2 = "integ_shared"
PKG_ONLY_J2 = "pkg_only_shared"

SHARED_WORKFLOW = "integ_shared.yaml"
PKG_ONLY_WORKFLOW = "pkg_only_shared.yaml"
DOTTED_WORKFLOW = "deploy.integ.yaml"

SHARED_BLUEPRINT = "integ_shared.yaml"
PKG_ONLY_BLUEPRINT = "pkg_only_shared.yaml"


@dataclass(frozen=True)
class IntegrationLab:
    """Paths and settings for a namespace collision lab.

    Attributes:
        root: Root directory of the generated lab layout.
        settings: NornFlowSettings wired to local dirs and fixture packages.
        pkg_alpha: Import path of the first fixture package.
        pkg_beta: Import path of the second fixture package.
    """

    root: Path
    settings: NornFlowSettings
    pkg_alpha: str = PKG_ALPHA
    pkg_beta: str = PKG_BETA


def _write_task(path: Path, func_name: str, marker: str) -> None:
    path.write_text(
        f'''\
from nornir.core.task import Result, Task


def {func_name}(task: Task) -> Result:
    """Integration fixture task ({marker})."""
    return Result(host=task.host, result="{marker}")
'''
    )


def _write_filter(path: Path, func_name: str, marker: str) -> None:
    path.write_text(
        f'''\
from nornir.core.inventory import Host


def {func_name}(host: Host, match: bool = True) -> bool:
    """Integration fixture filter ({marker})."""
    _ = host
    return match
'''
    )


def _write_j2_filter(path: Path, func_name: str, marker: str) -> None:
    path.write_text(
        f'''\
def {func_name}(value: str) -> str:
    """Integration fixture j2 filter ({marker})."""
    return "{marker}:" + str(value)
'''
    )


def _write_hook(path: Path, class_name: str, hook_name: str) -> None:
    path.write_text(
        f'''\
from nornflow.hooks.base import Hook


class {class_name}(Hook):
    """Integration fixture hook."""

    hook_name = "{hook_name}"
'''
    )


def _write_yaml_asset(path: Path, marker: str) -> None:
    path.write_text(
        f"""\
workflow:
  name: {marker}
  inventory_filters:
    hosts: []
    groups: []
  tasks: []
"""
    )


def _write_blueprint(path: Path, marker: str) -> None:
    path.write_text(
        f"""\
description: Integration fixture blueprint ({marker})
tasks: []
"""
    )


def _write_processor(path: Path, marker: str) -> None:
    path.write_text(
        f'''\
"""Integration fixture processor module ({marker})."""

INTEG_MARKER = "{marker}"
'''
    )


def _ensure_package(pkg_root: Path, marker: str) -> None:
    """Create one importable NornFlow package with colliding asset names.

    Args:
        pkg_root: Filesystem root for the package (contains __init__.py).
        marker: Tier marker string stored in generated assets (alpha or beta).
    """
    pkg_root.mkdir(parents=True, exist_ok=True)
    (pkg_root / "__init__.py").write_text(f'"""Integration package ({marker})."""\n')

    tasks = pkg_root / "tasks"
    tasks.mkdir(exist_ok=True)
    (tasks / "__init__.py").write_text("")
    _write_task(tasks / f"{SHARED_TASK}.py", SHARED_TASK, marker)
    _write_task(tasks / f"{PKG_ONLY_TASK}.py", PKG_ONLY_TASK, marker)

    filters = pkg_root / "filters"
    filters.mkdir(exist_ok=True)
    (filters / "__init__.py").write_text("")
    _write_filter(filters / f"{SHARED_FILTER}.py", SHARED_FILTER, marker)
    _write_filter(filters / f"{PKG_ONLY_FILTER}.py", PKG_ONLY_FILTER, marker)

    hooks = pkg_root / "hooks"
    hooks.mkdir(exist_ok=True)
    (hooks / "__init__.py").write_text("")
    _write_hook(hooks / f"{SHARED_HOOK}.py", f"IntegSharedHook{marker.title()}", SHARED_HOOK)
    _write_hook(hooks / f"{PKG_ONLY_HOOK}.py", f"PkgOnlyHook{marker.title()}", PKG_ONLY_HOOK)

    j2_filters = pkg_root / "j2_filters"
    j2_filters.mkdir(exist_ok=True)
    (j2_filters / "__init__.py").write_text("")
    _write_j2_filter(j2_filters / f"{SHARED_J2}.py", SHARED_J2, marker)
    _write_j2_filter(j2_filters / f"{PKG_ONLY_J2}.py", PKG_ONLY_J2, marker)

    workflows = pkg_root / "workflows"
    workflows.mkdir(exist_ok=True)
    _write_yaml_asset(workflows / SHARED_WORKFLOW, marker)
    _write_yaml_asset(workflows / PKG_ONLY_WORKFLOW, marker)
    _write_yaml_asset(workflows / DOTTED_WORKFLOW, marker)

    blueprints = pkg_root / "blueprints"
    blueprints.mkdir(exist_ok=True)
    _write_blueprint(blueprints / SHARED_BLUEPRINT, marker)
    _write_blueprint(blueprints / PKG_ONLY_BLUEPRINT, marker)

    processors = pkg_root / "processors"
    processors.mkdir(exist_ok=True)
    (processors / "__init__.py").write_text("")
    _write_processor(processors / f"proc_{marker}.py", marker)


def _ensure_local(local_root: Path) -> None:
    """Create local-tier assets that collide with builtins and both packages.

    Args:
        local_root: Root directory for all local_* resource folders.
    """
    local_root.mkdir(parents=True, exist_ok=True)

    tasks = local_root / "tasks"
    tasks.mkdir(exist_ok=True)
    _write_task(tasks / f"{SHARED_TASK}.py", SHARED_TASK, "local")
    _write_task(tasks / f"{ECHO_TASK}.py", ECHO_TASK, "local")

    filters = local_root / "filters"
    filters.mkdir(exist_ok=True)
    _write_filter(filters / f"{SHARED_FILTER}.py", SHARED_FILTER, "local")
    _write_filter(filters / f"{GROUPS_FILTER}.py", GROUPS_FILTER, "local")

    hooks = local_root / "hooks"
    hooks.mkdir(exist_ok=True)
    _write_hook(hooks / f"{SHARED_HOOK}.py", "IntegSharedHookLocal", SHARED_HOOK)

    j2_filters = local_root / "j2_filters"
    j2_filters.mkdir(exist_ok=True)
    _write_j2_filter(j2_filters / f"{SHARED_J2}.py", SHARED_J2, "local")

    workflows = local_root / "workflows"
    workflows.mkdir(exist_ok=True)
    _write_yaml_asset(workflows / SHARED_WORKFLOW, "local")
    _write_yaml_asset(workflows / DOTTED_WORKFLOW, "local")

    blueprints = local_root / "blueprints"
    blueprints.mkdir(exist_ok=True)
    _write_blueprint(blueprints / SHARED_BLUEPRINT, "local")


def _write_nornir_config(lab_root: Path) -> Path:
    """Write a minimal Nornir config tree for NornFlow initialization.

    Args:
        lab_root: Lab root directory.

    Returns:
        Path to the generated config.yaml file.
    """
    config_dir = lab_root / "nornir"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "hosts.yaml").write_text("{}\n")
    (config_dir / "groups.yaml").write_text("{}\n")
    (config_dir / "defaults.yaml").write_text("{}\n")
    config_file = config_dir / "config.yaml"
    config_file.write_text(
        """\
inventory:
  plugin: SimpleInventory
  options:
    host_file: 'hosts.yaml'
    group_file: 'groups.yaml'
    defaults_file: 'defaults.yaml'
runner:
  plugin: threaded
  options:
    num_workers: 1
"""
    )
    return config_file


def build_integration_lab(lab_root: Path) -> IntegrationLab:
    """Create local dirs, two importable packages, and NornFlow settings.

    Args:
        lab_root: Directory where the full lab layout is written.

    Returns:
        IntegrationLab with absolute paths and ready-to-use settings.
    """
    lab_root.mkdir(parents=True, exist_ok=True)

    packages_dir = lab_root / "packages"
    packages_dir.mkdir(exist_ok=True)
    _ensure_package(packages_dir / PKG_ALPHA, "alpha")
    _ensure_package(packages_dir / PKG_BETA, "beta")

    local_root = lab_root / "local"
    _ensure_local(local_root)

    config_file = _write_nornir_config(lab_root)

    settings = NornFlowSettings(
        nornir_config_file=str(config_file),
        local_tasks=[str(local_root / "tasks")],
        local_filters=[str(local_root / "filters")],
        local_hooks=[str(local_root / "hooks")],
        local_j2_filters=[str(local_root / "j2_filters")],
        local_workflows=[str(local_root / "workflows")],
        local_blueprints=[str(local_root / "blueprints")],
        packages=[
            PackageDescriptor(name=PKG_ALPHA),
            PackageDescriptor(name=PKG_BETA),
        ],
    )

    return IntegrationLab(root=lab_root, settings=settings)
