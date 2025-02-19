import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir.core import Nornir
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.utils import generate_from_dict, load_file_to_dict

from nornflow.exceptions import TaskDoesNotExistError, WorkflowInitializationError
from nornflow.inventory_filters import filter_by_groups, filter_by_hostname
from nornflow.models import TaskModel
from nornflow.processors import DefaultNornFlowProcessor

# making sure pydantic_serdes sees Workflow models
os.environ["MODELS_MODULES"] = "nornflow.models"


class Workflow:
    """
    Class representing a workflow in NornFlow.

    A workflow is a sequence of one or more Nornir tasks that can be run on a Nornir inventory.
    """

    def __init__(self, **kwargs: Any):
        """
        Initialize the Workflow object.

        Args:
            **kwargs (Any): Keyword arguments representing the workflow configuration.
        """
        self.workflow_dict = kwargs
        generate_from_dict(self.workflow_dict)
        self.records = get_global_data_store().records

    @property
    def workflow_dict(self) -> dict[str, Any]:
        """
        Get the workflow dictionary.

        Returns:
            Dict[str, Any]: The workflow dictionary.
        """
        return self._workflow_dict

    @workflow_dict.setter
    def workflow_dict(self, wf_dict: dict[str, Any]) -> None:
        """
        Set the workflow dictionary.

        Args:
            wf_dict (Dict[str, Any]): The workflow dictionary.
        """
        desired_keys_order = ["tasks", "workflow_configs"]
        self._workflow_dict = {key: wf_dict[key] for key in desired_keys_order}

    @property
    def tasks(self) -> list[TaskModel]:
        """
        Get the tasks in the workflow.

        Returns:
            List[TaskModel]: List of tasks in the workflow.
        """
        return self.records["TaskModel"]

    @property
    def inventory_filters(self) -> dict[str, Any]:
        """
        Get the inventory filters for the workflow.

        Returns:
            Dict[str, Any]: Dictionary of inventory filters.
        """
        return self.records["WorkflowModel"][0].inventory_filters

    def _check_tasks(self, tasks_catalog: dict[str, Callable]) -> None:
        """
        Check if the tasks in the workflow are present in the tasks catalog.

        Args:
            tasks_catalog (Dict[str, Callable]): The tasks catalog discovered by NornFlow.

        Raises:
            TaskDoesNotExistError: If any tasks in the workflow are not found in the tasks catalog.
        """
        task_names = [task.name for task in self.tasks]

        missing_tasks = [task_name for task_name in task_names if task_name not in tasks_catalog]

        if missing_tasks:
            raise TaskDoesNotExistError(missing_tasks)

    def _filter_inventory(self, nornir: Nornir) -> None:
        """
        Filter the inventory based on the inventory_filters attribute.
        """
        hosts, groups = self.inventory_filters.get("hosts"), self.inventory_filters.get("groups")

        if hosts:
            nornir = nornir.filter(filter_func=filter_by_hostname, hostnames=self.inventory_filters["hosts"])

        if groups:
            nornir = nornir.filter(filter_func=filter_by_groups, groups=self.inventory_filters["groups"])

    def _with_processors(self, nornir: Nornir) -> None:
        """
        Apply processors to the Nornir instance.
        """
        return nornir.with_processors([DefaultNornFlowProcessor()])
    
    def run(self, nornir: Nornir, tasks_catalog: dict[str, Callable]) -> None:
        """
        Run the tasks in the workflow using the provided Nornir instance and tasks mapping.

        Args:
            nornir (Nornir): The Nornir instance to use for running the tasks.
            tasks_catalog (dict[str, Callable]): The tasks catalog discovered by NornFlow.
        """
        self._check_tasks(tasks_catalog)
        self._filter_inventory(nornir)
        nornir = self._with_processors(nornir)

        for task in self.tasks:
            result = nornir.run(task=tasks_catalog[task.name], **task.args or {})


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
            workflow_path (Optional[Union[str, Path]]): Path to the workflow file.
            workflow_dict (Optional[dict[str, Any]]): Dictionary representing the workflow.
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
            workflow_path (Union[str, Path]): Path to the workflow file.

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
        return Workflow(**workflow_dict)
