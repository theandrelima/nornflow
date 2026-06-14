import logging
from types import ModuleType
from unittest.mock import patch

import pytest

from nornflow.exceptions import ResourceError
from nornflow.packages.descriptor import PackageDescriptor
from nornflow.packages.loader import PackageLoader

LOGGER_NAME = "nornflow"


class TestPackageLoaderInit:
    """Tests for PackageLoader construction."""

    def test_accepts_empty_descriptors(self):
        loader = PackageLoader([])
        assert loader.get_resource_dirs("tasks") == []

    def test_stores_descriptors(self):
        descs = [PackageDescriptor(name="a"), PackageDescriptor(name="b")]

        mod_a = ModuleType("a")
        mod_a.__file__ = "/fake/a/__init__.py"
        mod_b = ModuleType("b")
        mod_b.__file__ = "/fake/b/__init__.py"

        def import_side_effect(name):
            return {"a": mod_a, "b": mod_b}[name]

        with patch("nornflow.packages.loader.importlib.import_module", side_effect=import_side_effect):
            loader = PackageLoader(descs)

        assert loader._descriptors is descs


class TestResolveResourceDir:
    """Tests for PackageLoader._resolve_resource_dir()."""

    def test_returns_path_when_subdir_exists(self, fake_package_dir):
        desc = PackageDescriptor(name="fake_pkg")

        fake_module = ModuleType("fake_pkg")
        fake_module.__file__ = str(fake_package_dir / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            result = loader._resolve_resource_dir("fake_pkg", "tasks")

        assert result is not None
        assert result == fake_package_dir / "tasks"
        assert result.is_dir()

    def test_returns_none_when_subdir_missing(self, fake_package_dir):
        desc = PackageDescriptor(name="fake_pkg")

        fake_module = ModuleType("fake_pkg")
        fake_module.__file__ = str(fake_package_dir / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            result = loader._resolve_resource_dir("fake_pkg", "processors")

        assert result is None

    def test_raises_on_import_error(self):
        desc = PackageDescriptor(name="nonexistent_pkg")

        with patch("nornflow.packages.loader.importlib.import_module", side_effect=ImportError("nope")):
            with pytest.raises(ResourceError, match="could not be imported"):
                PackageLoader([desc])

    def test_namespace_package_skipped_with_warning(self, caplog):
        desc = PackageDescriptor(name="ns_pkg")

        fake_module = ModuleType("ns_pkg")
        fake_module.__file__ = None

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
                loader = PackageLoader([desc])

        assert any("namespace" in msg.lower() for msg in caplog.messages)
        assert loader.get_resource_dirs("tasks") == []

    def test_namespace_package_warned_once(self, caplog):
        desc = PackageDescriptor(name="ns_pkg")

        fake_module = ModuleType("ns_pkg")
        fake_module.__file__ = None

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
                loader = PackageLoader([desc])
                loader.get_resource_dirs("tasks")
                loader.get_resource_dirs("workflows")
                loader.get_resource_dirs("hooks")

        namespace_warnings = [msg for msg in caplog.messages if "namespace" in msg.lower()]
        assert len(namespace_warnings) == 1


class TestGetResourceDirs:
    """Tests for PackageLoader.get_resource_dirs()."""

    def test_returns_dirs_for_matching_descriptors(self, fake_package_dir):
        desc = PackageDescriptor(name="fake_pkg")

        fake_module = ModuleType("fake_pkg")
        fake_module.__file__ = str(fake_package_dir / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            result = loader.get_resource_dirs("tasks")

        assert len(result) == 1
        pkg_name, pkg_path = result[0]
        assert pkg_name == "fake_pkg"
        assert pkg_path == fake_package_dir / "tasks"

    def test_skips_descriptors_that_dont_include_resource_type(self, fake_package_dir):
        desc = PackageDescriptor(name="fake_pkg", include=["hooks"])

        fake_module = ModuleType("fake_pkg")
        fake_module.__file__ = str(fake_package_dir / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            result = loader.get_resource_dirs("tasks")

        assert result == []

    def test_returns_empty_when_subdir_missing_and_not_explicit(self, fake_package_dir):
        desc = PackageDescriptor(name="fake_pkg")

        fake_module = ModuleType("fake_pkg")
        fake_module.__file__ = str(fake_package_dir / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            result = loader.get_resource_dirs("j2_filters")

        assert result == []

    def test_logs_warning_when_explicit_include_but_dir_missing(self, fake_package_dir, caplog):
        desc = PackageDescriptor(name="fake_pkg", include=["j2_filters"])

        fake_module = ModuleType("fake_pkg")
        fake_module.__file__ = str(fake_package_dir / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
                result = loader.get_resource_dirs("j2_filters")

        assert result == []
        assert any(
            "explicitly listed" in msg and "j2_filters" in msg
            for msg in caplog.messages
        )

    def test_logs_debug_when_implicit_include_and_dir_missing(self, fake_package_dir, caplog):
        desc = PackageDescriptor(name="fake_pkg")

        fake_module = ModuleType("fake_pkg")
        fake_module.__file__ = str(fake_package_dir / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
                result = loader.get_resource_dirs("processors")

        assert result == []
        assert any("Skipping processors" in msg for msg in caplog.messages)

    def test_multiple_descriptors_multiple_dirs(self, tmp_path):
        pkg_a = tmp_path / "pkg_a"
        pkg_a.mkdir()
        (pkg_a / "__init__.py").write_text("")
        (pkg_a / "tasks").mkdir()

        pkg_b = tmp_path / "pkg_b"
        pkg_b.mkdir()
        (pkg_b / "__init__.py").write_text("")
        (pkg_b / "tasks").mkdir()

        desc_a = PackageDescriptor(name="pkg_a")
        desc_b = PackageDescriptor(name="pkg_b")

        mod_a = ModuleType("pkg_a")
        mod_a.__file__ = str(pkg_a / "__init__.py")
        mod_b = ModuleType("pkg_b")
        mod_b.__file__ = str(pkg_b / "__init__.py")

        def import_side_effect(name):
            if name == "pkg_a":
                return mod_a
            if name == "pkg_b":
                return mod_b
            raise ImportError(f"No module named '{name}'")

        with patch("nornflow.packages.loader.importlib.import_module", side_effect=import_side_effect):
            loader = PackageLoader([desc_a, desc_b])
            result = loader.get_resource_dirs("tasks")

        assert len(result) == 2
        assert result[0][0] == "pkg_a"
        assert result[1][0] == "pkg_b"

    def test_preserves_descriptor_order(self, tmp_path):
        dirs = {}
        for name in ["charlie", "alpha", "bravo"]:
            pkg = tmp_path / name
            pkg.mkdir()
            (pkg / "__init__.py").write_text("")
            (pkg / "tasks").mkdir()
            dirs[name] = pkg

        descs = [PackageDescriptor(name=n) for n in ["charlie", "alpha", "bravo"]]

        modules = {}
        for name, pkg_dir in dirs.items():
            mod = ModuleType(name)
            mod.__file__ = str(pkg_dir / "__init__.py")
            modules[name] = mod

        def import_side_effect(name):
            if name in modules:
                return modules[name]
            raise ImportError(f"No module named '{name}'")

        with patch("nornflow.packages.loader.importlib.import_module", side_effect=import_side_effect):
            loader = PackageLoader(descs)
            result = loader.get_resource_dirs("tasks")

        names = [pkg_name for pkg_name, _ in result]
        assert names == ["charlie", "alpha", "bravo"]

    def test_import_error_propagates(self):
        desc = PackageDescriptor(name="broken_pkg")

        with patch(
            "nornflow.packages.loader.importlib.import_module",
            side_effect=ImportError("cannot find"),
        ):
            with pytest.raises(ResourceError, match="could not be imported"):
                PackageLoader([desc])

    def test_mixed_existing_and_missing_dirs(self, tmp_path):
        pkg = tmp_path / "mixed_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "tasks").mkdir()

        desc = PackageDescriptor(name="mixed_pkg")

        fake_module = ModuleType("mixed_pkg")
        fake_module.__file__ = str(pkg / "__init__.py")

        with patch("nornflow.packages.loader.importlib.import_module", return_value=fake_module):
            loader = PackageLoader([desc])
            tasks_result = loader.get_resource_dirs("tasks")
            filters_result = loader.get_resource_dirs("filters")

        assert len(tasks_result) == 1
        assert filters_result == []
