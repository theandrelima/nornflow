import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir.core.processor import Processor
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.utils import generate_from_dict, load_file_to_dict

from nornflow.exceptions import (
    TaskNotFoundError,
    WorkflowInitializationError,
    WorkflowInventoryFilterError,
)
from nornflow.models import TaskModel
from nornflow.nornir_manager import NornirManager
from nornflow.processors import DefaultNornFlowProcessor

# making sure pydantic_serdes sees Workflow models
os.environ["MODELS_MODULES"] = "nornflow.models"


class Workflow:
    """
    Workflow represents a sequence of tasks to be executed against a Nornir inventory.

    This class handles the loading, parsing, and execution of workflow definitions,
    including inventory filtering, task sequencing, and result handling.

    Key responsibilities:
    - Parsing workflow definitions from YAML or dictionaries
    - Processing inventory filters in sequence (applying AND logic)
    - Supporting multiple filter formats:
      - Built-in filters (hosts, groups)
      - Custom filter functions with various parameter formats
      - Direct attribute filtering
    - Executing tasks in the defined sequence
    - Collecting and summarizing results
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
            TaskNotFoundError: If any tasks in the workflow are not found in the tasks catalog.
        """
        task_names = [task.name for task in self.tasks]

        missing_tasks = [task_name for task_name in task_names if task_name not in tasks_catalog]

        if missing_tasks:
            raise TaskNotFoundError(missing_tasks)

    def _get_filtering_kwargs(self, filters_catalog: dict[str, Callable]) -> list[dict[str, Any]]:
        """
        Generate a list of filter keyword argument dictionaries based on inventory_filters.

        This method processes each key in inventory_filters and determines how to handle it:
        1. If the key exists in filters_catalog: Process as a custom filter function
        2. Otherwise: Process as a direct attribute filter for Nornir

        Each filter is processed in the order defined in the YAML/dict, with filters applied
        sequentially to narrow down the inventory selection.

        Args:
            filters_catalog (dict[str, Callable]): Dictionary of available filter functions

        Returns:
            list[dict[str, Any]]: List of dictionaries with filter kwargs to be applied sequentially
        """
        # Skip if no inventory filters defined
        if not self.inventory_filters:
            return []

        # Process each filter
        filter_kwargs_list = []
        for key, filter_values in self.inventory_filters.items():
            if key in filters_catalog:
                # We first check if a key under 'inventory_filters'
                # is a filter function in the filters_catalog
                filter_kwargs = self._process_custom_filter(key, filter_values, filters_catalog)
                filter_kwargs_list.append(filter_kwargs)
            else:
                # NOTE: cases 1-6 are covered by _process_custom_filter
                # Case 7: No matching filter function - use direct attribute filtering
                # This handles Nornir's built-in Host-based basic filtering (like name, platform, etc.)
                filter_kwargs_list.append({key: filter_values})

        return filter_kwargs_list

    def _process_custom_filter(
        self, key: str, filter_values: Any, filters_catalog: dict[str, Callable]
    ) -> dict[str, Any]:
        """
        Process a custom filter function from the filters_catalog.

        Handles various parameter passing formats:
        1. No parameters (parameterless filter)
        2. Dictionary of named parameters
        3. List/tuple for a single parameter expecting a collection
        4. List/tuple of values mapping to multiple parameters in order
        5. Single scalar value for a filter with one parameter

        Args:
            key (str): The filter name/key from inventory_filters
            filter_values (Any): The value associated with the filter key
            filters_catalog (dict[str, Callable]): Dictionary of available filter functions

        Returns:
            dict[str, Any]: Dictionary with filter_func and any parameters to be passed to Nornir

        Raises:
            WorkflowInventoryFilterError: If parameter format doesn't match filter requirements
        """
        # Get the filter function and its parameter names
        filter_func, param_names = filters_catalog[key]

        # Start with filter_func parameter
        filter_kwargs = {"filter_func": filter_func}

        # Handle the filter values based on their type and the expected parameters
        if not param_names:
            # Case 1: No additional parameters needed besides host (parameter-less filter)
            # Just use the filter function with no additional parameters
            return filter_kwargs

        if isinstance(filter_values, dict):
            # Case 2: Parameters provided as a dictionary
            return self._handle_dict_parameters(key, filter_values, param_names, filter_kwargs)

        if isinstance(filter_values, list | tuple) and len(param_names) == 1:
            # Case 3: Single parameter expecting a list/tuple
            # The filter takes one parameter which is a list/tuple
            filter_kwargs[param_names[0]] = filter_values
            return filter_kwargs

        if isinstance(filter_values, list | tuple) and len(filter_values) == len(param_names):
            # Case 4: Multiple parameters provided as a list in the correct order
            # Create a dictionary by zipping parameter names with their values
            filter_kwargs.update(dict(zip(param_names, filter_values, strict=False)))
            return filter_kwargs

        if len(param_names) == 1:
            # Case 5: Single parameter with a scalar value
            # The filter takes one parameter with a simple value
            filter_kwargs[param_names[0]] = filter_values
            return filter_kwargs

        # Case 6: Parameter mismatch - incompatible values format
        raise WorkflowInventoryFilterError(
            f"Filter '{key}' expects {len(param_names)} parameters {param_names}, "
            f"but got incompatible value: {filter_values}"
        )

    def _handle_dict_parameters(
        self, key: str, filter_values: dict, param_names: list[str], filter_kwargs: dict
    ) -> dict[str, Any]:
        """
        Handle the case where filter parameters are provided as a dictionary.

        Args:
            key: The filter name
            filter_values: Dictionary of parameter values
            param_names: Expected parameter names
            filter_kwargs: Base filter kwargs dict

        Returns:
            dict[str, Any]: Updated filter kwargs dictionary

        Raises:
            WorkflowInventoryFilterError: If required parameters are missing
        """
        # Check that all required parameters are provided
        missing_params = set(param_names) - set(filter_values.keys())
        if missing_params:
            raise WorkflowInventoryFilterError(
                f"Filter '{key}' requires parameters {param_names}, but missing: {missing_params}"
            )

        # Add only the expected parameters from the dict
        for param in param_names:
            if param in filter_values:
                filter_kwargs[param] = filter_values[param]

        return filter_kwargs

    def _apply_filters(self, nornir_manager: NornirManager, filters_catalog: dict[str, Callable]) -> None:
        """
        Apply filtering to the Nornir instance.

        This method applies filters to the Nornir inventory in the order they were defined.
        It handles both special filters (hosts, groups) and direct attribute filters.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply filters to
            filters_catalog (dict[str, Callable]): Dictionary of available filter functions
        """
        filter_kwargs_list = self._get_filtering_kwargs(filters_catalog)
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

    def run(
        self,
        nornir_manager: NornirManager,
        tasks_catalog: dict[str, Callable],
        filters_catalog: dict[str, Callable],
    ) -> None:
        """
        Run the tasks in the workflow using the provided Nornir instance and tasks mapping.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to use for running the tasks.
            tasks_catalog (dict[str, Callable]): The tasks catalog discovered by NornFlow.
            filters_catalog (dict[str, Callable]): The filters catalog discovered by NornFlow.

        """
        self._check_tasks(tasks_catalog)
        self._apply_filters(nornir_manager, filters_catalog)

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
