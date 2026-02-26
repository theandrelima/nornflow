"""Unit tests for catalog functionality, including built-in prevention rules."""

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
        # Register a built-in task (simulating internal loading)
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")
        assert "set" in catalog
        assert catalog.sources["set"]["is_builtin"] is True

    def test_register_custom_task_with_builtin_name_fails(self):
        """Test that registering a custom task with a built-in name raises BuiltinOverrideError."""
        catalog = CallableCatalog(name="tasks")
        # First, register the built-in
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")

        # Attempt to register a custom task with the same name
        def custom_set(task):
            return "custom"

        with pytest.raises(BuiltinOverrideError, match="'set'.*is a built-in name and cannot be overridden"):
            catalog.register("set", custom_set, module_name="custom.module")

    def test_register_builtin_filter_success(self):
        """Test that built-in filters can be registered without issues."""
        catalog = CallableCatalog(name="filters")
        # Register a built-in filter (simulating internal loading)
        catalog.register("hosts", builtin_hosts_filter, module_name="nornflow.builtins.filters")
        assert "hosts" in catalog
        assert catalog.sources["hosts"]["is_builtin"] is True

    def test_register_custom_filter_with_builtin_name_fails(self):
        """Test that registering a custom filter with a built-in name raises BuiltinOverrideError."""
        catalog = CallableCatalog(name="filters")
        # First, register the built-in
        catalog.register("hosts", builtin_hosts_filter, module_name="nornflow.builtins.filters")

        # Attempt to register a custom filter with the same name
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

        # Register a custom task first
        def first_custom(task):
            return "first"
        catalog.register("custom_task", first_custom, module_name="first.module")

        # Override with another custom task
        def second_custom(task):
            return "second"
        catalog.register("custom_task", second_custom, module_name="second.module")

        # Should succeed and update to the second one
        assert "custom_task" in catalog
        assert catalog["custom_task"] == second_custom
        assert catalog.sources["custom_task"]["is_builtin"] is False

    def test_override_non_builtin_filter_success(self):
        """Test that non-built-in filters can be overridden by later registrations."""
        catalog = CallableCatalog(name="filters")

        # Register a custom filter first
        def first_custom(host):
            return True
        catalog.register("custom_filter", first_custom, module_name="first.module")

        # Override with another custom filter
        def second_custom(host):
            return False
        catalog.register("custom_filter", second_custom, module_name="second.module")

        # Should succeed and update to the second one
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
            assert count > 0  # Verify discovery works without assuming exact count

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

    def test_register_class_with_explicit_is_builtin_true(self):
        """Test that an explicit is_builtin=True class attribute is authoritative."""
        catalog = ClassCatalog(name="hooks")

        class FakeBuiltin:
            is_builtin = True

        catalog.register("fake_builtin", FakeBuiltin)
        assert catalog.sources["fake_builtin"]["is_builtin"] is True

    def test_register_class_with_explicit_is_builtin_false(self):
        """Test that an explicit is_builtin=False class attribute is authoritative,
        even when the module name would suggest builtin status."""
        catalog = ClassCatalog(name="hooks")

        class NotReallyBuiltin:
            __module__ = "nornflow.builtins.something"
            is_builtin = False

        catalog.register("not_really", NotReallyBuiltin)
        assert catalog.sources["not_really"]["is_builtin"] is False

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

    def test_register_class_kwargs_is_builtin_respected(self):
        """Test that caller-supplied is_builtin kwarg is used when class has no attr."""
        catalog = ClassCatalog(name="hooks")

        class Neutral:
            pass

        Neutral.__module__ = "some.module"
        catalog.register("neutral", Neutral, is_builtin=True)
        assert catalog.sources["neutral"]["is_builtin"] is True

    def test_builtin_override_raises(self):
        """Test that overriding a builtin entry raises BuiltinOverrideError."""
        catalog = ClassCatalog(name="hooks")

        class Builtin:
            is_builtin = True

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

        # Create test files
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

        builtin_file = tmp_path / "base.yaml"
        builtin_file.write_text("content")
        override_file = tmp_path / "base_v2.yaml"
        override_file.write_text("content")

        catalog.register("base.yaml", builtin_file, is_builtin=True)

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