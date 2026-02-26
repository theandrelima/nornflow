from pathlib import Path

import pytest

from nornflow.packages.descriptor import PackageDescriptor
from nornflow.packages.loader import PackageLoader


@pytest.fixture
def descriptor_all() -> PackageDescriptor:
    """Descriptor with no include filter (imports everything)."""
    return PackageDescriptor(name="nornflow_extras")


@pytest.fixture
def descriptor_tasks_only() -> PackageDescriptor:
    """Descriptor that explicitly includes only tasks."""
    return PackageDescriptor(name="nornflow_extras", include=["tasks"])


@pytest.fixture
def descriptor_multiple_includes() -> PackageDescriptor:
    """Descriptor that explicitly includes tasks, hooks, and workflows."""
    return PackageDescriptor(name="nornflow_extras", include=["tasks", "hooks", "workflows"])


@pytest.fixture
def fake_package_dir(tmp_path) -> Path:
    """Create a fake installed package directory with some resource subdirs."""
    pkg_root = tmp_path / "fake_pkg"
    pkg_root.mkdir()
    (pkg_root / "__init__.py").write_text("")

    (pkg_root / "tasks").mkdir()
    (pkg_root / "tasks" / "__init__.py").write_text("")
    (pkg_root / "tasks" / "my_task.py").write_text("def my_task(task): pass")

    (pkg_root / "workflows").mkdir()
    (pkg_root / "workflows" / "sample.yaml").write_text("name: sample")

    (pkg_root / "hooks").mkdir()
    (pkg_root / "hooks" / "__init__.py").write_text("")

    return pkg_root


@pytest.fixture
def loader_with_one_descriptor(descriptor_all) -> PackageLoader:
    """PackageLoader initialized with a single import-all descriptor."""
    return PackageLoader([descriptor_all])


@pytest.fixture
def loader_with_tasks_only(descriptor_tasks_only) -> PackageLoader:
    """PackageLoader initialized with a single tasks-only descriptor."""
    return PackageLoader([descriptor_tasks_only])
