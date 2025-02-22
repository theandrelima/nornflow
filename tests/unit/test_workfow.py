import pytest

from nornflow.workflow import WorkflowFactory, Workflow
from nornflow.exceptions import WorkflowInitializationError, TaskDoesNotExistError
from nornflow.models import TaskModel
from pydantic_serdes.exceptions import PydanticSerdesTypeError
from pydantic_serdes.datastore import get_global_data_store


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
        factory = WorkflowFactory(
            workflow_path=valid_workflow_file,
            workflow_dict=invalid_workflow_dict
        )
        workflow = factory.create()
        assert isinstance(workflow, Workflow)
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == f"{self.test_name}_task"
        assert workflow.tasks[0].args == {"arg1": "value1"}

    def test_check_tasks_validation(self, valid_workflow_dict):
        """Test task validation against task catalog."""
        workflow = WorkflowFactory.create_from_dict(valid_workflow_dict)
        tasks_catalog = {}  # Empty catalog to trigger error
        
        with pytest.raises(TaskDoesNotExistError) as exc_info:
            workflow._check_tasks(tasks_catalog)
        assert f"{self.test_name}_task" in str(exc_info.value)

    def test_inventory_filters(self, valid_workflow_dict):
        """Test inventory filters are correctly set."""
        workflow = WorkflowFactory.create_from_dict(valid_workflow_dict)
        assert workflow.inventory_filters == {
            "hosts": ("host1", "host2"),
            "groups": ("group1",)
        }