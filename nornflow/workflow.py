import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir.core.processor import Processor
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.utils import generate_from_dict, load_file_to_dict

from nornflow.exceptions import TaskDoesNotExistError, WorkflowInitializationError
from nornflow.inventory_filters import filter_by_groups, filter_by_hostname
from nornflow.models import TaskModel
from nornflow.nornir_manager import NornirManager
from nornflow.processors import DefaultNornFlowProcessor

# making sure pydantic_serdes sees Workflow models
os.environ["MODELS_MODULES"] = "nornflow.models"


class Workflow:
    """
    A workflow in NornFlow represents a structured, ordered collection of tasks that are executed
    against a Nornir inventory. Workflows provide a higher-level abstraction over individual Nornir
    tasks, enabling complex multi-step operations while maintaining readability and reusability.

    Workflows can be defined in YAML files or directly as dictionaries, and are processed through
    the pydantic-serdes library to validate their structure and convert them into runtime objects.

    Key features:
    - Task orchestration: Execute a sequence of tasks in defined order
    - Inventory filtering: Target specific hosts or groups for execution in the order specified
    - Task validation: Verify tasks exist before execution
    - Result processing: Apply processors for standardized result handling

    Example workflow definition (YAML):
        workflow:
          name: configure_interfaces
          description: Configure interface settings on network devices
          inventory_filters:
            groups: [access_switches]  # Applied first
            hosts: [switch1, switch2]  # Applied second
          tasks:
            - name: backup_configs
            - name: generate_configs
              args:
                template: interface_configs.j2
            - name: deploy_configs
    """

    def __init__(self, workflow_dict: dict[str, Any]):
        """
        Initialize the Workflow object.

        Args:
            workflow_dict (dict[str, Any]): Dictionary representing the workflow configuration.
        """
        self.workflow_dict = workflow_dict
        generate_from_dict(self.workflow_dict)
        self.records = get_global_data_store().records

    @property
    def workflow_dict(self) -> dict[str, Any]:
        """
        Get the workflow dictionary.

        Returns:
            dict[str, Any]: The workflow dictionary.
        """
        return self._workflow_dict

    @workflow_dict.setter
    def workflow_dict(self, wf_dict: dict[str, Any]) -> None:
        """
        Set the workflow dictionary.

        Args:
            wf_dict (dict[str, Any]): The workflow dictionary.
        """
        if "workflow" not in wf_dict:
            raise WorkflowInitializationError("Missing 'workflow' in workflow definition")

        self._workflow_dict = wf_dict

    @property
    def tasks(self) -> list[TaskModel]:
        """
        Get the tasks in the workflow.

        Returns:
            list[TaskModel]: List of tasks in the workflow.
        """
        return self.records["TaskModel"]

    @property
    def inventory_filters(self) -> dict[str, Any]:
        """
        Get the inventory filters for the workflow.

        Returns:
            dict[str, Any]: Dictionary of inventory filters.
        """
        return self.records["WorkflowModel"][0].inventory_filters

    def _check_tasks(self, tasks_catalog: dict[str, Callable]) -> None:
        """
        Check if the tasks in the workflow are present in the tasks catalog.

        Args:
            tasks_catalog (dict[str, Callable]): The tasks catalog discovered by NornFlow.

        Raises:
            TaskDoesNotExistError: If any tasks in the workflow are not found in the tasks catalog.
        """
        task_names = [task.name for task in self.tasks]

        missing_tasks = [task_name for task_name in task_names if task_name not in tasks_catalog]

        if missing_tasks:
            raise TaskDoesNotExistError(missing_tasks)

    def _get_filtering_kwargs(self) -> list[dict[str, Any]]:
        """
        Generate a list of filter keyword argument dictionaries based on inventory_filters.

        This method examines the inventory_filters attribute and creates a list of keyword
        argument dictionaries for filtering. Each dictionary contains:
        - filter_func: The appropriate filter function (filter_by_hostname or filter_by_groups)
        - Either 'hostnames' or 'groups': The corresponding filter values

        Filters are included in the result in the exact order they appear in inventory_filters.
        Empty filter values are skipped.

        Returns:
            list[dict[str, Any]]: List of dictionaries with filter kwargs
        """
        filter_kwargs_list = []
        filter_keys = list(self.inventory_filters.keys())

        for key in filter_keys:
            filter_values = self.inventory_filters[key]
            if not filter_values:
                continue

            if key == "hosts":
                filter_kwargs_list.append({"filter_func": filter_by_hostname, "hostnames": filter_values})
            elif key == "groups":
                filter_kwargs_list.append({"filter_func": filter_by_groups, "groups": filter_values})

        return filter_kwargs_list

    def _apply_filters(self, nornir_manager: NornirManager, **kwargs: Any) -> None:
        """
        Apply filtering to the Nornir instance using the provided kwargs.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply filters to
            **kwargs (Any): Keyword arguments containing filter criteria
        """
        for filter_kwargs in self._get_filtering_kwargs():
            nornir_manager.apply_filters(**filter_kwargs)

    def _with_processors(self, nornir_manager: NornirManager, processor_obj: Processor) -> None:
        """
        Apply processors to the Nornir instance.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply processors to
        """
        nornir_manager.apply_processors([processor_obj])

    def run(self, nornir_manager: NornirManager, tasks_catalog: dict[str, Callable]) -> None:
        """
        Run the tasks in the workflow using the provided Nornir instance and tasks mapping.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to use for running the tasks.
            tasks_catalog (dict[str, Callable]): The tasks catalog discovered by NornFlow.
        """
        self._check_tasks(tasks_catalog)
        self._apply_filters(nornir_manager)

        # for the moment, hardcoding DefaultNornFlowProcessor, but this should be configurable
        processor_obj = DefaultNornFlowProcessor()
        self._with_processors(nornir_manager, processor_obj)

        for task in self.tasks:
            nornir_manager.nornir.run(task=tasks_catalog[task.name], **task.args or {})

        if hasattr(processor_obj, "print_final_workflow_summary"):
            processor_obj.print_final_workflow_summary()


