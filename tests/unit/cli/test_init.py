from unittest.mock import MagicMock, patch

import pytest

from nornflow.cli.exceptions import CLIInitError
from nornflow.cli.init import (
    create_directories_from_settings,
    get_user_confirmation,
    init,
    setup_builder,
    setup_nornir_configs,
    setup_nornflow_settings_file,
    setup_sample_content,
    show_info_post_init,
)


class MockExit(Exception):
    """Mock exception for testing typer.Exit"""

    def __init__(self, code=0):
        self.code = code
        super().__init__(f"Exit with code {code}")


class TestInitCommand:
    """Tests for the 'init' CLI command."""

    @patch("nornflow.cli.init.NornFlowSettings")
    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_nornir_configs")
    @patch("nornflow.cli.init.setup_nornflow_settings_file")
    @patch("nornflow.cli.init.create_directories_from_settings")
    @patch("nornflow.cli.init.setup_sample_content")
    @patch("nornflow.cli.init.show_info_post_init")
    def test_init_successful(
        self,
        mock_show_info,
        mock_setup_sample_content,
        mock_create_dirs,
        mock_setup_settings,
        mock_setup_nornir,
        mock_confirmation,
        mock_setup_builder,
        mock_settings_class,
    ):
        """Test successful initialization."""
        mock_builder = MagicMock()
        mock_nornflow = MagicMock()
        mock_settings = MagicMock()
        mock_builder.build.return_value = mock_nornflow
        mock_setup_builder.return_value = mock_builder
        mock_settings_class.load.return_value = mock_settings
        mock_confirmation.return_value = True
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": "test_settings.yaml"}

        init(mock_ctx)

        mock_confirmation.assert_called_once()
        mock_setup_settings.assert_called_once_with("test_settings.yaml")
        mock_settings_class.load.assert_called_once()
        mock_setup_nornir.assert_called_once_with(mock_settings)
        mock_create_dirs.assert_called_once_with(mock_settings)
        mock_setup_builder.assert_called_once_with(mock_ctx)
        mock_builder.build.assert_called_once()
        mock_setup_sample_content.assert_called_once_with(mock_nornflow)
        mock_show_info.assert_called_once_with(mock_nornflow)

    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_nornir_configs")
    def test_init_user_declines(self, mock_setup_nornir, mock_confirmation, mock_setup_builder):
        """Test initialization when user declines."""
        mock_confirmation.return_value = False
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": ""}

        init(mock_ctx)

        mock_confirmation.assert_called_once()
        mock_setup_nornir.assert_not_called()

    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_nornflow_settings_file")
    def test_init_file_not_found_error(self, mock_setup_settings, mock_confirmation, mock_setup_builder):
        """Test initialization with file not found error."""
        mock_confirmation.return_value = True
        mock_setup_settings.side_effect = FileNotFoundError("File not found")
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": ""}

        with pytest.raises(CLIInitError):
            init(mock_ctx)

    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_nornflow_settings_file")
    def test_init_permission_error(self, mock_setup_settings, mock_confirmation, mock_setup_builder):
        """Test initialization with permission error."""
        mock_confirmation.return_value = True
        mock_setup_settings.side_effect = PermissionError("Permission denied")
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": ""}

        with pytest.raises(CLIInitError):
            init(mock_ctx)


