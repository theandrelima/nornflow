import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir.core.processor import Processor
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.utils import generate_from_dict, load_file_to_dict

from nornflow.constants import NORNFLOW_SPECIAL_FILTER_KEYS
from nornflow.exceptions import TaskDoesNotExistError, WorkflowInitializationError, WorkflowInventoryFilterError
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

    def _get_filtering_kwargs(self, filters_catalog: dict[str, Callable]) -> list[dict[str, Any]]:
        """
        Generate a list of filter keyword argument dictionaries based on inventory_filters.
        
        This method processes the inventory_filters and converts them into filter kwargs
        that can be applied to a Nornir instance. The filters can be either:
        - Custom filter functions from the filters_catalog
        - Direct attribute filters passed directly to Nornir
        
        Returns:
            list[dict[str, Any]]: List of dictionaries with filter kwargs
        """
        # Skip if no inventory filters defined
        if not self.inventory_filters:
            return []
        
        # Process each filter
        filter_kwargs_list = []
        for key, filter_values in self.inventory_filters.items():
            if key in filters_catalog:
                # We first check if a key under 'inventory_filters' is a filter function in the filters_catalog
                filter_kwargs = self._process_custom_filter(key, filter_values, filters_catalog)
                filter_kwargs_list.append(filter_kwargs)
            else:
                # NOTE: cases 1-6 are covered by _process_custom_filter
                # Case 7: No matching filter function - use direct attribute filtering
                # This handles Nornir's built-in Host-based basic filtering (like name, platform, etc.)
                filter_kwargs_list.append({key: filter_values})
                
        return filter_kwargs_list
    
    def _process_custom_filter(self, key: str, filter_values: Any, 
                             filters_catalog: dict[str, Callable]) -> dict[str, Any]:
        """
        Process a single custom filter and its values.
        
        Args:
            key: The filter name/key
            filter_values: The values for this filter
            filters_catalog: Dictionary mapping filter names to (func, param_names) tuples
            
        Returns:
            dict[str, Any]: Filter kwargs dictionary for this filter
            
        Raises:
            WorkflowInventoryFilterError: If parameter validation fails
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
            
        elif isinstance(filter_values, dict):
            # Case 2: Parameters provided as a dictionary
            return self._handle_dict_parameters(key, filter_values, param_names, filter_kwargs)
            
        elif isinstance(filter_values, (list, tuple)) and len(param_names) == 1:
            # Case 3: Single parameter expecting a list/tuple
            # The filter takes one parameter which is a list/tuple
            filter_kwargs[param_names[0]] = filter_values
            return filter_kwargs
            
        elif isinstance(filter_values, (list, tuple)) and len(filter_values) == len(param_names):
            # Case 4: Multiple parameters provided as a list in the correct order
            # Create a dictionary by zipping parameter names with their values
            filter_kwargs.update(dict(zip(param_names, filter_values)))
            return filter_kwargs
            
        elif len(param_names) == 1:
            # Case 5: Single parameter with a scalar value
            # The filter takes one parameter with a simple value
            filter_kwargs[param_names[0]] = filter_values
            return filter_kwargs
            
        else:
            # Case 6: Parameter mismatch - incompatible values format
            raise WorkflowInventoryFilterError(
                f"Filter '{key}' expects {len(param_names)} parameters {param_names}, "
                f"but got incompatible value: {filter_values}"
            )
    
    def _handle_dict_parameters(self, key: str, filter_values: dict, 
                              param_names: list[str], filter_kwargs: dict) -> dict[str, Any]:
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
            **kwargs (Any): Additional keyword arguments for filtering (not currently used)
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

    def run(self, nornir_manager: NornirManager, tasks_catalog: dict[str, Callable], filters_catalog: dict[str, Callable]) -> None:
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