class WorkflowFactory:
    """
    Factory class for creating Workflow objects from a file or a dictionary.

    Usage:
        - Instantiate with a workflow_path or workflow_dict.
        - Call the create() method to create a Workflow object.
        - Alternatively, use the static methods create_from_file() or create_from_dict().

    If both workflow_path and workflow_dict are provided, the file path takes precedence.
    """

    def __init__(self, workflow_path: str | Path | None = None, workflow_dict: dict[str, Any] | None = None):
        """
        Initialize the WorkflowFactory.

        Args:
            workflow_path (str | Path | None): Path to the workflow file.
            workflow_dict (dict[str, Any] | None): Dictionary representing the workflow.
        """
        self.workflow_path = workflow_path
        self.workflow_dict = workflow_dict

    def create(self) -> Workflow:
        """
        Create a Workflow object based on the provided parameters.

        Returns:
            Workflow: The created Workflow object.

        Raises:
            WorkflowInitializationError: If neither workflow_path nor workflow_dict is provided.
        """
        if self.workflow_path:
            return self.create_from_file(self.workflow_path)
        if self.workflow_dict:
            return self.create_from_dict(self.workflow_dict)

        raise WorkflowInitializationError("Either workflow_path or workflow_dict must be provided.")

    @staticmethod
    def create_from_file(workflow_path: str | Path) -> Workflow:
        """
        Create a Workflow object from a file.

        Args:
            workflow_path (str | Path): Path to the workflow file.

        Returns:
            Workflow: The created Workflow object.
        """
        loaded_dict = load_file_to_dict(workflow_path)
        return WorkflowFactory.create_from_dict(loaded_dict)

    @staticmethod
    def create_from_dict(workflow_dict: dict[str, Any]) -> Workflow:
        """
        Create a Workflow object from a dictionary.

        Args:
            workflow_dict (dict[str, Any]): Dictionary representing the workflow.

        Returns:
            Workflow: The created Workflow object.
        """
        return Workflow(workflow_dict)
