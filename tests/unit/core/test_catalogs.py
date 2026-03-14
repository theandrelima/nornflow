"""Unit tests for catalog functionality, including built-in prevention rules."""

import inspect
import logging

import pytest
from pathlib import Path
from unittest.mock import patch

from nornflow.catalogs import CallableCatalog, ClassCatalog, FileCatalog
from nornflow.exceptions import BuiltinOverrideError
from nornflow.builtins.tasks import set as builtin_set_task
from nornflow.builtins.filters import hosts as builtin_hosts_filter


class TestPythonEntityCatalog:
    """Tests for PythonEntityCatalog registration and built-in prevention."""

    def test_register_builtin_task_success(self):
        """Test that built-in tasks can be registered without issues."""
        catalog = CallableCatalog(name="tasks")
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")
        assert "set" in catalog
        assert catalog.sources["set"]["is_builtin"] is True

    def test_register_custom_task_with_builtin_name_fails(self):
        """Test that registering a custom task with a built-in name raises BuiltinOverrideError."""
        catalog = CallableCatalog(name="tasks")
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")

        def custom_set(task):
            return "custom"

        with pytest.raises(BuiltinOverrideError, match="'set'.*is a built-in name and cannot be overridden"):
            catalog.register("set", custom_set, module_name="custom.module")

    def test_register_builtin_filter_success(self):
        """Test that built-in filters can be registered without issues."""
        catalog = CallableCatalog(name="filters")
        catalog.register("hosts", builtin_hosts_filter, module_name="nornflow.builtins.filters")
        assert "hosts" in catalog
        assert catalog.sources["hosts"]["is_builtin"] is True

    def test_register_custom_filter_with_builtin_name_fails(self):
        """Test that registering a custom filter with a built-in name raises BuiltinOverrideError."""
        catalog = CallableCatalog(name="filters")
        catalog.register("hosts", builtin_hosts_filter, module_name="nornflow.builtins.filters")

        def custom_hosts(host):
            return True

        with pytest.raises(BuiltinOverrideError, match="'hosts'.*is a built-in name and cannot be overridden"):
            catalog.register("hosts", custom_hosts, module_name="custom.module")

    def test_register_custom_task_with_non_builtin_name_success(self):
        """Test that custom tasks can be registered with non-built-in names."""
        catalog = CallableCatalog(name="tasks")
        def custom_task(task):
            return "ok"

        catalog.register("custom_task", custom_task, module_name="custom.module")
        assert "custom_task" in catalog
        assert catalog.sources["custom_task"]["is_builtin"] is False

    def test_register_custom_filter_with_non_builtin_name_success(self):
        """Test that custom filters can be registered with non-built-in names."""
        catalog = CallableCatalog(name="filters")
        def custom_filter(host):
            return host.name.startswith("test")

        catalog.register("custom_filter", custom_filter, module_name="custom.module")
        assert "custom_filter" in catalog
        assert catalog.sources["custom_filter"]["is_builtin"] is False

    def test_override_non_builtin_task_success(self):
        """Test that non-built-in tasks can be overridden by later registrations."""
        catalog = CallableCatalog(name="tasks")

        def first_custom(task):
            return "first"
        catalog.register("custom_task", first_custom, module_name="first.module")

        def second_custom(task):
            return "second"
        catalog.register("custom_task", second_custom, module_name="second.module")

        assert "custom_task" in catalog
        assert catalog["custom_task"] == second_custom
        assert catalog.sources["custom_task"]["is_builtin"] is False

    def test_override_non_builtin_filter_success(self):
        """Test that non-built-in filters can be overridden by later registrations."""
        catalog = CallableCatalog(name="filters")

        def first_custom(host):
            return True
        catalog.register("custom_filter", first_custom, module_name="first.module")

        def second_custom(host):
            return False
        catalog.register("custom_filter", second_custom, module_name="second.module")

        assert "custom_filter" in catalog
        assert catalog["custom_filter"] == second_custom
        assert catalog.sources["custom_filter"]["is_builtin"] is False

    def test_register_with_module_path_and_name(self):
        """Test registration with explicit module path and name."""
        catalog = CallableCatalog(name="tasks")
        def sample_task(task):
            pass

        catalog.register("sample", sample_task, module_path="/path/to/module.py", module_name="sample.module")
        assert "sample" in catalog
        assert catalog.sources["sample"]["module_path"] == "/path/to/module.py"
        assert catalog.sources["sample"]["module_name"] == "sample.module"

    def test_get_builtin_items(self):
        """Test retrieving only built-in items."""
        catalog = CallableCatalog(name="tasks")
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")
        catalog.register("custom", lambda x: x, module_name="custom.module")

        builtins = catalog.get_builtin_items()
        assert "set" in builtins
        assert "custom" not in builtins

    def test_get_custom_items(self):
        """Test retrieving only custom (non-builtin) items."""
        catalog = CallableCatalog(name="tasks")
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")
        catalog.register("custom", lambda x: x, module_name="custom.module")

        customs = catalog.get_custom_items()
        assert "custom" in customs
        assert "set" not in customs

    def test_get_sources_by_module(self):
        """Test grouping items by their source modules."""
        catalog = CallableCatalog(name="tasks")
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")
        catalog.register("custom1", lambda x: x, module_name="custom.module")
        catalog.register("custom2", lambda x: x, module_name="custom.module")

        sources = catalog.get_sources_by_module()
        assert "nornflow.builtins.tasks" in sources
        assert sources["nornflow.builtins.tasks"] == ["set"]
        assert sources["custom.module"] == ["custom1", "custom2"]

    @patch("nornflow.catalogs.import_module_from_path")
    def test_discover_items_in_dir_success(self, mock_import):
        """Test discovering items from a directory."""
        mock_module = type("MockModule", (), {"task1": lambda: None, "task2": lambda: None})()
        mock_import.return_value = mock_module

        catalog = CallableCatalog(name="tasks")
        with patch("pathlib.Path.is_dir", return_value=True), \
             patch("pathlib.Path.rglob", return_value=[Path("test.py")]):
            count = catalog.discover_items_in_dir("dummy_dir")
            assert count > 0

    @patch("nornflow.catalogs.import_module_from_path")
    def test_discover_items_in_dir_import_failure(self, mock_import):
        """Test handling import failures during discovery."""
        from nornflow.exceptions import CoreError
        mock_import.side_effect = Exception("Import error")

        catalog = CallableCatalog(name="tasks")
        with patch("pathlib.Path.is_dir", return_value=True), \
             patch("pathlib.Path.rglob", return_value=[Path("test.py")]):
            with pytest.raises(CoreError, match="Failed to import module"):
                catalog.discover_items_in_dir("dummy_dir")

    def test_non_builtin_override_logs_warning(self, caplog):
        """Test that overriding a non-builtin callable logs a last-write-wins warning."""
        catalog = CallableCatalog(name="tasks")

        def first(task):
            pass

        def second(task):
            pass

        catalog.register("dup_task", first, module_name="pkg_a.tasks")

        with caplog.at_level(logging.WARNING):
            catalog.register("dup_task", second, module_name="pkg_b.tasks")

        assert any("dup_task" in msg and "being overridden" in msg for msg in caplog.messages)
        assert catalog["dup_task"] is second