class TestSetupFunctions:
    """Tests for the setup helper functions used by the init command."""

    @patch("nornflow.cli.init.NornFlowBuilder")
    @patch("nornflow.cli.init.NORNFLOW_SETTINGS")
    @patch("nornflow.cli.init.Path")
    def test_setup_builder_with_custom_settings(self, mock_path_class, mock_default_settings, mock_nornflow_builder):
        """Test setup_builder function with custom settings."""
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": "test_settings.yaml"}
        mock_builder_instance = MagicMock()
        mock_nornflow_builder.return_value = mock_builder_instance
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        result = setup_builder(mock_ctx)

        mock_nornflow_builder.assert_called_once()
        mock_builder_instance.with_settings_path.assert_called_once_with("test_settings.yaml")
        assert result == mock_builder_instance

    @patch("nornflow.cli.init.NornFlowBuilder")
    @patch("nornflow.cli.init.NORNFLOW_SETTINGS")
    def test_setup_builder_with_default_settings(self, mock_default_settings, mock_nornflow_builder):
        """Test setup_builder function with default settings."""
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": None}
        mock_builder_instance = MagicMock()
        mock_nornflow_builder.return_value = mock_builder_instance
        mock_default_settings.exists.return_value = True

        result = setup_builder(mock_ctx)

        mock_nornflow_builder.assert_called_once()
        mock_builder_instance.with_settings_path.assert_called_once_with(mock_default_settings)
        assert result == mock_builder_instance

    @patch("nornflow.cli.init.typer.confirm")
    def test_get_user_confirmation_yes(self, mock_confirm):
        """Test get_user_confirmation when user confirms."""
        mock_confirm.return_value = True

        result = get_user_confirmation()

        assert result is True

    @patch("nornflow.cli.init.typer.confirm")
    def test_get_user_confirmation_no(self, mock_confirm):
        """Test get_user_confirmation when user declines."""
        mock_confirm.return_value = False

        result = get_user_confirmation()

        assert result is False

    @patch("nornflow.cli.init.shutil.copytree")
    @patch("nornflow.cli.init.typer.secho")
    @patch("nornflow.cli.init.Path")
    def test_setup_nornir_configs_new_directory(self, mock_path_class, mock_secho, mock_copytree):
        """Test setup_nornir_configs when directory doesn't exist."""
        mock_settings = MagicMock()
        mock_settings.nornir_config_file = "/path/to/nornir_configs/config.yaml"
        
        mock_config_path = MagicMock()
        mock_config_dir = MagicMock()
        mock_config_dir.exists.return_value = False
        mock_config_path.parent = mock_config_dir
        mock_path_class.return_value = mock_config_path

        setup_nornir_configs(mock_settings)

        mock_copytree.assert_called_once()
        assert mock_secho.call_count >= 1

    @patch("nornflow.cli.init.shutil.copytree")
    @patch("nornflow.cli.init.typer.secho")
    @patch("nornflow.cli.init.Path")
    def test_setup_nornir_configs_existing_directory(self, mock_path_class, mock_secho, mock_copytree):
        """Test setup_nornir_configs when directory already exists."""
        mock_settings = MagicMock()
        mock_settings.nornir_config_file = "/path/to/nornir_configs/config.yaml"
        
        mock_config_path = MagicMock()
        mock_config_dir = MagicMock()
        mock_config_dir.exists.return_value = True
        mock_config_path.parent = mock_config_dir
        mock_path_class.return_value = mock_config_path

        setup_nornir_configs(mock_settings)

        mock_copytree.assert_not_called()

    @patch("nornflow.cli.init.NORNFLOW_SETTINGS")
    @patch("nornflow.cli.init.SAMPLE_NORNFLOW_FILE")
    @patch("nornflow.cli.init.shutil.copy")
    @patch("nornflow.cli.init.typer.secho")
    @patch("nornflow.cli.init.os.getenv", return_value=None)
    @patch("nornflow.cli.init.Path")
    def test_setup_nornflow_config_no_settings(
        self, mock_path_class, mock_getenv, mock_secho, mock_copy, mock_sample, mock_default_settings
    ):
        """Test setup_nornflow_settings_file with no existing settings."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path
        mock_default_settings.exists.return_value = False

        setup_nornflow_settings_file("")

        mock_copy.assert_called_once()

    @patch("nornflow.cli.init.create_directory")
    def test_create_directories_from_settings(self, mock_create_dir):
        """Test create_directories_from_settings function."""
        mock_settings = MagicMock()
        mock_settings.local_tasks = ["tasks"]
        mock_settings.local_workflows = ["workflows"]
        mock_settings.local_filters = ["filters"]
        mock_settings.local_hooks = ["hooks"]
        mock_settings.vars_dir = "vars"

        create_directories_from_settings(mock_settings)

        assert mock_create_dir.call_count == 5

    @patch("nornflow.cli.init.copy_sample_files_to_dir")
    @patch("nornflow.cli.init.Path")
    def test_setup_sample_content(self, mock_path_class, mock_copy_files):
        """Test setup_sample_content function."""
        mock_nornflow = MagicMock()
        mock_nornflow.settings.local_tasks = ["tasks"]
        mock_nornflow.settings.local_workflows = ["workflows"]
        mock_nornflow.settings.vars_dir = "vars"

        setup_sample_content(mock_nornflow)

        assert mock_copy_files.call_count == 3

    @patch("nornflow.cli.init.show_nornflow_settings")
    @patch("nornflow.cli.init.show_catalog")
    def test_show_info_post_init(self, mock_show_catalog, mock_show_settings):
        """Test show_info_post_init function."""
        mock_nornflow = MagicMock()

        show_info_post_init(mock_nornflow)

        mock_show_settings.assert_called_once_with(mock_nornflow)
        mock_show_catalog.assert_called_once_with(mock_nornflow)