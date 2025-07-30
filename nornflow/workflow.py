import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir.core.processor import Processor
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.utils import generate_from_dict, load_file_to_dict

from nornflow.exceptions import (
    ProcessorError,
    TaskNotFoundError,
    WorkflowInitializationError,
    WorkflowInventoryFilterError,
)
from nornflow.models import TaskModel
from nornflow.nornir_manager import NornirManager
from nornflow.utils import load_processor
from nornflow.vars.constants import VARS_DIR_DEFAULT
from nornflow.vars.manager import NornFlowVariablesManager
from nornflow.vars.processors import NornFlowVariableProcessor

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
    - Managing variable resolution through the VariablesManager
    - Executing tasks in the defined sequence
    - Collecting and summarizing results

    Filter Parameter Formats:
    The workflow supports a flexible filter parameter system with multiple formats:
    1. Parameterless filters: `filter_name: null` or just `filter_name:`
    2. Named parameters as dict: `filter_name: {param1: value1, param2: value2}`
    3. Single list parameter: `filter_name: [item1, item2]` for a filter expecting a collection
    4. Ordered parameters as list: `filter_name: [value1, value2]` mapping to multiple parameters
    5. Single value parameter: `filter_name: value` for a filter with one parameter
    6. Direct attribute filtering: `attribute: value` for filtering by host attributes

    These formats allow maximum flexibility in workflow definition files while
    maintaining readability.

    Variables and CLI Variables:
    The workflow integrates with NornFlow's variable resolution system and supports
    both initialization-time and late-binding of CLI variables:

    - CLI variables can be provided during workflow creation via WorkflowFactory
    - CLI variables can also be provided/updated at runtime via the run() method
    - This dual approach allows maximum flexibility in different usage scenarios

    CLI Variables - Dual Nature:
    While named "CLI variables" due to their primary source being command-line arguments,
    these variables serve a dual purpose in NornFlow:
    1. Traditional CLI usage: Variables parsed from command-line arguments (--vars)
    2. Override mechanism: Programmatically set variables with highest precedence

    This dual nature allows CLI variables to be:
    - Set during workflow creation for traditional CLI workflows
    - Updated at runtime for dynamic behavior and programmatic control
    - Used as a universal override mechanism in complex automation scenarios

    The term "CLI variables" reflects their highest precedence nature and primary
    source, while also serving as a flexible override mechanism for any high-priority
    variable needs.

    For detailed information about the variable system hierarchy and precedence,
    see the NornFlow documentation.
    """

    def __init__(
        self,
        workflow_dict: dict[str, Any],
        vars_dir: str = VARS_DIR_DEFAULT,
        cli_vars: dict[str, Any] | None = None,
        workflow_path: Path | None = None,
    ):
        """
        Initialize the Workflow object.

        Args:
            workflow_dict (dict[str, Any]): Dictionary representing the workflow configuration
            vars_dir (str): Directory containing variable files
            cli_vars (Optional[dict[str, Any]]): Variables with highest precedence in the
                variable resolution chain. While named "CLI variables" due to their primary
                source being command-line arguments, these serve as a universal override
                mechanism that can be:
                - Parsed from actual CLI arguments (--vars)
                - Set programmatically for workflow customization
                - Updated at runtime via the run() method for maximum flexibility
                These variables always override any other variable source.
            workflow_path (Optional[Path]): Path to the workflow file (for domain variables)
        """
        self.workflow_dict = workflow_dict
        generate_from_dict(self.workflow_dict)
        self.records = get_global_data_store().records
        self.processors_config = self.workflow_dict.get("workflow", {}).get("processors")

        # Store variable-related parameters
        self.vars_dir = vars_dir
        self._cli_vars = cli_vars or {}  # Direct assignment for initialization
        self.workflow_path = workflow_path

        # Extract workflow vars from the workflow definition
        self.vars = self.workflow_dict.get("workflow", {}).get("vars", {})

        # Initialize variable manager (lazily in run() if needed)
        self.vars_manager = None

    @property
    def cli_vars(self) -> dict[str, Any]:
        """
        Get the CLI variables with highest precedence in the variable resolution chain.

        While named "CLI variables" due to their primary source being command-line arguments,
        these variables serve a dual purpose:
        1. Storage for variables parsed from CLI arguments (--vars)
        2. Universal override mechanism for programmatic variable setting

        These variables always have the highest precedence, overriding any other variable
        source including workflow variables, environment variables, and defaults.

        Returns:
            dict[str, Any]: Dictionary containing the CLI variables.
        """
        return self._cli_vars

    @cli_vars.setter
    def cli_vars(self, value: dict[str, Any]) -> None:
        """
        Set CLI variables. This supports both initialization-time setting and
        late-binding during the run() method.

        The late-binding capability allows CLI variables to be updated at runtime,
        supporting scenarios where:
        - NornFlow.run() passes updated CLI variables to workflows
        - Programmatic systems need to override variables based on runtime conditions
        - Same workflow object needs to be executed with different variable sets

        Args:
            value (dict[str, Any]): Dictionary of CLI variables with highest precedence
        """
        self._cli_vars = value or {}

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

        This method processes each filter key in inventory_filters and determines the appropriate
        handling approach. The filter processing supports two main scenarios:

        Custom Filter Functions:
        When the filter key exists in filters_catalog, it's treated as a custom filter function.
        These filters are processed by _process_custom_filter() which handles multiple parameter
        formats (see Filter Parameter Formats in class docstring).

        Direct Attribute Filtering:
        When the filter key is not in filters_catalog, it's treated as direct Nornir host
        attribute filtering (like name, platform, hostname, etc.). These are passed directly
        to Nornir's filtering system.

        Each filter is processed in the order defined in the workflow, with filters applied
        sequentially to narrow down the inventory selection (AND logic).

        Args:
            filters_catalog (dict[str, Callable]): Dictionary of available filter functions

        Returns:
            list[dict[str, Any]]: List of dictionaries with filter kwargs to be applied sequentially
        """
        # Skip if no inventory filters defined
        if not self.inventory_filters:
            return []

        # Process each filter in order
        filter_kwargs_list = []
        for key, filter_values in self.inventory_filters.items():
            if key in filters_catalog:
                # Custom filter function: Process with flexible parameter handling
                filter_kwargs = self._process_custom_filter(key, filter_values, filters_catalog)
                filter_kwargs_list.append(filter_kwargs)
            else:
                # Direct attribute filtering: Pass through to Nornir
                filter_kwargs_list.append({key: filter_values})

        return filter_kwargs_list

    def _process_custom_filter(
        self, key: str, filter_values: Any, filters_catalog: dict[str, Callable]
    ) -> dict[str, Any]:
        """
        Process a custom filter function from the filters_catalog.

        This method handles the flexible parameter passing system that allows workflow
        definitions to specify filter parameters in various user-friendly formats.
        The goal is to make workflow YAML files as readable and intuitive as possible
        while supporting the full range of filter function signatures.

        Supported Parameter Formats:

        Format 1: Parameterless Filters
            inventory_filters:
              is_active:          # No parameters needed
              # or
              is_active: null     # Explicit null

        Format 2: Named Parameters (Dictionary)
            inventory_filters:
              site_filter:
                region: "east"
                site_type: "campus"

        Format 3: Collection Parameter (List/Tuple for Single Parameter)
            inventory_filters:
              in_subnets: ["10.1.0.0/24", "10.2.0.0/24"]

        Format 4: Ordered Parameters (List/Tuple for Multiple Parameters)
            inventory_filters:
              location_filter: ["nyc", "hq"]  # Maps to (city, building) parameters

        Format 5: Single Scalar Parameter
            inventory_filters:
              exact_model: "C9300-48P"

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
            # Format 1: No additional parameters needed (parameterless filter)
            return filter_kwargs

        if isinstance(filter_values, dict):
            # Format 2: Named parameters provided as a dictionary
            return self._handle_dict_parameters(key, filter_values, param_names, filter_kwargs)

        if isinstance(filter_values, list | tuple) and len(param_names) == 1:
            # Format 3: Single parameter expecting a list/tuple collection
            filter_kwargs[param_names[0]] = filter_values
            return filter_kwargs

        if isinstance(filter_values, list | tuple) and len(filter_values) == len(param_names):
            # Format 4: Multiple parameters provided as a list in the correct order
            filter_kwargs.update(dict(zip(param_names, filter_values, strict=False)))
            return filter_kwargs

        if len(param_names) == 1:
            # Format 5: Single parameter with a scalar value
            filter_kwargs[param_names[0]] = filter_values
            return filter_kwargs

        # If we reached here, the parameter format is incompatible with the filter
        raise WorkflowInventoryFilterError(
            f"Filter '{key}' expects {len(param_names)} parameters {param_names}, "
            f"but got incompatible value: {filter_values}"
        )

    def _handle_dict_parameters(
        self, key: str, filter_values: dict, param_names: list[str], filter_kwargs: dict
    ) -> dict[str, Any]:
        """
        Handle dictionary-format filter parameters (Format 2).

        This method validates that all required parameters are provided when using
        the dictionary format for filter parameters. Dictionary format provides
        the most explicit mapping of parameter names to values and is the most
        readable format for complex filters with multiple parameters.

        Example usage in workflow YAML:
            inventory_filters:
              site_filter:
                region: "east"
                site_type: "campus"
                active: true

        Args:
            key: The filter name for error reporting
            filter_values: Dictionary of parameter values from workflow
            param_names: Expected parameter names for this filter function
            filter_kwargs: Base filter kwargs dict containing filter_func

        Returns:
            dict[str, Any]: Updated filter kwargs dictionary with all parameters

        Raises:
            WorkflowInventoryFilterError: If required parameters are missing from the dictionary
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

        This method applies filters to the Nornir inventory in the order they were defined
        in the workflow. Both custom filter functions and direct attribute filters are
        processed and applied sequentially, creating an AND relationship between filters.

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply filters to
            filters_catalog (dict[str, Callable]): Dictionary of available filter functions
        """
        filter_kwargs_list = self._get_filtering_kwargs(filters_catalog)
        if not filter_kwargs_list:
            return

        for filter_kwargs in filter_kwargs_list:
            nornir_manager.apply_filters(**filter_kwargs)

    def _init_variable_manager(self, workflows_dirs: list[str]) -> None:
        """
        Initialize the VariablesManager if it hasn't been created yet.

        This lazy initialization pattern ensures that:
        1. The VariablesManager is only created when actually needed (during workflow execution)
        2. CLI variables can be updated via late binding before the manager is created
        3. The most up-to-date variable values are used when resolving variables

        The manager integrates variables from multiple sources based on NornFlow's
        precedence rules, with CLI variables having the highest priority. The lazy
        initialization allows CLI variables to be updated at runtime before the
        variable resolution system is activated.
        """
        if self.vars_manager is None:
            self.vars_manager = NornFlowVariablesManager(
                vars_dir=self.vars_dir,
                cli_vars=self.cli_vars,  # Uses most recent CLI vars
                inline_workflow_vars=self.vars,
                workflow_path=self.workflow_path,
                workflow_roots=workflows_dirs,
            )

    def _with_processors(
        self,
        nornir_manager: NornirManager,
        workflows_dirs: list[str],
        processors: list[Processor] | None = None,
    ) -> None:
        """
        Apply processors to the Nornir instance based on configuration.

        IMPORTANT: Always adds NornFlowVariableProcessor as the first processor
        to ensure host context is available for variable resolution.

        This method handles the processor selection logic:
        1. Always add NornFlowVariableProcessor first (for variable resolution)
        2. Use workflow-specific processors from self.processors_config if defined
        3. Otherwise use the passed processors parameter
        4. If neither exists, do nothing (use NornFlow's global processors)

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply processors to
            processors (list[Processor] | None): List of processors to apply if no workflow-specific
                processors defined
        """
        # Ensure we have a variable manager
        self._init_variable_manager(workflows_dirs=workflows_dirs)

        # Create our variable processor for host-specific variable resolution
        var_processor = NornFlowVariableProcessor(self.vars_manager)

        # Start with the variable processor
        all_processors = [var_processor]

        # Apply workflow-specific processors if defined
        if self.processors_config:
            try:
                workflow_processors = []
                for processor_config in self.processors_config:
                    processor = load_processor(processor_config)
                    workflow_processors.append(processor)

                if workflow_processors:
                    all_processors.extend(workflow_processors)
            except Exception as e:
                raise ProcessorError(f"Failed to initialize workflow processors: {e!s}") from e
        # Otherwise use processors passed as parameter if provided
        elif processors:
            all_processors.extend(processors)

        # Apply all processors
        nornir_manager.apply_processors(all_processors)        

    def run(
        self,
        nornir_manager: NornirManager,
        tasks_catalog: dict[str, Callable],
        filters_catalog: dict[str, Callable],
        workflows_dirs: list[str] | None = None,
        processors: list[Processor] | None = None,
        cli_vars: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> None:
        """
        This method orchestrates the complete workflow execution process:
        1. Updates CLI variables if provided (late binding support)
        2. Initializes the variable manager with the current variable state
        3. Applies inventory filters to narrow down target devices
        4. Sets up processors (always including NornFlowVariableProcessor first)
        5. Executes each task in the defined sequence
        6. If a task has the 'set_to' keyword, its result is saved as a runtime variable.
        7. Prints final workflow summary via processors

        Late Binding of CLI Variables:
        The method supports late binding of CLI variables, allowing them to be provided
        or updated at runtime even after the workflow is created. This design enables:
        - NornFlow.run() to pass its CLI variables to workflows at execution time
        - Programmatic systems to override variables based on runtime conditions
        - The same workflow object to be reused with different variable sets

        The late binding pattern ensures maximum flexibility while maintaining the
        highest precedence for CLI variables in the variable resolution system.

        Args:
            nornir_manager: The NornirManager instance for task execution
            tasks_catalog: Dictionary of available task functions
            filters_catalog: Dictionary of available filter functions
            processors: List of processors to apply (if no workflow-specific processors)
            cli_vars: Optional CLI variables with highest precedence. Can override
                those set during initialization, enabling late binding for maximum
                flexibility in variable management.
            dry_run: Whether to execute the workflow in dry-run mode
        """
        # Update CLI variables if provided (late binding)
        if cli_vars is not None:
            self.cli_vars = cli_vars

        # Determine effective dry_run mode: CLI parameter takes precedence over workflow setting
        workflow_model = self.records["WorkflowModel"][0]
        effective_dry_run = dry_run or workflow_model.dry_run

        processors = processors or []

        # Make sure tasks exist in the catalog
        self._check_tasks(tasks_catalog)

        # Initialize variable manager with updated CLI vars
        self._init_variable_manager(workflows_dirs=workflows_dirs)

        # Apply inventory filters
        self._apply_filters(nornir_manager, filters_catalog)

        # Apply processors (NornFlowVariableProcessor will be added first)
        self._with_processors(nornir_manager, workflows_dirs, processors)

        # Set task count on processors that support it
        for processor in nornir_manager.nornir.processors:
            if hasattr(processor, "total_workflow_tasks"):
                processor.total_workflow_tasks = len(self.tasks)

        # Execute tasks in sequence with dry-run support
        for task in self.tasks:
            # Pass dry-run context to task execution
            nornir_manager.set_dry_run(effective_dry_run)
            
            # Run the task and capture its result
            aggregated_result = task.run(nornir_manager, tasks_catalog)

            # After the task runs, check if its 'set_to' attribute is defined.
            if hasattr(task, "set_to") and task.set_to:
                # The 'aggregated_result' is a dictionary of {host_name: Result}.
                # We must iterate through it to set the variable for each host,
                # because NornFlow Runtime Variables are per-device.
                for host_name, host_result in aggregated_result.items():
                    self.vars_manager.set_runtime_variable(
                        name=task.set_to,
                        value=host_result,  # The entire Nornir Result object for this host
                        host_name=host_name,
                    )

        # Call print_final_workflow_summary on processors that support it
        for processor in nornir_manager.nornir.processors:
            if hasattr(processor, "print_final_workflow_summary"):
                processor.print_final_workflow_summary()


class WorkflowFactory:
    """
    Factory class for creating Workflow objects from a file or a dictionary.

    Usage:
        - Instantiate with a workflow_path or workflow_dict.
        - Call the create() method to create a Workflow object.
        - Alternatively, use the static methods create_from_file() or create_from_dict().

    If both workflow_path and workflow_dict are provided, the file path takes precedence.

    CLI Variables in Factory Context:
    The factory supports setting CLI variables at workflow creation time. These variables
    have the highest precedence in the variable resolution system and serve a dual purpose:

    1. Traditional CLI representation: Variables parsed from command-line arguments
    2. Programmatic override mechanism: Variables set for highest precedence control

    The factory-set CLI variables can be:
    - Used immediately during workflow creation for variable resolution
    - Updated later via the workflow.run() method (late binding) for maximum flexibility
    - Overridden by runtime CLI variables passed to workflow execution

    This dual approach allows maximum flexibility in how and when CLI variables are
    provided to workflows, supporting both traditional CLI usage and advanced programmatic
    scenarios.
    """

    def __init__(
        self,
        workflow_path: str | Path | None = None,
        workflow_dict: dict[str, Any] | None = None,
        vars_dir: str = VARS_DIR_DEFAULT,
        cli_vars: dict[str, Any] | None = None,
    ):
        """
        Initialize the WorkflowFactory.

        Args:
            workflow_path (str | Path | None): Path to the workflow file
            workflow_dict (dict[str, Any] | None): Dictionary representing the workflow
            vars_dir (str): Directory containing variable files
            cli_vars (Optional[dict[str, Any]]): Variables with highest precedence in the
                variable resolution chain. While named "CLI variables" due to their primary
                source being command-line arguments, these serve as a universal override
                mechanism. These variables can be overridden later during workflow execution
                if new CLI variables are provided to workflow.run().
        """
        self.workflow_path = workflow_path
        self.workflow_dict = workflow_dict
        self.vars_dir = vars_dir
        self.cli_vars = cli_vars or {}

    def create(self) -> Workflow:
        """
        Create a Workflow object based on the provided parameters.

        Returns:
            Workflow: The created Workflow object with all configurations applied.

        Raises:
            WorkflowInitializationError: If neither workflow_path nor workflow_dict is provided.
        """
        if self.workflow_path:
            return self.create_from_file(self.workflow_path, vars_dir=self.vars_dir, cli_vars=self.cli_vars)
        if self.workflow_dict:
            return self.create_from_dict(self.workflow_dict, vars_dir=self.vars_dir, cli_vars=self.cli_vars)

        raise WorkflowInitializationError("Either workflow_path or workflow_dict must be provided.")

    @staticmethod
    def create_from_file(
        workflow_path: str | Path,
        vars_dir: str = VARS_DIR_DEFAULT,
        cli_vars: dict[str, Any] | None = None,
    ) -> Workflow:
        """
        Create a Workflow object from a file.

        Args:
            workflow_path (str | Path): Path to the workflow file
            vars_dir (str): Directory containing variable files
            cli_vars (Optional[dict[str, Any]]): Variables with highest precedence in the
                variable resolution chain

        Returns:
            Workflow: The created Workflow object.
        """
        loaded_dict = load_file_to_dict(workflow_path)
        path_obj = Path(workflow_path) if isinstance(workflow_path, str) else workflow_path
        return WorkflowFactory.create_from_dict(
            loaded_dict, vars_dir=vars_dir, cli_vars=cli_vars, workflow_path=path_obj
        )

    @staticmethod
    def create_from_dict(
        workflow_dict: dict[str, Any],
        vars_dir: str = VARS_DIR_DEFAULT,
        cli_vars: dict[str, Any] | None = None,
        workflow_path: Path | None = None,
    ) -> Workflow:
        """
        Create a Workflow object from a dictionary.

        Args:
            workflow_dict (dict[str, Any]): Dictionary representing the workflow
            vars_dir (str): Directory containing variable files
            cli_vars (Optional[dict[str, Any]]): Variables with highest precedence in the
                variable resolution chain
            workflow_path (Optional[Path]): Path to the workflow file (for domain variables)

        Returns:
            Workflow: The created Workflow object.
        """
        return Workflow(
            workflow_dict,
            vars_dir=vars_dir,
            cli_vars=cli_vars,
            workflow_path=workflow_path,
        )
