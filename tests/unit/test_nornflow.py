import pytest

from nornflow import NornFlowBuilder
from nornflow.exceptions import (
    CatalogModificationError,
    DirectoryNotFoundError,
    EmptyTaskCatalogError,
    NornFlowInitializationError,
    NornirConfigError,
    SettingsModificationError,
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
        assert len(nornflow.tasks_catalog) == 1

    def test_create_with_invalid_kwargs(self):
        """Test creating NornFlow with invalid kwargs."""
        with pytest.raises(NornFlowInitializationError):
            NornFlow(config_file="invalid.yaml")  # config_file is invalid init kwarg


class TestNornFlowValidation:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__

    def test_empty_tasks_catalog(self, tmp_path):
        """Test error when no tasks are found is wrapped in NornFlowInitializationError."""
        tasks_dir = tmp_path / "empty_tasks"
        tasks_dir.mkdir()

        settings = NornFlowSettings(local_tasks_dirs=[str(tasks_dir)])
        with pytest.raises(NornFlowInitializationError) as exc_info:
            NornFlow(nornflow_settings=settings)

        assert isinstance(exc_info.value.__cause__, EmptyTaskCatalogError)

    def test_invalid_tasks_directory(self):
        """Test error when tasks directory doesn't exist is wrapped in NornFlowInitializationError."""
        settings = NornFlowSettings(local_tasks_dirs=["/nonexistent/dir"])
        with pytest.raises(NornFlowInitializationError) as exc_info:
            NornFlow(nornflow_settings=settings)

        assert isinstance(exc_info.value.__cause__, DirectoryNotFoundError)

    def test_property_modifications(self, basic_nornflow):
        """Test that properties cannot be modified directly."""
        with pytest.raises(NornirConfigError):
            basic_nornflow.nornir_configs = {}

        with pytest.raises(SettingsModificationError):
            basic_nornflow.settings = NornFlowSettings()

        with pytest.raises(CatalogModificationError):
            basic_nornflow.tasks_catalog = {}

        with pytest.raises(CatalogModificationError):
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
