"""Unit tests for catalog namespace isolation and registration."""

from pathlib import Path
from unittest.mock import patch

import pytest

from nornflow.builtins.tasks import set as builtin_set_task
from nornflow.catalogs import (
    BUILTIN_NAMESPACE,
    LOCAL_NAMESPACE,
    TIER_BUILTIN,
    TIER_LOCAL,
    TIER_PACKAGE,
    CallableCatalog,
    ClassCatalog,
    FileCatalog,
)
from nornflow.exceptions import AssetAmbiguityError, AssetNotFoundError, CoreError


class TestCatalogNamespaceResolution:
    """Tests for bare vs qualified resolution and tier priority."""

    def test_builtin_bare_resolution(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register(
            "set",
            builtin_set_task,
            module_name="nornflow.builtins.tasks",
            namespace=BUILTIN_NAMESPACE,
            tier=TIER_BUILTIN,
        )
        catalog.finalize_package_tier()

        assert catalog.resolve("set") is builtin_set_task
        assert catalog.resolve("nornflow.set") is builtin_set_task

    def test_local_reuses_builtin_name_via_qualified_only(self):
        catalog = CallableCatalog(name="tasks")

        def custom_set(task):
            return "custom"

        catalog.register(
            "set",
            builtin_set_task,
            module_name="nornflow.builtins.tasks",
            namespace=BUILTIN_NAMESPACE,
            tier=TIER_BUILTIN,
        )
        catalog.register(
            "set",
            custom_set,
            module_name="custom.module",
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )
        catalog.finalize_package_tier()
        catalog.compute_collision_metadata()

        assert catalog.resolve("set") is builtin_set_task
        assert catalog.resolve("local.set") is custom_set
        assert "local" in catalog.sources["nornflow.set"]["collision"]

    def test_local_wins_bare_over_package(self):
        catalog = CallableCatalog(name="tasks")

        def local_backup(task):
            return "local"

        def pkg_backup(task):
            return "package"

        catalog.register("backup", local_backup, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        catalog.register("backup", pkg_backup, namespace="nornflow_arista", tier=TIER_PACKAGE)
        catalog.finalize_package_tier()
        catalog.compute_collision_metadata()

        assert catalog.resolve("backup") is local_backup
        assert catalog.resolve("nornflow_arista.backup") is pkg_backup

    def test_package_vs_package_bare_ambiguity(self):
        catalog = CallableCatalog(name="tasks")

        def arista(task):
            return "arista"

        def cisco(task):
            return "cisco"

        catalog.register("get_facts", arista, namespace="nornflow_arista", tier=TIER_PACKAGE)
        catalog.register("get_facts", cisco, namespace="nornflow_cisco", tier=TIER_PACKAGE)
        catalog.finalize_package_tier()
        catalog.compute_collision_metadata()

        assert catalog.resolve("nornflow_arista.get_facts") is arista
        assert catalog.resolve("nornflow_cisco.get_facts") is cisco
        with pytest.raises(AssetAmbiguityError):
            catalog.resolve("get_facts")
        assert "(bare ambiguous)" in catalog.sources["nornflow_arista.get_facts"]["collision"]

    def test_qualified_not_found_raises(self):
        catalog = CallableCatalog(name="tasks")
        catalog.finalize_package_tier()

        with pytest.raises(AssetNotFoundError):
            catalog.resolve("missing.task")

    def test_contains_supports_bare_and_qualified(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register(
            "echo",
            lambda t: t,
            namespace=BUILTIN_NAMESPACE,
            tier=TIER_BUILTIN,
        )
        catalog.finalize_package_tier()

        assert "echo" in catalog
        assert "nornflow.echo" in catalog
        assert "missing" not in catalog

    def test_get_unambiguous_bare_names_excludes_ambiguous(self):
        catalog = CallableCatalog(name="tasks")

        def arista(task):
            return "arista"

        def cisco(task):
            return "cisco"

        catalog.register("get_facts", arista, namespace="nornflow_arista", tier=TIER_PACKAGE)
        catalog.register("get_facts", cisco, namespace="nornflow_cisco", tier=TIER_PACKAGE)
        catalog.register("unique", lambda t: t, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        catalog.finalize_package_tier()

        unambiguous = catalog.get_unambiguous_bare_names()
        assert "unique" in unambiguous
        assert "get_facts" not in unambiguous


class TestCallableCatalogRegistration:
    """Tests for callable catalog registration helpers."""

    def test_register_builtin_task_success(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register(
            "set",
            builtin_set_task,
            module_name="nornflow.builtins.tasks",
            namespace=BUILTIN_NAMESPACE,
            tier=TIER_BUILTIN,
        )
        assert "nornflow.set" in catalog
        assert catalog.sources["nornflow.set"]["is_builtin"] is True

    def test_register_custom_task_success(self):
        catalog = CallableCatalog(name="tasks")

        def custom_task(task):
            return "ok"

        catalog.register(
            "custom_task",
            custom_task,
            module_name="custom.module",
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )
        assert "local.custom_task" in catalog
        assert catalog.sources["local.custom_task"]["is_builtin"] is False

    def test_same_namespace_last_write_wins(self):
        catalog = CallableCatalog(name="tasks")

        def first(task):
            return "first"

        def second(task):
            return "second"

        catalog.register("dup", first, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        catalog.register("dup", second, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)

        assert catalog["local.dup"] is second

    def test_get_builtin_and_custom_items(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register(
            "set",
            builtin_set_task,
            module_name="nornflow.builtins.tasks",
            namespace=BUILTIN_NAMESPACE,
            tier=TIER_BUILTIN,
        )
        catalog.register(
            "custom",
            lambda x: x,
            module_name="custom.module",
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )

        assert "nornflow.set" in catalog.get_builtin_items()
        assert "local.custom" in catalog.get_custom_items()

    @patch("nornflow.catalogs.import_module_from_path")
    def test_discover_items_in_dir_success(self, mock_import):
        mock_module = type("MockModule", (), {"task1": lambda: None, "task2": lambda: None})()
        mock_import.return_value = mock_module

        catalog = CallableCatalog(name="tasks")
        with patch("pathlib.Path.is_dir", return_value=True), patch(
            "pathlib.Path.rglob", return_value=[Path("test.py")]
        ):
            count = catalog.discover_items_in_dir(
                "dummy_dir", namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL
            )
            assert count > 0

    @patch("nornflow.catalogs.import_module_from_path")
    def test_discover_items_in_dir_import_failure(self, mock_import):
        mock_import.side_effect = Exception("Import error")

        catalog = CallableCatalog(name="tasks")
        with patch("pathlib.Path.is_dir", return_value=True), patch(
            "pathlib.Path.rglob", return_value=[Path("test.py")]
        ):
            with pytest.raises(CoreError, match="Failed to import module"):
                catalog.discover_items_in_dir("dummy_dir")


class TestClassCatalog:
    """Tests for ClassCatalog metadata and registration."""

    def test_register_class_builtin_from_module_origin(self):
        catalog = ClassCatalog(name="hooks")

        class FakeBuiltin:
            pass

        FakeBuiltin.__module__ = "nornflow.builtins.hooks.fake"
        catalog.register("fake_builtin", FakeBuiltin)
        assert catalog.sources["nornflow.fake_builtin"]["is_builtin"] is True

    def test_register_class_custom_namespace(self):
        catalog = ClassCatalog(name="hooks")

        class UserHook:
            pass

        UserHook.__module__ = "mypkg.hooks.custom"
        catalog.register("user_hook", UserHook, namespace="mypkg", tier=TIER_PACKAGE)
        assert "mypkg.user_hook" in catalog
        assert catalog.sources["mypkg.user_hook"]["is_builtin"] is False

    def test_same_bare_different_namespaces_allowed(self):
        catalog = ClassCatalog(name="hooks")

        class First:
            pass

        class Second:
            pass

        catalog.register("clash", First, namespace="pkg_a", tier=TIER_PACKAGE)
        catalog.register("clash", Second, namespace="pkg_b", tier=TIER_PACKAGE)
        catalog.finalize_package_tier()

        assert catalog["pkg_a.clash"] is First
        assert catalog["pkg_b.clash"] is Second


class TestFileCatalog:
    """Tests for FileCatalog functionality."""

    def test_discover_items_in_dir_success(self, tmp_path):
        catalog = FileCatalog(name="workflows")

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("content")
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        count = catalog.discover_items_in_dir(
            str(tmp_path),
            predicate=lambda path: path.suffix == ".yaml",
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )
        assert count == 1
        assert "local.test.yaml" in catalog

    def test_package_and_local_same_filename(self, tmp_path):
        catalog = FileCatalog(name="workflows")

        local_file = tmp_path / "wf.yaml"
        local_file.write_text("local")
        pkg_file = tmp_path / "pkg_wf.yaml"
        pkg_file.write_text("pkg")

        catalog.register("wf.yaml", local_file, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        catalog.register(
            "wf.yaml",
            pkg_file,
            namespace="my_pkg",
            tier=TIER_PACKAGE,
            is_package=True,
        )
        catalog.finalize_package_tier()
        catalog.compute_collision_metadata()

        assert catalog.resolve("wf.yaml") == local_file
        assert catalog.resolve("my_pkg.wf.yaml") == pkg_file

    def test_get_package_names_returns_qualified_keys(self, tmp_path):
        catalog = FileCatalog(name="blueprints")

        pkg_file = tmp_path / "pkg_bp.yaml"
        pkg_file.write_text("content")
        local_file = tmp_path / "local_bp.yaml"
        local_file.write_text("content")

        catalog.register(
            "pkg_bp.yaml",
            pkg_file,
            namespace="my_pkg",
            tier=TIER_PACKAGE,
            is_package=True,
        )
        catalog.register(
            "local_bp.yaml",
            local_file,
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )

        result = catalog.get_package_names()
        assert "my_pkg.pkg_bp.yaml" in result
        assert "local.local_bp.yaml" not in result


class TestCatalogBaseHelpers:
    """Tests for Catalog base helper methods."""

    def test_is_empty_true_on_fresh_catalog(self):
        catalog = CallableCatalog(name="tasks")
        assert catalog.is_empty is True

    def test_get_item_info_returns_none_for_missing(self):
        catalog = CallableCatalog(name="tasks")
        assert catalog.get_item_info("nonexistent") is None

    def test_get_item_info_includes_qualified_name(self):
        catalog = CallableCatalog(name="tasks")
        fn = lambda t: t
        catalog.register("my_task", fn, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        info = catalog.get_item_info("local.my_task")
        assert info["name"] == "local.my_task"
        assert info["value"] is fn

    def test_items_with_info_returns_triples(self):
        catalog = CallableCatalog(name="tasks")
        fn = lambda t: t
        catalog.register("task_x", fn, namespace=LOCAL_NAMESPACE, tier=TIER_LOCAL)
        triples = catalog.items_with_info()
        assert len(triples) == 1
        name, value, meta = triples[0]
        assert name == "local.task_x"
        assert value is fn
        assert meta["namespace"] == LOCAL_NAMESPACE


class TestCallableCatalogRegisterFromModule:
    """Tests for CallableCatalog.register_from_module()."""

    def test_registers_with_namespace(self):
        catalog = CallableCatalog(name="tasks")

        mod = type(
            "FakeMod",
            (),
            {
                "__file__": "/fake/mod.py",
                "__name__": "fake_mod",
                "good_task": lambda task: None,
            },
        )()

        catalog.register_from_module(
            mod,
            predicate=callable,
            namespace="my_pkg",
            tier=TIER_PACKAGE,
        )
        assert "my_pkg.good_task" in catalog

    def test_transform_item_is_applied(self):
        catalog = CallableCatalog(name="filters")

        original = lambda host: host
        transformed = ("wrapped", original)

        mod = type(
            "FakeMod",
            (),
            {
                "__file__": "/fake/mod.py",
                "__name__": "fake_mod",
                "my_filter": original,
            },
        )()

        catalog.register_from_module(
            mod,
            predicate=callable,
            transform_item=lambda fn: transformed,
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )
        assert catalog["local.my_filter"] == transformed

    def test_get_sources_by_module_groups_qualified_keys(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register(
            "t1",
            lambda t: t,
            module_name="pkg.a",
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )
        catalog.register(
            "t2",
            lambda t: t,
            module_name="pkg.a",
            namespace=LOCAL_NAMESPACE,
            tier=TIER_LOCAL,
        )

        result = catalog.get_sources_by_module()
        assert sorted(result["pkg.a"]) == ["local.t1", "local.t2"]