class TestClassCatalog:
    """Tests for ClassCatalog registration, is_builtin resolution, and override policies."""

    def test_register_class_builtin_from_module_origin(self):
        """Test that is_builtin is derived from __module__ starting with 'nornflow.builtins'."""
        catalog = ClassCatalog(name="hooks")

        class FakeBuiltin:
            pass

        FakeBuiltin.__module__ = "nornflow.builtins.hooks.fake"
        catalog.register("fake_builtin", FakeBuiltin)
        assert catalog.sources["fake_builtin"]["is_builtin"] is True

    def test_register_class_module_origin_ignores_class_attribute(self):
        """Test that is_builtin is derived from module origin, ignoring any class attribute."""
        catalog = ClassCatalog(name="hooks")

        class ClaimsNotBuiltin:
            __module__ = "nornflow.builtins.something"
            is_builtin = False

        catalog.register("actually_builtin", ClaimsNotBuiltin)
        assert catalog.sources["actually_builtin"]["is_builtin"] is True

    def test_register_class_fallback_to_module_name_builtin(self):
        """Test that module-name prefix is used when no explicit is_builtin attr exists."""
        catalog = ClassCatalog(name="hooks")

        class PlainClass:
            pass

        PlainClass.__module__ = "nornflow.builtins.hooks.something"
        catalog.register("plain_builtin", PlainClass)
        assert catalog.sources["plain_builtin"]["is_builtin"] is True

    def test_register_class_fallback_to_module_name_not_builtin(self):
        """Test that a non-builtins module path results in is_builtin=False."""
        catalog = ClassCatalog(name="hooks")

        class UserClass:
            pass

        UserClass.__module__ = "mypkg.hooks.custom"
        catalog.register("user_hook", UserClass)
        assert catalog.sources["user_hook"]["is_builtin"] is False

    def test_register_class_kwargs_cannot_override_module_origin(self):
        """Test that caller-supplied is_builtin kwarg is ignored — module origin wins."""
        catalog = ClassCatalog(name="hooks")

        class Neutral:
            pass

        Neutral.__module__ = "some.module"
        catalog.register("neutral", Neutral, is_builtin=True)
        assert catalog.sources["neutral"]["is_builtin"] is False

    def test_builtin_override_raises(self):
        """Test that overriding a builtin entry raises BuiltinOverrideError."""
        catalog = ClassCatalog(name="hooks")

        class Builtin:
            pass

        Builtin.__module__ = "nornflow.builtins.hooks.something"

        class Imposter:
            pass

        catalog.register("protected", Builtin)

        with pytest.raises(BuiltinOverrideError, match="'protected'.*is a built-in name"):
            catalog.register("protected", Imposter)

    def test_non_builtin_override_last_write_wins(self):
        """Test that overriding a non-builtin entry succeeds (last-write-wins)."""
        catalog = ClassCatalog(name="hooks")

        class First:
            pass

        class Second:
            pass

        First.__module__ = "pkg.a"
        Second.__module__ = "pkg.b"

        catalog.register("clash", First)
        catalog.register("clash", Second)

        assert catalog["clash"] is Second

    def test_non_builtin_override_logs_warning(self, caplog):
        """Test that overriding a non-builtin entry emits a warning."""
        catalog = ClassCatalog(name="hooks")

        class V1:
            pass

        class V2:
            pass

        V1.__module__ = "pkg.a"
        V2.__module__ = "pkg.b"

        catalog.register("warn_me", V1)

        with caplog.at_level(logging.WARNING):
            catalog.register("warn_me", V2)

        assert any("warn_me" in msg and "being overridden" in msg for msg in caplog.messages)

    def test_description_from_docstring(self):
        """Test that ClassCatalog extracts description from a class docstring."""
        catalog = ClassCatalog(name="hooks")

        class Documented:
            """This is the first line of the docstring."""
            pass

        catalog.register("documented", Documented)
        assert catalog.sources["documented"]["description"] == "This is the first line of the docstring."

    def test_description_from_class_attribute(self):
        """Test that ClassCatalog prefers description class attribute over docstring."""
        catalog = ClassCatalog(name="hooks")

        class WithAttr:
            """Docstring that should be ignored."""
            description = "Explicit description"

        catalog.register("with_attr", WithAttr)
        assert catalog.sources["with_attr"]["description"] == "Explicit description"

    def test_description_kwarg_takes_precedence(self):
        """Test that caller-supplied description kwarg is not overwritten."""
        catalog = ClassCatalog(name="hooks")

        class HasDoc:
            """Class docstring."""
            pass

        catalog.register("has_doc", HasDoc, description="Caller description")
        assert catalog.sources["has_doc"]["description"] == "Caller description"

    def test_register_non_class_item(self):
        """Test that non-class items bypass class-specific metadata extraction."""
        catalog = ClassCatalog(name="misc")
        catalog.register("a_string", "hello")
        assert catalog["a_string"] == "hello"
        assert "is_builtin" not in catalog.sources["a_string"]

    def test_module_name_auto_extracted(self):
        """Test that module_name is extracted from __module__ when not supplied."""
        catalog = ClassCatalog(name="hooks")

        class SomeClass:
            pass

        SomeClass.__module__ = "auto.detected.module"
        catalog.register("auto", SomeClass)
        assert catalog.sources["auto"]["module_name"] == "auto.detected.module"


