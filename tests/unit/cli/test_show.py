from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import typer
import yaml
from typer.testing import CliRunner

from nornflow.cli.entrypoint import app
from nornflow.cli.show import (
    get_catalog_table_headers,
    render_blueprints_catalog_table_data,
    render_filters_catalog_table_data,
    render_j2_filters_catalog_table_data,
    render_nornir_cfgs_table_data,
    render_settings_table_data,
    render_table_data,
    render_task_catalog_table_data,
    render_workflows_catalog_table_data,
    render_hooks_catalog_table_data,
    show,
    show_catalog,
    show_catalog_formatted_table,
    show_formatted_table,
    show_nornflow_settings,
    show_nornir_configs,
)


class MockExit(Exception):
    """Mock exception for testing typer.Exit"""

    def __init__(self, code=0):
        self.code = code
        super().__init__(f"Exit with code {code}")


class TestShowCommand:
    """Tests for the 'show' CLI command."""

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_tasks_catalog")
    @patch("nornflow.cli.show.show_filters_catalog")
    @patch("nornflow.cli.show.show_workflows_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_all_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_workflows, 
        mock_show_filters, mock_show_tasks, mock_builder
    ):
        """Test 'show' with --all flag displays everything."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_enabled = True
        mock_nornflow.logs_redaction_enabled = True
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        show(mock_ctx, catalogs=False, tasks=False, filters=False,
             workflows=False, settings=False, nornir_configs=False, all=True, no_redact=False)

        mock_show_tasks.assert_called_once_with(mock_nornflow)
        mock_show_filters.assert_called_once_with(mock_nornflow)
        mock_show_workflows.assert_called_once_with(mock_nornflow)
        mock_show_settings.assert_called_once_with(mock_nornflow, redaction_enabled=True)
        mock_show_nornir_configs.assert_called_once_with(mock_nornflow, redaction_enabled=True)
        mock_builder_instance.build.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_tasks_catalog")
    @patch("nornflow.cli.show.show_filters_catalog")
    @patch("nornflow.cli.show.show_workflows_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_catalogs_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_workflows,
        mock_show_filters, mock_show_tasks, mock_builder
    ):
        """Test 'show' with --catalogs flag displays all catalogs."""
        mock_nornflow = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        show(mock_ctx, catalogs=True, tasks=False, filters=False,
             workflows=False, settings=False, nornir_configs=False, all=False)

        mock_show_tasks.assert_called_once_with(mock_nornflow)
        mock_show_filters.assert_called_once_with(mock_nornflow)
        mock_show_workflows.assert_called_once_with(mock_nornflow)
        mock_show_settings.assert_not_called()
        mock_show_nornir_configs.assert_not_called()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_tasks_catalog")
    @patch("nornflow.cli.show.show_filters_catalog")
    @patch("nornflow.cli.show.show_workflows_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_settings_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_workflows,
        mock_show_filters, mock_show_tasks, mock_builder
    ):
        """Test 'show' with --settings flag displays only settings."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_enabled = True
        mock_nornflow.logs_redaction_enabled = True
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        show(mock_ctx, catalogs=False, tasks=False, filters=False,
             workflows=False, settings=True, nornir_configs=False, all=False, no_redact=False)

        mock_show_tasks.assert_not_called()
        mock_show_filters.assert_not_called()
        mock_show_workflows.assert_not_called()
        mock_show_settings.assert_called_once_with(mock_nornflow, redaction_enabled=True)
        mock_show_nornir_configs.assert_not_called()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_tasks_catalog")
    @patch("nornflow.cli.show.show_filters_catalog")
    @patch("nornflow.cli.show.show_workflows_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_nornir_configs_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_workflows,
        mock_show_filters, mock_show_tasks, mock_builder
    ):
        """Test 'show' with --nornir-configs flag displays only Nornir configs."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_enabled = True
        mock_nornflow.logs_redaction_enabled = True
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        show(mock_ctx, catalogs=False, tasks=False, filters=False,
             workflows=False, settings=False, nornir_configs=True, all=False, no_redact=False)

        mock_show_tasks.assert_not_called()
        mock_show_filters.assert_not_called()
        mock_show_workflows.assert_not_called()
        mock_show_settings.assert_not_called()
        mock_show_nornir_configs.assert_called_once_with(mock_nornflow, redaction_enabled=True)

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_tasks_catalog")
    @patch("nornflow.cli.show.show_filters_catalog")
    @patch("nornflow.cli.show.show_workflows_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_with_settings_path(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_workflows,
        mock_show_filters, mock_show_tasks, mock_builder
    ):
        """Test 'show' with settings path in context."""
        mock_nornflow = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": "custom_settings.yaml"}

        show(mock_ctx, catalogs=False, tasks=False, filters=False,
             workflows=False, settings=False, nornir_configs=False, all=True)

        mock_builder_instance.with_settings_path.assert_called_once_with("custom_settings.yaml")
        mock_show_tasks.assert_called_once()
        mock_show_filters.assert_called_once()
        mock_show_workflows.assert_called_once()
        mock_show_settings.assert_called_once()
        mock_show_nornir_configs.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    def test_show_no_flags(self, mock_builder):
        """Test 'show' with no flags raises an error."""
        mock_ctx = MagicMock()
        mock_ctx.obj = {}
    
        with pytest.raises(typer.BadParameter):
            show(mock_ctx, catalogs=False, tasks=False, filters=False,
                 workflows=False, blueprints=False, j2_filters=False, hooks=False, settings=False, nornir_configs=False, all=False)

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.CLIShowError")
    def test_show_nornflow_error(self, mock_error, mock_builder):
        """Test 'show' handles NornFlowAppError correctly."""
        from nornflow.exceptions import NornFlowError

        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.side_effect = NornFlowError("Test error")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        with patch("nornflow.cli.show.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                show(mock_ctx, catalogs=False, tasks=False, filters=False,
                     workflows=False, settings=True, nornir_configs=False, all=False)

            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.CLIShowError")
    def test_show_yaml_error(self, mock_error, mock_builder):
        """Test 'show' handles YAML errors correctly."""
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.side_effect = yaml.YAMLError("Invalid YAML")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        with patch("nornflow.cli.show.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                show(mock_ctx, catalogs=False, tasks=False, filters=False,
                     workflows=False, settings=True, nornir_configs=False, all=False)

            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.CLIShowError")
    def test_show_file_not_found_error(self, mock_error, mock_builder):
        """Test 'show' handles FileNotFoundError correctly."""
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.side_effect = FileNotFoundError("File not found")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        with patch("nornflow.cli.show.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                show(mock_ctx, catalogs=False, tasks=False, filters=False,
                     workflows=False, settings=True, nornir_configs=False, all=False)

            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()


class TestShowHelpers:
    """Tests for the show helper functions."""

    @patch("nornflow.cli.show.show_catalog_formatted_table")
    def test_show_catalog(self, mock_show_table):
        """Test show_catalog calls show_catalog_formatted_table for each catalog."""
        mock_nornflow = MagicMock()

        show_catalog(mock_nornflow)

        assert mock_show_table.call_count == 6
        calls = [
            call("TASKS CATALOG", render_task_catalog_table_data, mock_nornflow),
            call("FILTERS CATALOG", render_filters_catalog_table_data, mock_nornflow),
            call("WORKFLOWS CATALOG", render_workflows_catalog_table_data, mock_nornflow),
            call("BLUEPRINTS CATALOG", render_blueprints_catalog_table_data, mock_nornflow),
            call("JINJA2 FILTERS CATALOG", render_j2_filters_catalog_table_data, mock_nornflow),
            call("HOOKS CATALOG", render_hooks_catalog_table_data, mock_nornflow),
        ]
        mock_show_table.assert_has_calls(calls)

    @patch("nornflow.cli.show.show_formatted_table")
    def test_show_nornflow_settings(self, mock_show_table):
        """Test show_nornflow_settings calls show_formatted_table with correct parameters."""
        mock_nornflow = MagicMock()

        show_nornflow_settings(mock_nornflow)

        args, _ = mock_show_table.call_args
        assert args[0] == "NORNFLOW SETTINGS"
        assert callable(args[1])
        assert args[2] == ["Setting", "Value"]
        assert args[3] is mock_nornflow

    @patch("nornflow.cli.show.show_formatted_table")
    def test_show_nornir_configs(self, mock_show_table):
        """Test show_nornir_configs calls show_formatted_table with correct parameters."""
        mock_nornflow = MagicMock()

        show_nornir_configs(mock_nornflow)

        args, _ = mock_show_table.call_args
        assert args[0] == "NORNIR CONFIGS"
        assert callable(args[1])
        assert args[2] == ["Config", "Value"]
        assert args[3] is mock_nornflow

    @patch("nornflow.cli.show.tabulate")
    @patch("nornflow.cli.show.display_banner")
    def test_show_formatted_table(self, mock_display_banner, mock_tabulate):
        """Test show_formatted_table formats and displays table correctly."""
        mock_nornflow = MagicMock()
        mock_renderer = MagicMock()
        mock_renderer.return_value = [["row1col1", "row1col2"], ["row2col1", "row2col2"]]
        mock_tabulate.return_value = "formatted table"
        headers = ["Header1", "Header2"]

        show_formatted_table("Test Banner", mock_renderer, headers, mock_nornflow)

        mock_renderer.assert_called_once_with(mock_nornflow)
        mock_display_banner.assert_called_once()
        mock_tabulate.assert_called_once()


class TestTableRenderers:
    """Tests for the table data rendering functions."""

    def test_render_task_catalog_table_data(self):
        """Test render_task_catalog_table_data generates task catalog table data."""
        mock_nornflow = MagicMock()
        task_func1 = MagicMock(__doc__="Test task 1 description")
        task_func2 = MagicMock(__doc__="Test task 2 description")
        
        mock_tasks_catalog = MagicMock()
        mock_tasks_catalog.get_builtin_items.return_value = {"nornflow.task1": task_func1}
        mock_tasks_catalog.get_custom_items.return_value = {"local.task2": task_func2}
        mock_tasks_catalog.__getitem__.side_effect = lambda x: task_func1 if x == "nornflow.task1" else task_func2
        mock_tasks_catalog.sources = {
            "nornflow.task1": {"description": "Test task 1 description", "bare_name": "task1", "collision": ""},
            "local.task2": {"description": "Test task 2 description", "bare_name": "task2", "collision": ""},
        }
        mock_nornflow.tasks_catalog = mock_tasks_catalog

        result, headers = render_task_catalog_table_data(mock_nornflow)

        assert headers == get_catalog_table_headers(include_collision=False)
        assert len(result) == 2
        for row in result:
            assert len(row) == 2

    def test_render_task_catalog_table_data_includes_collision_column(self):
        """Test collision column appears when any entry has collision metadata."""
        mock_nornflow = MagicMock()
        task_func1 = MagicMock(__doc__="Test task 1 description")

        mock_tasks_catalog = MagicMock()
        mock_tasks_catalog.get_builtin_items.return_value = {"nornflow.task1": task_func1}
        mock_tasks_catalog.get_custom_items.return_value = {}
        mock_tasks_catalog.sources = {
            "nornflow.task1": {
                "description": "Test task 1 description",
                "collision": "local (bare → nornflow.task1)",
            },
        }
        mock_nornflow.tasks_catalog = mock_tasks_catalog

        result, headers = render_task_catalog_table_data(mock_nornflow)

        assert headers == get_catalog_table_headers(include_collision=True)
        assert len(result) == 1
        assert len(result[0]) == 3

    def test_render_workflows_catalog_table_data(self):
        """Test render_workflows_catalog_table_data generates workflow catalog table data."""
        mock_nornflow = MagicMock()
        workflow_path1 = MagicMock(spec=Path)
        workflow_path2 = MagicMock(spec=Path)
        
        mock_nornflow.workflows_catalog.sources = {
            "local.workflow1": {"description": "Test workflow 1"},
            "local.workflow2": {"description": "Test workflow 2"},
        }
        mock_nornflow.workflows_catalog.get_builtin_items.return_value = {}
        mock_nornflow.workflows_catalog.get_custom_items.return_value = {
            "local.workflow1": workflow_path1,
            "local.workflow2": workflow_path2,
        }

        result, headers = render_workflows_catalog_table_data(mock_nornflow)

        assert headers == get_catalog_table_headers(include_collision=False)
        assert len(result) == 2
        for row in result:
            assert len(row) == 2

    def test_render_filters_catalog_table_data(self):
        """Test render_filters_catalog_table_data generates filters catalog table data."""
        mock_nornflow = MagicMock()
        filter_func1 = MagicMock(__doc__="Test filter 1 description")
        filter_func2 = MagicMock(__doc__="Test filter 2 description")
        
        mock_filters_catalog = MagicMock()
        mock_filters_catalog.get_builtin_items.return_value = {"nornflow.filter1": filter_func1}
        mock_filters_catalog.get_custom_items.return_value = {"local.filter2": filter_func2}
        mock_filters_catalog.__getitem__.side_effect = (
            lambda x: (filter_func1, ["param1"]) if x == "nornflow.filter1" else (filter_func2, [])
        )
        mock_filters_catalog.sources = {
            "nornflow.filter1": {"description": "Test filter 1 description", "bare_name": "filter1", "collision": ""},
            "local.filter2": {"description": "Test filter 2 description", "bare_name": "filter2", "collision": ""},
        }
        mock_nornflow.filters_catalog = mock_filters_catalog
    
        result, headers = render_filters_catalog_table_data(mock_nornflow)

        assert headers == get_catalog_table_headers(include_collision=False)
        assert len(result) == 2
        for row in result:
            assert len(row) == 2

    def test_render_j2_filters_catalog_table_data(self):
        """Test render_j2_filters_catalog_table_data generates Jinja2 filters catalog table data."""
        mock_nornflow = MagicMock()
        filter_func1 = MagicMock(__doc__="Test Jinja2 filter 1 description.")
        filter_func2 = MagicMock(__doc__="Test Jinja2 filter 2 description.")
        
        mock_j2_filters_catalog = MagicMock()
        mock_j2_filters_catalog.get_builtin_items.return_value = {"nornflow.j2_filter1": filter_func1}
        mock_j2_filters_catalog.get_custom_items.return_value = {"local.j2_filter2": filter_func2}
        mock_j2_filters_catalog.__getitem__.side_effect = (
            lambda x: filter_func1 if x == "nornflow.j2_filter1" else filter_func2
        )
        mock_j2_filters_catalog.sources = {
            "nornflow.j2_filter1": {"description": "Test Jinja2 filter 1 description.", "bare_name": "j2_filter1", "collision": ""},
            "local.j2_filter2": {"description": "Test Jinja2 filter 2 description.", "bare_name": "j2_filter2", "collision": ""},
        }
        mock_nornflow.j2_filters_catalog = mock_j2_filters_catalog

        result, headers = render_j2_filters_catalog_table_data(mock_nornflow)

        assert headers == get_catalog_table_headers(include_collision=False)
        assert len(result) == 2
        for row in result:
            assert len(row) == 2

    def test_render_blueprints_catalog_table_data(self):
        """Test render_blueprints_catalog_table_data generates blueprints catalog table data."""
        mock_nornflow = MagicMock()
        blueprint_path1 = MagicMock(spec=Path)
        blueprint_path2 = MagicMock(spec=Path)
        
        mock_nornflow.blueprints_catalog.sources = {
            "local.blueprint1": {"description": "Test blueprint 1"},
            "local.blueprint2": {"description": "Test blueprint 2"},
        }
        mock_nornflow.blueprints_catalog.get_builtin_items.return_value = {}
        mock_nornflow.blueprints_catalog.get_custom_items.return_value = {
            "local.blueprint1": blueprint_path1,
            "local.blueprint2": blueprint_path2,
        }

        result, headers = render_blueprints_catalog_table_data(mock_nornflow)

        assert headers == get_catalog_table_headers(include_collision=False)
        assert len(result) == 2
        for row in result:
            assert len(row) == 2

    def test_render_settings_table_data(self):
        """Test render_settings_table_data generates settings table data."""
        mock_nornflow = MagicMock()
        mock_nornflow.settings.as_dict = {"setting1": "value1", "setting2": "value2"}

        result = render_settings_table_data(mock_nornflow)

        assert len(result) == 2
        for row in result:
            assert len(row) == 2

    def test_render_nornir_cfgs_table_data(self):
        """Test render_nornir_cfgs_table_data generates nornir configs table data."""
        mock_nornflow = MagicMock()
        mock_nornflow.nornir_configs = {"config1": "value1", "config2": "value2"}

        result = render_nornir_cfgs_table_data(mock_nornflow)

        assert len(result) == 2
        for row in result:
            assert len(row) == 2


class TestMaskingInShow:
    """Verify that render_table_data masks sensitive values before display."""

    def test_nested_token_is_masked(self):
        """nautobot_token nested inside inventory options must never appear in output."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_sensitive_names = frozenset()
        mock_nornflow.nornir_configs = {
            "inventory": {
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://localhost:8080",
                    "nautobot_token": "3ff4118f836dfa3c2fc1b4bc0db7afccfb87dcd3",
                },
            }
        }

        result = render_nornir_cfgs_table_data(mock_nornflow)

        rendered = str(result)
        assert "3ff4118f836dfa3c2fc1b4bc0db7afccfb87dcd3" not in rendered
        assert "***REDACTED***" in rendered

    def test_url_is_not_masked(self):
        """Non-sensitive values such as nautobot_url must pass through unchanged."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_sensitive_names = frozenset()
        mock_nornflow.nornir_configs = {
            "inventory": {
                "options": {
                    "nautobot_url": "http://localhost:8080",
                    "nautobot_token": "secret",
                }
            }
        }

        result = render_nornir_cfgs_table_data(mock_nornflow)

        assert "http://localhost:8080" in str(result)

    def test_user_sensitive_name_in_nornir_configs_is_masked(self):
        """Names listed only in sensitive_names must be redacted in show output."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_sensitive_names = frozenset({"credential_x"})
        mock_nornflow.nornir_configs = {
            "inventory": {
                "hosts": {
                    "leaf1": {
                        "hostname": "10.0.0.1",
                        "credential_x": "CLAB_ONLY_SECRET",
                        "site_label": "lab-east",
                    }
                }
            }
        }

        result = render_nornir_cfgs_table_data(mock_nornflow)

        rendered = str(result)
        assert "CLAB_ONLY_SECRET" not in rendered
        assert "***REDACTED***" in rendered
        assert "lab-east" in rendered
        assert "10.0.0.1" in rendered

    def test_top_level_sensitive_key_in_settings_is_masked(self):
        """A top-level sensitive key in settings.as_dict must be masked."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_sensitive_names = frozenset()
        mock_nornflow.settings.as_dict = {
            "nornir_config_file": "nornir_configs/config.yaml",
            "db_password": "hunter2",
        }

        result = render_settings_table_data(mock_nornflow)

        rendered = str(result)
        assert "hunter2" not in rendered
        assert "***REDACTED***" in rendered
        assert "nornir_configs/config.yaml" in rendered


class TestNoRedact:
    """Verify that render_table_data and show helpers respect redaction_enabled=False."""

    def test_render_table_data_no_redact_shows_secret(self):
        """When redaction_enabled=False, sensitive values must not be replaced."""
        data = {"nautobot_token": "abc123", "host": "router1"}

        result = render_table_data(data, redaction_enabled=False)

        rendered = str(result)
        assert "abc123" in rendered
        assert "***REDACTED***" not in rendered

    def test_render_table_data_default_redacts_secret(self):
        """When redaction_enabled=True (default), sensitive values must be replaced."""
        data = {"nautobot_token": "abc123", "host": "router1"}

        result = render_table_data(data)

        rendered = str(result)
        assert "abc123" not in rendered
        assert "***REDACTED***" in rendered

    def test_render_settings_table_data_no_redact(self):
        """render_settings_table_data with redaction_enabled=False shows plain values."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_sensitive_names = frozenset()
        mock_nornflow.settings.as_dict = {"db_password": "hunter2", "host": "router1"}

        result = render_settings_table_data(mock_nornflow, redaction_enabled=False)

        rendered = str(result)
        assert "hunter2" in rendered
        assert "***REDACTED***" not in rendered

    def test_render_nornir_cfgs_table_data_no_redact(self):
        """render_nornir_cfgs_table_data with redaction_enabled=False shows nested token."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_sensitive_names = frozenset()
        mock_nornflow.nornir_configs = {
            "inventory": {"options": {"nautobot_token": "s3cr3t"}}
        }

        result = render_nornir_cfgs_table_data(mock_nornflow, redaction_enabled=False)

        assert "s3cr3t" in str(result)
        assert "***REDACTED***" not in str(result)

    def test_settings_redaction_disabled_propagates_to_show(self):
        """When redaction is disabled, render_settings_table_data shows secrets."""
        mock_nornflow = MagicMock()
        mock_nornflow.settings.as_dict = {"api_key": "topsecret"}

        result = render_settings_table_data(mock_nornflow, redaction_enabled=False)

        assert "topsecret" in str(result)

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_nornflow_settings")
    def test_show_no_redact_passes_kwarg_to_builder(self, mock_show_settings, mock_builder):
        """--no-redact must disable terminal redaction only; logs follow settings."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_enabled = False
        mock_nornflow.logs_redaction_enabled = True
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        show(
            mock_ctx,
            catalogs=False,
            tasks=False,
            filters=False,
            workflows=False,
            settings=True,
            nornir_configs=False,
            all=False,
            no_redact=True,
        )

        mock_builder_instance.with_kwargs.assert_called_once_with(no_redact=True)
        mock_show_settings.assert_called_once_with(mock_nornflow, redaction_enabled=False)


class TestShowCliShortOptions:
    """CLI short-option coverage for nornflow show."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @patch("nornflow.cli.show.show_hooks_catalog")
    @patch("nornflow.cli.show.NornFlowBuilder")
    def test_show_hooks_short_option(
        self, mock_builder: MagicMock, mock_hooks: MagicMock, runner: CliRunner
    ) -> None:
        """-h selects the hooks catalog instead of showing command help."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_enabled = True
        mock_nornflow.logs_redaction_enabled = True
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow

        result = runner.invoke(app, ["show", "-h"])

        assert result.exit_code == 0
        mock_hooks.assert_called_once_with(mock_nornflow)

    @patch("nornflow.cli.show.show_tasks_catalog")
    @patch("nornflow.cli.show.NornFlowBuilder")
    def test_show_catalogs_short_option(
        self, mock_builder: MagicMock, mock_tasks: MagicMock, runner: CliRunner
    ) -> None:
        """-c selects --catalogs."""
        mock_nornflow = MagicMock()
        mock_nornflow.redaction_enabled = True
        mock_nornflow.logs_redaction_enabled = True
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow

        result = runner.invoke(app, ["show", "-c"])

        assert result.exit_code == 0
        mock_tasks.assert_called_once_with(mock_nornflow)
