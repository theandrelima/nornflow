from unittest.mock import MagicMock, patch

import pytest

from nornflow import NornFlowBuilder
from nornflow.exceptions import (
    CatalogError,
    CoreError,
    NornFlowError, 
    NornirError,
    SettingsError,
)
from nornflow.nornflow import NornFlow
from nornflow.settings import NornFlowSettings
from nornflow.workflow import Workflow


class TestNornFlowBasicCreation:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__

    def test_create_with_minimal_settings(self, tmp_path, task_content):
        """Test creating NornFlow with minimal required settings."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "task1.py").write_text(task_content)

        settings = NornFlowSettings(local_tasks_dirs=[str(tasks_dir)])
        nornflow = NornFlow(nornflow_settings=settings)

        assert isinstance(nornflow, NornFlow)
        assert "hello_world" in nornflow.tasks_catalog
        assert "set" in nornflow.tasks_catalog
        assert "hello_world" in nornflow.tasks_catalog

    def test_create_with_invalid_kwargs(self):
        """Test creating NornFlow with invalid kwargs."""
        with pytest.raises(NornFlowError):
            NornFlow(config_file="invalid.yaml")  # config_file is invalid init kwarg


class TestNornFlowValidation:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__

    def test_empty_tasks_catalog(self, tmp_path):
        """Test error when no tasks are found is wrapped in NornFlowError."""
        tasks_dir = tmp_path / "empty_tasks"
        tasks_dir.mkdir()

        settings = NornFlowSettings(local_tasks_dirs=[str(tasks_dir)])
        
        # Directly mock the builtin_tasks to be empty and intercept the CatalogError
        with patch("nornflow.nornflow.builtin_tasks", {}), \
             patch("nornflow.nornflow.CatalogError", wraps=CatalogError) as mock_catalog_error:
            
            # The initialization should raise NornFlowError wrapping a CatalogError
            with pytest.raises(NornFlowError) as exc_info:
                NornFlow(nornflow_settings=settings)

            # Verify that CatalogError was called with the expected message and catalog_name
            mock_catalog_error.assert_called_with(
                "No tasks were found. The Tasks Catalog can't be empty.",
                catalog_name="tasks"
            )
            
            # Verify the top exception is NornFlowError
            assert isinstance(exc_info.value, NornFlowError)
            
            # Verify the error message contains expected text
            assert "tasks catalog" in str(exc_info.value).lower()

    def test_invalid_tasks_directory(self):
        """Test error when tasks directory doesn't exist is wrapped in NornFlowError."""
        settings = NornFlowSettings(local_tasks_dirs=["/nonexistent/dir"])

        # Directly mock the builtin_tasks to be empty and intercept the CatalogError
        with patch("nornflow.nornflow.builtin_tasks", {}), \
             patch("nornflow.nornflow.CatalogError", wraps=CatalogError) as mock_catalog_error:
            
            # The initialization should raise NornFlowError wrapping a CatalogError
            with pytest.raises(NornFlowError) as exc_info:
                NornFlow(nornflow_settings=settings)

            # Verify that CatalogError was called with the expected message and catalog_name
            mock_catalog_error.assert_called_with(
                "No tasks were found. The Tasks Catalog can't be empty.",
                catalog_name="tasks"
            )
            
            # Verify the top exception is NornFlowError
            assert isinstance(exc_info.value, NornFlowError)
            
            # Verify the error message contains expected text
            assert "tasks catalog" in str(exc_info.value).lower()

    def test_property_modifications(self, basic_nornflow):
        """Test that properties cannot be modified directly."""
        with pytest.raises(NornirError):
            basic_nornflow.nornir_configs = {}

        with pytest.raises(SettingsError):
            basic_nornflow.settings = NornFlowSettings()

        with pytest.raises(CoreError):
            basic_nornflow.tasks_catalog = {}

        with pytest.raises(CoreError):
            basic_nornflow.workflows_catalog = {}


class TestNornFlowBuilder:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__

    def test_builder_with_settings(self, basic_settings):
        """Test building NornFlow with settings."""
        nornflow = NornFlowBuilder().with_settings_object(basic_settings).build()
        assert isinstance(nornflow, NornFlow)
        assert nornflow.settings == basic_settings

    def test_builder_with_workflow_object(self, basic_settings, valid_workflow):
        """Test building NornFlow with a workflow object."""
        nornflow = (
            NornFlowBuilder()
            .with_settings_object(basic_settings)
            .with_workflow_object(valid_workflow)
            .build()
        )
        assert isinstance(nornflow, NornFlow)
        assert nornflow.workflow == valid_workflow

    def test_builder_with_workflow_path(self, basic_settings, valid_workflow_file):
        """Test building NornFlow with a workflow path."""
        nornflow = (
            NornFlowBuilder()
            .with_settings_object(basic_settings)
            .with_workflow_path(valid_workflow_file)
            .build()
        )
        assert isinstance(nornflow, NornFlow)
        assert isinstance(nornflow.workflow, Workflow)

    def test_builder_precedence(self, basic_settings, valid_workflow, valid_workflow_file):
        """Test that workflow object takes precedence over path."""
        nornflow = (
            NornFlowBuilder()
            .with_settings_object(basic_settings)
            .with_workflow_path(valid_workflow_file)
            .with_workflow_object(valid_workflow)
            .build()
        )
        assert nornflow.workflow == valid_workflow


class TestNornFlowExecution:
    """Test suite for NornFlow execution and connection management."""

    @patch("nornflow.nornflow.NornirManager")
    def test_run_uses_context_manager(self, mock_nornir_manager_class):
        """Test that run() method uses the NornirManager as a context manager."""
        # Setup
        mock_nornir_manager = MagicMock()
        mock_nornir_manager_class.return_value = mock_nornir_manager
        mock_nornir_manager.__enter__.return_value = mock_nornir_manager
        
        mock_workflow = MagicMock()
        mock_settings = MagicMock()
        mock_settings.nornir_config_file = "dummy_config.yaml"
        
        nornflow = NornFlow(
            workflow=mock_workflow,
            nornflow_settings=mock_settings,
        )
        
        # Execute run method
        nornflow.run()
        
        # Verify context manager was used
        mock_nornir_manager.__enter__.assert_called_once()
        mock_nornir_manager.__exit__.assert_called_once()
        
        # Verify workflow was run
        mock_workflow.run.assert_called_once()

    @patch("nornflow.nornflow.NornirManager")
    def test_run_handles_exceptions(self, mock_nornir_manager_class):
        """Test that connections are closed even if workflow raises an exception."""
        # Setup
        mock_nornir_manager = MagicMock()
        mock_nornir_manager_class.return_value = mock_nornir_manager
        mock_nornir_manager.__enter__.return_value = mock_nornir_manager
        
        mock_workflow = MagicMock()
        mock_workflow.run.side_effect = ValueError("Test exception")
        
        mock_settings = MagicMock()
        mock_settings.nornir_config_file = "dummy_config.yaml"
        
        nornflow = NornFlow(
            workflow=mock_workflow,
            nornflow_settings=mock_settings,
        )
        
        # Execute run method, expect exception
        with pytest.raises(ValueError):
            nornflow.run()
        
        # Verify context manager's exit was called (connections closed)
        mock_nornir_manager.__enter__.assert_called_once()
        mock_nornir_manager.__exit__.assert_called()