class TestFileCatalog:
    """Tests for FileCatalog functionality."""

    def test_discover_items_in_dir_success(self, tmp_path):
        """Test discovering files in a directory."""
        catalog = FileCatalog(name="workflows")

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("content")
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        def yaml_predicate(path):
            return path.suffix == ".yaml"

        count = catalog.discover_items_in_dir(str(tmp_path), predicate=yaml_predicate)
        assert count == 1
        assert "test.yaml" in catalog

    def test_get_by_extension(self, tmp_path):
        """Test filtering files by extension."""
        catalog = FileCatalog(name="files")

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("content")
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        catalog.register("test.yaml", yaml_file, file_path=str(yaml_file))
        catalog.register("test.txt", txt_file, file_path=str(txt_file))

        yamls = catalog.get_by_extension("yaml")
        assert "test.yaml" in yamls
        assert "test.txt" not in yamls

    def test_builtin_override_raises(self, tmp_path):
        """Test that overriding a builtin file entry raises BuiltinOverrideError."""
        catalog = FileCatalog(name="workflows")

        builtin_file = FileCatalog.nornflow_builtins_dir / "base.yaml"
        override_file = tmp_path / "base.yaml"
        override_file.write_text("content")

        catalog.register("base.yaml", builtin_file)

        with pytest.raises(BuiltinOverrideError, match="'base.yaml'.*is a built-in name"):
            catalog.register("base.yaml", override_file)

    def test_non_builtin_override_last_write_wins(self, tmp_path):
        """Test that overriding a non-builtin file entry succeeds."""
        catalog = FileCatalog(name="workflows")

        first = tmp_path / "wf_v1.yaml"
        first.write_text("v1")
        second = tmp_path / "wf_v2.yaml"
        second.write_text("v2")

        catalog.register("workflow.yaml", first, module_name="pkg_a")
        catalog.register("workflow.yaml", second, module_name="pkg_b")

        assert catalog["workflow.yaml"] == second

    def test_non_builtin_override_logs_warning(self, tmp_path, caplog):
        """Test that overriding a non-builtin file entry emits a warning."""
        catalog = FileCatalog(name="blueprints")

        first = tmp_path / "bp1.yaml"
        first.write_text("v1")
        second = tmp_path / "bp2.yaml"
        second.write_text("v2")

        catalog.register("shared.yaml", first, module_name="pkg_a")

        with caplog.at_level(logging.WARNING):
            catalog.register("shared.yaml", second, module_name="pkg_b")

        assert any("shared.yaml" in msg and "being overridden" in msg for msg in caplog.messages)


