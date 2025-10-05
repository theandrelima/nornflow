"""Unit tests for catalog functionality, including built-in prevention rules."""

import pytest
from pathlib import Path
from unittest.mock import patch

from nornflow.catalogs import CallableCatalog, CatalogError, FileCatalog
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
        """Test that registering a custom task with a built-in name raises CatalogError."""
        catalog = CallableCatalog(name="tasks")
        # First, register the built-in
        catalog.register("set", builtin_set_task, module_name="nornflow.builtins.tasks")
        
        # Attempt to register a custom task with the same name
        def custom_set(task):
            return "custom"
        
        with pytest.raises(CatalogError, match="Cannot override built-in 'set' with a custom implementation"):
            catalog.register("set", custom_set, module_name="custom.module")

    def test_register_builtin_filter_success(self):
        """Test that built-in filters can be registered without issues."""
        catalog = CallableCatalog(name="filters")
        # Register a built-in filter (simulating internal loading)
        catalog.register("hosts", builtin_hosts_filter, module_name="nornflow.builtins.filters")
        assert "hosts" in catalog
        assert catalog.sources["hosts"]["is_builtin"] is True

    def test_register_custom_filter_with_builtin_name_fails(self):
        """Test that registering a custom filter with a built-in name raises CatalogError."""
        catalog = CallableCatalog(name="filters")
        # First, register the built-in
        catalog.register("hosts", builtin_hosts_filter, module_name="nornflow.builtins.filters")
        
        # Attempt to register a custom filter with the same name
        def custom_hosts(host):
            return True
        
        with pytest.raises(CatalogError, match="Cannot override built-in 'hosts' with a custom implementation"):
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