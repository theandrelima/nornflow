from unittest.mock import MagicMock, patch

import pytest

from nornflow import NornFlow, NornFlowBuilder
from nornflow.exceptions import (
    CatalogError,
    InitializationError,
    ResourceError,
    WorkflowError,
)
from nornflow.models import TaskModel, WorkflowModel
from nornflow.settings import NornFlowSettings


class TestNornFlowBasicCreation:
    """Test basic NornFlow creation scenarios."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_create_with_minimal_settings(self, tmp_path, task_content):
        """Test creating NornFlow with minimal required settings."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "task1.py").write_text(task_content)

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            settings = NornFlowSettings(
                nornir_config_file="dummy_config.yaml",
                local_tasks_dirs=[str(tasks_dir)]
            )
            nornflow = NornFlow(nornflow_settings=settings)

            assert isinstance(nornflow, NornFlow)
            assert "hello_world" in nornflow.tasks_catalog
            assert "set" in nornflow.tasks_catalog

    def test_create_with_invalid_kwargs(self):
        """Test creating NornFlow with invalid kwargs raises InitializationError."""
        settings = NornFlowSettings(nornir_config_file="dummy_config.yaml")
        
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            with pytest.raises(InitializationError, match="Invalid kwarg"):
                NornFlow(
                    nornflow_settings=settings,
                    nornir_config_file="should_not_be_passed_here"
                )


class TestNornFlowValidation:
    """Test NornFlow validation logic."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_empty_tasks_catalog(self, tmp_path):
        """Test error when no tasks are found raises CatalogError."""
        tasks_dir = tmp_path / "empty_tasks"
        tasks_dir.mkdir()

        settings = NornFlowSettings(
            nornir_config_file="dummy_config.yaml",
            local_tasks_dirs=[str(tasks_dir)]
        )

        with patch("nornflow.nornflow.builtin_tasks", {}), patch(
            "nornflow.nornflow.NornFlow._initialize_nornir"
        ):
            with pytest.raises(CatalogError):
                NornFlow(nornflow_settings=settings)

    def test_invalid_tasks_directory(self):
        """Test error when tasks directory doesn't exist raises ResourceError."""
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            settings = NornFlowSettings(
                nornir_config_file="dummy_config.yaml",
                local_tasks_dirs=["/nonexistent/dir"]
            )

            with pytest.raises(InitializationError) as exc_info:
                NornFlow(nornflow_settings=settings)

            assert isinstance(exc_info.value.__cause__, ResourceError)

    def test_property_modifications(self, basic_nornflow):
        """Ensure nornir_manager property is readable."""
        assert basic_nornflow.nornir_manager is not None


class TestWorkflowModelCreation:
    """Test workflow model creation."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_create_from_dict_missing_workflow_key(self):
        with pytest.raises(WorkflowError):
            WorkflowModel.create({})

    def test_create_from_invalid_dict(self, invalid_workflow_dict):
        with pytest.raises(ValueError):
            WorkflowModel.create(invalid_workflow_dict)

    def test_create_from_valid_dict(self, valid_workflow_dict):
        workflow = WorkflowModel.create(valid_workflow_dict)
        assert workflow.name == f"Test Workflow {self.test_name}"
        assert len(workflow.tasks) == 1

    def test_inventory_filters_dict(self, valid_workflow_dict):
        workflow = WorkflowModel.create(valid_workflow_dict)
        filters = {
            "hosts": list(workflow.inventory_filters["hosts"]),
            "groups": list(workflow.inventory_filters["groups"]),
        }
        assert filters == {"hosts": ["host1", "host2"], "groups": ["group1"]}


class TestNornFlowBuilder:
    """Test builder behaviour."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_builder_with_settings(self, basic_settings):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = NornFlowBuilder().with_settings_object(basic_settings).build()
            assert nf.settings == basic_settings

    def test_builder_with_workflow_object(self, basic_settings, valid_workflow):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = (
                NornFlowBuilder()
                .with_settings_object(basic_settings)
                .with_workflow_model(valid_workflow)
                .build()
            )
            assert nf.workflow == valid_workflow

    def test_builder_with_workflow_path(self, basic_settings, valid_workflow_file):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = (
                NornFlowBuilder()
                .with_settings_object(basic_settings)
                .with_workflow_path(valid_workflow_file)
                .build()
            )
            assert isinstance(nf.workflow, WorkflowModel)

    def test_builder_precedence(self, basic_settings, valid_workflow, valid_workflow_file):
        with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
            nf = (
                NornFlowBuilder()
                .with_settings_object(basic_settings)
                .with_workflow_path(valid_workflow_file)
                .with_workflow_model(valid_workflow)
                .build()
            )
            assert nf.workflow == valid_workflow