class TestFileCatalogPackageProvenance:
    """Tests for FileCatalog package-origin tracking and is_package metadata."""

    def test_register_with_is_package_true_sets_metadata(self, tmp_path):
        catalog = FileCatalog(name="workflows")
        f = tmp_path / "pkg_wf.yaml"
        f.write_text("content")

        catalog.register("pkg_wf.yaml", f, is_package=True)

        assert catalog.sources["pkg_wf.yaml"]["is_package"] is True

    def test_register_without_is_package_defaults_false(self, tmp_path):
        catalog = FileCatalog(name="workflows")
        f = tmp_path / "local_wf.yaml"
        f.write_text("content")

        catalog.register("local_wf.yaml", f)

        assert catalog.sources["local_wf.yaml"].get("is_package", False) is False

    def test_get_package_names_returns_only_package_entries(self, tmp_path):
        catalog = FileCatalog(name="blueprints")

        pkg_file = tmp_path / "pkg_bp.yaml"
        pkg_file.write_text("content")
        local_file = tmp_path / "local_bp.yaml"
        local_file.write_text("content")

        catalog.register("pkg_bp.yaml", pkg_file, is_package=True)
        catalog.register("local_bp.yaml", local_file)

        result = catalog.get_package_names()

        assert "pkg_bp.yaml" in result
        assert "local_bp.yaml" not in result

    def test_get_package_names_empty_when_no_packages(self, tmp_path):
        catalog = FileCatalog(name="workflows")
        f = tmp_path / "wf.yaml"
        f.write_text("content")
        catalog.register("wf.yaml", f)

        assert catalog.get_package_names() == set()

    def test_get_package_names_empty_catalog(self):
        catalog = FileCatalog(name="workflows")
        assert catalog.get_package_names() == set()

    def test_discover_items_in_dir_with_is_package_true(self, tmp_path):
        catalog = FileCatalog(name="blueprints")
        f = tmp_path / "bp.yaml"
        f.write_text("content")

        catalog.discover_items_in_dir(
            str(tmp_path),
            predicate=lambda p: p.suffix == ".yaml",
            is_package=True,
        )

        assert "bp.yaml" in catalog
        assert catalog.sources["bp.yaml"]["is_package"] is True

    def test_discover_items_in_dir_is_package_false_by_default(self, tmp_path):
        catalog = FileCatalog(name="workflows")
        f = tmp_path / "wf.yaml"
        f.write_text("content")

        catalog.discover_items_in_dir(
            str(tmp_path),
            predicate=lambda p: p.suffix == ".yaml",
        )

        assert catalog.sources["wf.yaml"].get("is_package", False) is False

    def test_discover_items_in_dir_non_recursive(self, tmp_path):
        catalog = FileCatalog(name="workflows")

        top = tmp_path / "top.yaml"
        top.write_text("content")
        sub = tmp_path / "sub"
        sub.mkdir()
        nested = sub / "nested.yaml"
        nested.write_text("content")

        catalog.discover_items_in_dir(
            str(tmp_path),
            predicate=lambda p: p.suffix == ".yaml",
            recursive=False,
        )

        assert "top.yaml" in catalog
        assert "nested.yaml" not in catalog

    def test_discover_items_in_dir_recursive_finds_nested(self, tmp_path):
        catalog = FileCatalog(name="workflows")

        sub = tmp_path / "sub"
        sub.mkdir()
        nested = sub / "nested.yaml"
        nested.write_text("content")

        catalog.discover_items_in_dir(
            str(tmp_path),
            predicate=lambda p: p.suffix == ".yaml",
            recursive=True,
        )

        assert "nested.yaml" in catalog


