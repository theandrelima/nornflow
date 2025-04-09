from unittest.mock import MagicMock, patch

import pytest

from nornflow.cli.init import (
    get_user_confirmation,
    init,
    setup_builder,
    setup_directory_structure,
    setup_nornflow_config_file,
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

    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_directory_structure")
    @patch("nornflow.cli.init.setup_nornflow_config_file")
    @patch("nornflow.cli.init.setup_sample_content")
    @patch("nornflow.cli.init.show_info_post_init")
    def test_init_successful(
        self,
        mock_show_info,
        mock_setup_sample_content,
        mock_setup_config,
        mock_setup_dirs,
        mock_confirmation,
        mock_setup_builder,
    ):
        """Test successful initialization."""
        # Setup mocks
        mock_builder = MagicMock()
        mock_setup_builder.return_value = mock_builder
        mock_confirmation.return_value = True
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": "test_settings.yaml"}

        # Call the init function
        init(mock_ctx)

        # Verify all expected functions were called
        mock_setup_builder.assert_called_once_with(mock_ctx)
        mock_confirmation.assert_called_once()
        mock_setup_dirs.assert_called_once()
        mock_setup_config.assert_called_once_with("test_settings.yaml")
        mock_setup_sample_content.assert_called_once()
        mock_show_info.assert_called_once_with(mock_builder)

    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_directory_structure")
    def test_init_user_declines(self, mock_setup_dirs, mock_confirmation, mock_setup_builder):
        """Test initialization when user declines confirmation."""
        # Setup mocks
        mock_confirmation.return_value = False
        mock_ctx = MagicMock()

        # Call the init function
        init(mock_ctx)

        # Verify setup_builder was called but not setup_directory_structure
        mock_setup_builder.assert_called_once()
        mock_confirmation.assert_called_once()
        mock_setup_dirs.assert_not_called()

    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_directory_structure")
    @patch("nornflow.cli.init.CLIInitError")
    def test_init_file_not_found_error(
        self, mock_error, mock_setup_dirs, mock_confirmation, mock_setup_builder
    ):
        """Test initialization when FileNotFoundError occurs."""
        # Setup mocks
        mock_confirmation.return_value = True
        mock_setup_dirs.side_effect = FileNotFoundError("test file not found")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()

        # Don't expect Exit to be raised in test since we're mocking the implementation
        with patch("nornflow.cli.init.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                init(mock_ctx)

            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()

    @patch("nornflow.cli.init.setup_builder")
    @patch("nornflow.cli.init.get_user_confirmation")
    @patch("nornflow.cli.init.setup_directory_structure")
    @patch("nornflow.cli.init.CLIInitError")
    def test_init_permission_error(self, mock_error, mock_setup_dirs, mock_confirmation, mock_setup_builder):
        """Test initialization when PermissionError occurs."""
        # Setup mocks
        mock_confirmation.return_value = True
        mock_setup_dirs.side_effect = PermissionError("permission denied")
        mock_error_instance = MagicMock()
        mock_error.return_value = mock_error_instance
        mock_ctx = MagicMock()

        # Don't expect Exit to be raised in test since we're mocking the implementation
        with patch("nornflow.cli.init.typer") as mock_typer:
            mock_typer.Exit = MockExit
            with pytest.raises(MockExit) as exc_info:
                init(mock_ctx)

            assert exc_info.value.code == 2
            mock_error.assert_called_once()
            mock_error_instance.show.assert_called_once()


class TestSetupFunctions:
    """Tests for the setup helper functions used by the init command."""

    @patch("nornflow.cli.init.NornFlowBuilder")
    def test_setup_builder(self, mock_nornflow_builder):
        """Test setup_builder function."""
        mock_builder = MagicMock()
        mock_nornflow_builder.return_value = mock_builder
        mock_ctx = MagicMock()
        mock_ctx.obj = {"settings": "custom_settings.yaml"}

        result = setup_builder(mock_ctx)

        assert result == mock_builder
        mock_builder.with_settings_path.assert_called_once_with("custom_settings.yaml")

    @patch("nornflow.cli.init.typer.confirm")
    def test_get_user_confirmation_yes(self, mock_confirm):
        """Test get_user_confirmation when user confirms."""
        mock_confirm.return_value = True
        result = get_user_confirmation()
        assert result is True
        mock_confirm.assert_called_once()

    @patch("nornflow.cli.init.typer.confirm")
    def test_get_user_confirmation_no(self, mock_confirm):
        """Test get_user_confirmation when user declines."""
        mock_confirm.return_value = False
        result = get_user_confirmation()
        assert result is False
        mock_confirm.assert_called_once()

    @patch("nornflow.cli.init.create_directory")
    @patch("nornflow.cli.init.shutil.copytree")
    @patch("nornflow.cli.init.shutil.copy")
    def test_setup_directory_structure(self, mock_copy, mock_copytree, mock_create_dir):
        """Test setup_directory_structure creates directories."""
        # Setup mock to return True to simulate directory creation
        mock_create_dir.return_value = True

        setup_directory_structure()

        # Verify create_directory was called at least once
        assert mock_create_dir.call_count >= 1  # Should be called for nornir_configs at minimum

        # Verify shutil.copy or copytree were called to populate directories
        assert mock_copy.call_count + mock_copytree.call_count > 0

    @patch("nornflow.cli.init.NORNFLOW_CONFIG_FILE")
    @patch("nornflow.cli.init.SAMPLE_NORNFLOW_FILE")
    @patch("nornflow.cli.init.shutil.copy")
    @patch("nornflow.cli.init.typer.secho")
    @patch("nornflow.cli.init.os.getenv", return_value=None)
    def test_setup_nornflow_config_no_settings(
        self, mock_getenv, mock_secho, mock_copy, mock_sample, mock_config
    ):
        """Test setup_nornflow_config_file with no settings."""
        # Make Path.exists return False to ensure file is copied
        mock_config.exists.return_value = False

        setup_nornflow_config_file("")

        # Verify config file was copied
        mock_copy.assert_called_once_with(mock_sample, mock_config)
        mock_secho.assert_called_once()

    @patch("nornflow.cli.init.create_directory_and_copy_sample_files")
    @patch("nornflow.cli.init.typer.secho")
    @patch("nornflow.cli.init.Path")
    def test_setup_sample_content(self, mock_path, mock_secho, mock_create_and_copy):
        """Test setup_sample_content copies sample files."""
        # Configure the mock
        mock_create_and_copy.return_value = None

        setup_sample_content()

        # Verify create_directory_and_copy_sample_files was called at least 2 times
        assert mock_create_and_copy.call_count >= 2
        mock_secho.assert_called()

    @patch("nornflow.cli.init.show_nornflow_settings")
    @patch("nornflow.cli.init.show_catalog")
    def test_show_info_post_init(self, mock_show_catalog, mock_show_settings):
        """Test show_info_post_init displays information."""
        mock_builder = MagicMock()
        mock_nornflow = MagicMock()
        mock_builder.build.return_value = mock_nornflow

        show_info_post_init(mock_builder)

        # Should build the NornFlow object
        mock_builder.build.assert_called_once()
        # Should call show functions
        mock_show_settings.assert_called_once_with(mock_nornflow)
        mock_show_catalog.assert_called_once_with(mock_nornflow)