class TestWorkflowModelValidation:
    """Workflow validation."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    def test_empty_tasks_list(self):
        with pytest.raises(ValueError):
            WorkflowModel.create({"workflow": {"name": "Test", "tasks": []}})

    def test_invalid_failure_strategy(self):
        data = {
            "workflow": {
                "name": "Test Workflow",
                "failure_strategy": "invalid",
                "tasks": [{"name": "t"}],
            }
        }
        with pytest.raises(WorkflowError):
            WorkflowModel.create(data)

    def test_task_validation(self):
        data = {"workflow": {"name": "Test", "tasks": [{"name": "x"}]}}
        workflow = WorkflowModel.create(data)

        mock_nf = MagicMock(spec=NornFlow)
        mock_nf._tasks_catalog = {}
        mock_nf._vars_manager = MagicMock()
        mock_nf.workflow = workflow


class TestNornFlowExecution:
    """Execution tests."""

    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        self.test_name = request.function.__name__

    @patch("nornflow.nornflow.NornirManager")
    def test_run_uses_context_manager(self, mock_mgr_cls):
        """Ensure context manager is used during run()."""
        mock_mgr = MagicMock()
        mock_mgr.__enter__.return_value = mock_mgr
        mock_mgr_cls.return_value = mock_mgr

        wf = MagicMock(spec=WorkflowModel)
        wf.dry_run = False
        wf.tasks = []
        wf.inventory_filters = {}
        wf.processors = []
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.name = "Test WF"

        settings = MagicMock()
        settings.nornir_config_file = None
        settings.local_workflows_dirs = []
        settings.vars_dir = "/tmp"
        settings.vars = {}

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"), patch.object(
            NornFlow, "_apply_processors", MagicMock()
        ):
            def dummy_exec(self):
                with self.nornir_manager:
                    pass

            with patch.object(NornFlow, "_orchestrate_execution", dummy_exec):
                nf = NornFlow(workflow=wf, nornflow_settings=settings)
                nf._nornir_manager = mock_mgr
                nf._print_workflow_overview = MagicMock()
                nf._print_workflow_summary = MagicMock()

                nf.run()

        mock_mgr.__enter__.assert_called_once()
        mock_mgr.__exit__.assert_called_once()

    @patch("nornflow.nornflow.NornirManager")
    def test_run_handles_exceptions(self, mock_mgr_cls):
        """Connections are closed even when an error occurs."""
        mock_mgr = MagicMock()
        mock_mgr.__enter__.return_value = mock_mgr
        mock_mgr_cls.return_value = mock_mgr

        wf = MagicMock(spec=WorkflowModel)
        wf.dry_run = False
        wf.tasks = []
        wf.inventory_filters = {}
        wf.processors = []
        wf.vars = {}
        wf.description = None
        wf.failure_strategy = None
        wf.name = "Test WF"

        settings = MagicMock()
        settings.nornir_config_file = None
        settings.local_workflows_dirs = []
        settings.vars_dir = "/tmp"
        settings.vars = {}

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"), patch.object(
            NornFlow, "_apply_processors", MagicMock()
        ):
            def dummy_exec(self):
                with self.nornir_manager:
                    raise Exception("Test error")

            with patch.object(NornFlow, "_orchestrate_execution", dummy_exec):
                nf = NornFlow(workflow=wf, nornflow_settings=settings)
                nf._nornir_manager = mock_mgr
                nf._print_workflow_overview = MagicMock()

                with pytest.raises(Exception, match="Test error"):
                    nf.run()

        mock_mgr.__exit__.assert_called_once()

    def test_workflow_execution_orchestration(self):
        """Tasks run in order."""
        t1, t2 = MagicMock(spec=TaskModel), MagicMock(spec=TaskModel)
        t1.name, t2.name = "task1", "task2"

        wf = MagicMock(spec=WorkflowModel)
        wf.tasks = [t1, t2]
        wf.dry_run = False
        wf.inventory_filters = {}
        wf.vars = {}
        wf.processors = []
        wf.failure_strategy = None
        wf.name = "WF"
        wf.description = None

        settings = NornFlowSettings(nornir_config_file="dummy_config.yaml")

        with patch("nornflow.nornflow.NornFlow._initialize_nornir"), patch.object(
            NornFlow, "_create_variable_manager", return_value=MagicMock()
        ):
            nf = NornFlow(workflow=wf, nornflow_settings=settings)
            mgr = MagicMock()
            mgr.__enter__.return_value = mgr
            nf._nornir_manager = mgr
            nf._print_workflow_overview = MagicMock()
            nf._print_workflow_summary = MagicMock()
            nf._vars_manager = MagicMock()
            nf._tasks_catalog = {"task1": MagicMock(), "task2": MagicMock()}

            nf.run()

            t1.run.assert_called_once()
            t2.run.assert_called_once()