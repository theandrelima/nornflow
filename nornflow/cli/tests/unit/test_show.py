from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import typer
import yaml

from nornflow.cli.show import (
    render_filters_catalog_table_data,
    render_nornir_cfgs_table_data,
    render_settings_table_data,
    render_task_catalog_table_data,
    render_workflows_catalog_table_data,
    show,
    show_catalog,
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
    @patch("nornflow.cli.show.show_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_all_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_catalog, mock_builder
    ):
        """Test 'show' with --all flag displays everything."""
        # Setup mocks
        mock_nornflow = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        # Call the show function with all=True
        show(mock_ctx, catalog=False, settings=False, nornir_configs=False, all=True)

        # Verify all show functions were called
        mock_show_catalog.assert_called_once_with(mock_nornflow)
        mock_show_settings.assert_called_once_with(mock_nornflow)
        mock_show_nornir_configs.assert_called_once_with(mock_nornflow)
        mock_builder_instance.build.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_catalog_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_catalog, mock_builder
    ):
        """Test 'show' with --catalog flag displays only catalog."""
        # Setup mocks
        mock_nornflow = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        # Call the show function with catalog=True
        show(mock_ctx, catalog=True, settings=False, nornir_configs=False, all=False)

        # Verify only catalog function was called
        mock_show_catalog.assert_called_once_with(mock_nornflow)
        mock_show_settings.assert_not_called()
        mock_show_nornir_configs.assert_not_called()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_settings_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_catalog, mock_builder
    ):
        """Test 'show' with --settings flag displays only settings."""
        # Setup mocks
        mock_nornflow = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        # Call the show function with settings=True
        show(mock_ctx, catalog=False, settings=True, nornir_configs=False, all=False)

        # Verify only settings function was called
        mock_show_catalog.assert_not_called()
        mock_show_settings.assert_called_once_with(mock_nornflow)
        mock_show_nornir_configs.assert_not_called()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_nornir_configs_flag(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_catalog, mock_builder
    ):
        """Test 'show' with --nornir-configs flag displays only Nornir configs."""
        # Setup mocks
        mock_nornflow = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        # Call the show function with nornir_configs=True
        show(mock_ctx, catalog=False, settings=False, nornir_configs=True, all=False)

        # Verify only nornir_configs function was called
        mock_show_catalog.assert_not_called()
        mock_show_settings.assert_not_called()
        mock_show_nornir_configs.assert_called_once_with(mock_nornflow)

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.show_catalog")
    @patch("nornflow.cli.show.show_nornflow_settings")
    @patch("nornflow.cli.show.show_nornir_configs")
    def test_show_with_settings_path(
        self, mock_show_nornir_configs, mock_show_settings, mock_show_catalog, mock_builder
    ):
        """Test 'show' with settings path in context."""
        # Setup mocks
        mock_nornflow = MagicMock()
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_nornflow
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": "custom_settings.yaml"}

        # Call the show function with all=True
        show(mock_ctx, catalog=False, settings=False, nornir_configs=False, all=True)

        # Verify settings path was used
        mock_builder_instance.with_settings_path.assert_called_once_with("custom_settings.yaml")
        mock_show_catalog.assert_called_once()
        mock_show_settings.assert_called_once()
        mock_show_nornir_configs.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    def test_show_no_flags(self, mock_builder):
        """Test 'show' with no flags raises an error."""
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        with pytest.raises(typer.BadParameter):
            show(mock_ctx, catalog=False, settings=False, nornir_configs=False, all=False)

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.CLIShowError")
    def test_show_nornflow_error(self, mock_error, mock_builder):
        """Test 'show' handles NornFlowAppError correctly."""
        from nornflow.exceptions import NornFlowError

        # Setup mocks
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.side_effect = NornFlowError("Test error")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        # Call with typer.Exit mocked
        with patch("nornflow.cli.show.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                show(mock_ctx, catalog=False, settings=True, nornir_configs=False, all=False)

            # Verify error handling
            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.CLIShowError")
    def test_show_yaml_error(self, mock_error, mock_builder):
        """Test 'show' handles YAML errors correctly."""
        # Setup mocks
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.side_effect = yaml.YAMLError("Invalid YAML")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        # Call with typer.Exit mocked
        with patch("nornflow.cli.show.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                show(mock_ctx, catalog=False, settings=True, nornir_configs=False, all=False)

            # Verify error handling
            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()

    @patch("nornflow.cli.show.NornFlowBuilder")
    @patch("nornflow.cli.show.CLIShowError")
    def test_show_file_not_found_error(self, mock_error, mock_builder):
        """Test 'show' handles FileNotFoundError correctly."""
        # Setup mocks
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        mock_builder_instance.build.side_effect = FileNotFoundError("File not found")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()
        mock_ctx.obj = {}

        # Call with typer.Exit mocked
        with patch("nornflow.cli.show.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                show(mock_ctx, catalog=False, settings=True, nornir_configs=False, all=False)

            # Verify error handling
            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()


class TestShowHelpers:
    """Tests for the show helper functions."""

    @patch("nornflow.cli.show.show_formatted_table")
    def test_show_catalog(self, mock_show_table):
        """Test show_catalog calls show_formatted_table with correct parameters."""
        mock_nornflow = MagicMock()

        show_catalog(mock_nornflow)

        assert mock_show_table.call_count == 3
        # Should call for tasks, workflows, and filters catalogs
        calls = [
            call(
                "TASKS CATALOG",
                render_task_catalog_table_data,
                ["Task Name", "Description", "Location"],
                mock_nornflow,
            ),
            call(
                "WORKFLOWS CATALOG",
                render_workflows_catalog_table_data,
                ["Workflow Name", "Description", "Location"],
                mock_nornflow,
            ),
            call(
                "FILTERS CATALOG",
                render_filters_catalog_table_data,
                ["Filter Name", "Description", "Location"],
                mock_nornflow,
            ),
        ]
        mock_show_table.assert_has_calls(calls)

    @patch("nornflow.cli.show.show_formatted_table")
    def test_show_nornflow_settings(self, mock_show_table):
        """Test show_nornflow_settings calls show_formatted_table with correct parameters."""
        mock_nornflow = MagicMock()

        show_nornflow_settings(mock_nornflow)

        mock_show_table.assert_called_once_with(
            "NORNFLOW SETTINGS", render_settings_table_data, ["Setting", "Value"], mock_nornflow
        )

    @patch("nornflow.cli.show.show_formatted_table")
    def test_show_nornir_configs(self, mock_show_table):
        """Test show_nornir_configs calls show_formatted_table with correct parameters."""
        mock_nornflow = MagicMock()

        show_nornir_configs(mock_nornflow)

        mock_show_table.assert_called_once_with(
            "NORNIR CONFIGS", render_nornir_cfgs_table_data, ["Config", "Value"], mock_nornflow
        )

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
        # Setup tasks catalog with mock functions having docstrings
        task_func1 = MagicMock(__doc__="Test task 1 description")
        task_func2 = MagicMock(__doc__="Test task 2 description")
        mock_nornflow.tasks_catalog = {"task1": task_func1, "task2": task_func2}

        with patch("nornflow.cli.show.inspect") as mock_inspect:
            mock_inspect.getfile.return_value = "/path/to/task.py"
            mock_inspect.getmodule.return_value = None

            result = render_task_catalog_table_data(mock_nornflow)

            # Verify result is a list with 2 items (one for each task)
            assert len(result) == 2
            # Each item should be a list with 3 elements: name, description, location
            for row in result:
                assert len(row) == 3

    @patch("yaml.safe_load")
    def test_render_workflows_catalog_table_data(self, mock_safe_load):
        """Test render_workflows_catalog_table_data generates workflow catalog table data."""
        mock_nornflow = MagicMock()
        # Setup workflows catalog with paths
        mock_nornflow.workflows_catalog = {
            "workflow1.yaml": Path("/path/to/workflow1.yaml"),
            "workflow2.yaml": Path("/path/to/workflow2.yaml"),
        }

        # Mock yaml.safe_load to return workflow data
        mock_safe_load.side_effect = [
            {"workflow": {"description": "Test workflow 1"}},
            {"workflow": {"description": "Test workflow 2"}},
        ]

        # Need to mock Path.open to return a file-like object
        with patch("pathlib.Path.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
