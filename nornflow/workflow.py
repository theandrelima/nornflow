import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir.core.processor import Processor
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.utils import generate_from_dict, load_file_to_dict

from nornflow.constants import NORNFLOW_SPECIAL_FILTER_KEYS
from nornflow.exceptions import TaskDoesNotExistError, WorkflowInitializationError
from nornflow.models import TaskModel
from nornflow.nornir_manager import NornirManager
from nornflow.processors import DefaultNornFlowProcessor
from nornflow.utils import resolve_special_filter

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
        return self.records["WorkflowModel"][0].inventory_filters or {}

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

        This method processes the inventory_filters and separates them into special filters
        (hosts, groups) that use custom filter functions, and direct attribute filters that
        are passed directly to Nornir's filter method.

        Returns:
            list[dict[str, Any]]: List of dictionaries with filter kwargs
        """
        # Start with empty lists for each filter type
        special_filters = []
        direct_filters = {}

        # Skip if no inventory filters defined
        if not self.inventory_filters:
            return []

        # Process each filter
        for key, filter_values in self.inventory_filters.items():
            if not filter_values:
                continue

            # Check if this is a special filter key
            if key in NORNFLOW_SPECIAL_FILTER_KEYS:
                filter_kwargs = resolve_special_filter(key, filter_values)
                if filter_kwargs:
                    special_filters.append(filter_kwargs)
                else:
                    # Fall back to direct filtering if the function doesn't exist
                    direct_filters[key] = filter_values
            else:
                # Add to direct filters for attribute-based filtering
                direct_filters[key] = filter_values

        # Special filters go first (preserving order), then direct filters if any
        filter_kwargs_list = special_filters
        if direct_filters:
            filter_kwargs_list.append(direct_filters)

        return filter_kwargs_list

    def _apply_filters(self, nornir_manager: NornirManager, **kwargs: Any) -> None:
        """
        Apply filtering to the Nornir instance.

        This method applies filters to the Nornir inventory in the order they were defined.
        It handles both special filters (hosts, groups) and direct attribute filters.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply filters to
            **kwargs (Any): Additional keyword arguments for filtering (not currently used)
        """
        filter_kwargs_list = self._get_filtering_kwargs()
        if not filter_kwargs_list:
            return

        for filter_kwargs in filter_kwargs_list:
            nornir_manager.apply_filters(**filter_kwargs)

    def _with_processors(self, nornir_manager: NornirManager, processor_obj: Processor) -> None:
        """
        Apply processors to the Nornir instance.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply processors to
            processor_obj (Processor): The processor to apply
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