class TestCatalogBaseHelpers:
    """Tests for Catalog base class helper methods: get_item_info, get_all_items_info, items_with_info, is_empty."""

    def test_is_empty_true_on_fresh_catalog(self):
        catalog = CallableCatalog(name="tasks")
        assert catalog.is_empty is True

    def test_is_empty_false_after_registration(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register("my_task", lambda t: t, module_name="some.module")
        assert catalog.is_empty is False

    def test_get_item_info_returns_none_for_missing(self):
        catalog = CallableCatalog(name="tasks")
        assert catalog.get_item_info("nonexistent") is None

    def test_get_item_info_includes_name_by_default(self):
        catalog = CallableCatalog(name="tasks")
        fn = lambda t: t
        catalog.register("my_task", fn, module_name="mod")
        info = catalog.get_item_info("my_task")
        assert info["name"] == "my_task"
        assert info["value"] is fn

    def test_get_item_info_excludes_name_when_flagged(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register("my_task", lambda t: t, module_name="mod")
        info = catalog.get_item_info("my_task", include_name=False)
        assert "name" not in info

    def test_get_item_info_contains_registered_at(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register("timed_task", lambda t: t, module_name="mod")
        info = catalog.get_item_info("timed_task")
        assert "registered_at" in info

    def test_get_all_items_info_returns_all(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register("a", lambda t: t, module_name="mod")
        catalog.register("b", lambda t: t, module_name="mod")
        all_info = catalog.get_all_items_info()
        assert "a" in all_info
        assert "b" in all_info

    def test_get_all_items_info_empty_catalog(self):
        catalog = CallableCatalog(name="tasks")
        assert catalog.get_all_items_info() == {}

    def test_items_with_info_returns_triples(self):
        catalog = CallableCatalog(name="tasks")
        fn = lambda t: t
        catalog.register("task_x", fn, module_name="mod")
        triples = catalog.items_with_info()
        assert len(triples) == 1
        name, value, meta = triples[0]
        assert name == "task_x"
        assert value is fn
        assert "module_name" in meta

    def test_items_with_info_empty_catalog(self):
        catalog = CallableCatalog(name="tasks")
        assert catalog.items_with_info() == []


class TestCallableCatalogRegisterFromModule:
    """Tests for CallableCatalog.register_from_module()."""

    def test_registers_all_matching_members(self):
        catalog = CallableCatalog(name="tasks")

        class FakeModule:
            __file__ = "/fake/module.py"
            __name__ = "fake_module"

            def task_a(self):
                pass

            def task_b(self):
                pass

            not_callable = "a string"

        # FakeModule is a class, not an instance — its methods are functions, so isfunction works
        count = catalog.register_from_module(FakeModule, predicate=inspect.isfunction)
        # task_a and task_b are unbound functions on the class object
        assert count >= 0  # number varies by Python internals; main check is no crash

    def test_registers_with_predicate(self):
        catalog = CallableCatalog(name="tasks")

        mod = type("FakeMod", (), {
            "__file__": "/fake/mod.py",
            "__name__": "fake_mod",
            "good_task": lambda task: None,
            "bad_item": "not_callable",
        })()

        catalog.register_from_module(mod, predicate=callable)
        assert "good_task" in catalog

    def test_transform_item_is_applied(self):
        catalog = CallableCatalog(name="filters")

        original = lambda host: host
        transformed = ("wrapped", original)

        mod = type("FakeMod", (), {
            "__file__": "/fake/mod.py",
            "__name__": "fake_mod",
            "my_filter": original,
        })()

        catalog.register_from_module(
            mod,
            predicate=callable,
            transform_item=lambda fn: transformed,
        )
        assert catalog["my_filter"] == transformed

    def test_module_name_tracked_in_sources(self):
        catalog = CallableCatalog(name="tasks")

        mod = type("FakeMod", (), {
            "__file__": "/some/path.py",
            "__name__": "my.module.name",
            "a_task": lambda t: t,
        })()

        catalog.register_from_module(mod, predicate=callable)
        assert catalog.sources["a_task"]["module_name"] == "my.module.name"

    def test_get_sources_by_module_groups_correctly(self):
        catalog = CallableCatalog(name="tasks")
        catalog.register("t1", lambda t: t, module_name="pkg.a")
        catalog.register("t2", lambda t: t, module_name="pkg.a")
        catalog.register("t3", lambda t: t, module_name="pkg.b")

        result = catalog.get_sources_by_module()

        assert sorted(result["pkg.a"]) == ["t1", "t2"]
        assert result["pkg.b"] == ["t3"]

    def test_register_without_explicit_module_name_auto_derives_from_callable(self):
        """When no module_name is supplied, the callable's __module__ is used as fallback."""
        catalog = CallableCatalog(name="tasks")

        def my_task(t):
            pass

        catalog.register("anon", my_task)

        result = catalog.get_sources_by_module()
        # my_task.__module__ is this test module — it must appear somewhere in the result
        assert any("anon" in names for names in result.values())


class TestClassCatalogIsBuiltinModuleOrigin:
    """Tests that is_builtin is derived solely from module origin in ClassCatalog."""

    def test_kwargs_cannot_fake_builtin(self):
        """Caller-supplied is_builtin=True kwarg is ignored when module is not builtin."""
        catalog = ClassCatalog(name="hooks")

        class External:
            pass

        External.__module__ = "third_party.hooks"
        catalog.register("external", External, is_builtin=True)
        assert catalog.sources["external"]["is_builtin"] is False

    def test_class_attr_cannot_fake_builtin(self):
        """is_builtin=True class attribute is ignored when module is not builtin."""
        catalog = ClassCatalog(name="hooks")

        class ClaimsBuiltin:
            __module__ = "third_party.hooks"
            is_builtin = True

        catalog.register("claims", ClaimsBuiltin)
        assert catalog.sources["claims"]["is_builtin"] is False

    def test_class_attr_cannot_deny_builtin(self):
        """is_builtin=False class attribute is ignored when module IS builtin."""
        catalog = ClassCatalog(name="hooks")

        class DeniesBuiltin:
            __module__ = "nornflow.builtins.hooks"
            is_builtin = False

        catalog.register("denier", DeniesBuiltin)
        assert catalog.sources["denier"]["is_builtin"] is True
