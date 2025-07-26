from unittest.mock import MagicMock, patch

import pytest
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.exceptions import PydanticSerdesTypeError

from nornflow.exceptions import TaskNotFoundError, WorkflowInitializationError
from nornflow.models import TaskModel
from nornflow.workflow import Workflow, WorkflowFactory

GLOBAL_DATA_STORE = get_global_data_store()


class TestWorkflowBasicCreation:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__

    def test_create_with_no_parameters(self):
        """Test creating a workflow with no parameters."""
        factory = WorkflowFactory()
        with pytest.raises(WorkflowInitializationError) as exc_info:
            factory.create()
        assert "Either workflow_path or workflow_dict must be provided" in str(exc_info.value)

    def test_create_from_nonexistent_file(self):
        """Test creating a workflow from a non-existent file."""
        with pytest.raises(PydanticSerdesTypeError):
            WorkflowFactory.create_from_file("nonexistent.yaml")


class TestWorkflowValidation:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__

    def test_create_from_invalid_file(self, invalid_workflow_file):
        """Test creating a workflow from an invalid file (missing tasks)."""
        with pytest.raises(ValueError) as exc_info:
            WorkflowFactory.create_from_file(invalid_workflow_file)
        assert "The OneToMany initialization iterable can't be empty" in str(exc_info.value)

    def test_create_from_invalid_dict(self, invalid_workflow_dict):
        """Test creating a workflow from an invalid dictionary."""
        with pytest.raises(ValueError) as exc_info:
            WorkflowFactory.create_from_dict(invalid_workflow_dict)
        assert "The OneToMany initialization iterable can't be empty" in str(exc_info.value)


class TestWorkflowSuccessfulCreation:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__

    def test_create_from_dict_valid(self, valid_workflow_dict):
        """Test creating a workflow from a valid dictionary."""
        GLOBAL_DATA_STORE.flush()
        workflow = WorkflowFactory.create_from_dict(valid_workflow_dict)
        assert isinstance(workflow, Workflow)
        assert len(workflow.tasks) == 1
        assert isinstance(workflow.tasks[0], TaskModel)
        assert workflow.tasks[0].name == f"{self.test_name}_task"
        assert workflow.tasks[0].args == {"arg1": ("value1", "value2")}

    def test_create_from_file_valid(self, valid_workflow_file):
        """Test creating a workflow from a valid file."""
        GLOBAL_DATA_STORE.flush()
        workflow = WorkflowFactory.create_from_file(valid_workflow_file)
        assert isinstance(workflow, Workflow)
        assert len(workflow.tasks) == 1
        assert isinstance(workflow.tasks[0], TaskModel)
        assert workflow.tasks[0].name == f"{self.test_name}_task"
        assert workflow.tasks[0].args == {"arg1": "value1"}

    def test_factory_precedence(self, valid_workflow_file, invalid_workflow_dict):
        """Test that file path takes precedence over dictionary when both are provided."""
        GLOBAL_DATA_STORE.flush()
        factory = WorkflowFactory(workflow_path=valid_workflow_file, workflow_dict=invalid_workflow_dict)
        workflow = factory.create()
        assert isinstance(workflow, Workflow)
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == f"{self.test_name}_task"
        assert workflow.tasks[0].args == {"arg1": "value1"}

    def test_check_tasks_validation(self, valid_workflow_dict):
        """Test task validation against task catalog."""
        workflow = WorkflowFactory.create_from_dict(valid_workflow_dict)
        tasks_catalog = {}  # Empty catalog to trigger error

        with pytest.raises(TaskNotFoundError) as exc_info:
            workflow._check_tasks(tasks_catalog)
        assert f"{self.test_name}_task" in str(exc_info.value)

    def test_inventory_filters(self, valid_workflow_dict):
        """Test inventory filters are correctly set."""
        workflow = WorkflowFactory.create_from_dict(valid_workflow_dict)
        assert workflow.inventory_filters == {"hosts": ("host1", "host2"), "groups": ("group1",)}


class TestWorkflowExecution:
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method to ensure each test uses unique names."""
        self.test_name = request.function.__name__
        # Clean the global data store before each test
        GLOBAL_DATA_STORE.flush()

    def test_workflow_run_calls_task_run(self):
        """Test that Workflow.run calls task.run for each task."""
        # Create workflow with real TaskModel instances
        workflow_dict = {
            "workflow": {"name": "test_workflow", "tasks": [{"name": "task1"}, {"name": "task2"}]}
        }

        workflow = WorkflowFactory.create_from_dict(workflow_dict)

        # Setup
        mock_nornir_manager = MagicMock()
        mock_nornir_manager.nornir = MagicMock()
        mock_tasks_catalog = {"task1": MagicMock(), "task2": MagicMock()}
        mock_filters_catalog = {}

        # Patch _check_tasks to do nothing and patch the TaskModel.run method
        with patch.object(workflow, "_check_tasks"), patch("nornflow.models.TaskModel.run") as mock_run:

            # Execute
            workflow.run(mock_nornir_manager, mock_tasks_catalog, mock_filters_catalog)

            # Verify run was called twice (once for each task)
            assert mock_run.call_count == 2
            # Verify each call had the right arguments
            for call_args in mock_run.call_args_list:
                args, kwargs = call_args
                assert args[0] == mock_nornir_manager
                assert args[1] == mock_tasks_catalog

    def test_workflow_run_applies_filters_and_processors(self):
        """Test that Workflow.run properly applies filters and processors."""
        # Create workflow
        workflow_dict = {
            "workflow": {
                "name": "test_workflow",
                "inventory_filters": {"hosts": ["test_host"]},
                "tasks": [{"name": "test_task"}],
            }
        }

        workflow = WorkflowFactory.create_from_dict(workflow_dict)

        mock_nornir_manager = MagicMock()
        mock_nornir_manager.nornir = MagicMock()
        mock_tasks_catalog = {"test_task": MagicMock()}
        mock_filters_catalog = {}
        mock_processors = [MagicMock()]

        # Patch _check_tasks and other methods
        with (
            patch.object(workflow, "_check_tasks"),
            patch("nornflow.models.TaskModel.run") as mock_run,
            patch.object(workflow, "_apply_filters") as mock_apply_filters,
            patch.object(workflow, "_with_processors") as mock_with_processors,
        ):

            # Execute
            workflow.run(mock_nornir_manager, mock_tasks_catalog, mock_filters_catalog, mock_processors)

            # Verify
            mock_apply_filters.assert_called_once_with(mock_nornir_manager, mock_filters_catalog)
            mock_with_processors.assert_called_once_with(mock_nornir_manager, [], mock_processors)
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            assert args[0] == mock_nornir_manager
            assert args[1] == mock_tasks_catalog