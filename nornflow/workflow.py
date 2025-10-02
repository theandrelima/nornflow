import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir.core.processor import Processor
from pydantic_serdes.datastore import get_global_data_store
from pydantic_serdes.utils import generate_from_dict, load_file_to_dict

from nornflow.builtins.processors import NornFlowFailureStrategyProcessor
from nornflow.constants import FailureStrategy
from nornflow.exceptions import (
    ProcessorError,
    TaskError,
    WorkflowError,
)
from nornflow.models import TaskModel
from nornflow.nornir_manager import NornirManager
from nornflow.settings import NornFlowSettings
from nornflow.utils import load_processor, print_workflow_overview
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
        settings: NornFlowSettings,
        cli_vars: dict[str, Any] | None = None,
        cli_filters: dict[str, Any] | None = None,
        cli_failure_strategy: FailureStrategy | None = None,
        workflow_path: Path | None = None,
    ):
        """
        Initialize the Workflow object.

        Args:
            workflow_dict (dict[str, Any]): Dictionary representing the workflow configuration
            settings (NornFlowSettings): NornFlow settings object containing all configuration
            cli_vars (dict[str, Any] | None): Variables with highest precedence in the
                variable resolution chain. While named "CLI variables" due to their primary
                source being command-line arguments, these serve as a universal override
                mechanism that can be:
                - Parsed from actual CLI arguments (--vars)
                - Set programmatically for workflow customization
                - Updated at runtime via the run() method for maximum flexibility
                These variables always override any other variable source.
            cli_filters (dict[str, Any] | None): Inventory filters from CLI that override
                workflow inventory filters. Like cli_vars, these have the highest precedence.
            cli_failure_strategy (FailureStrategy | None): Failure strategy from CLI that overrides
                the workflow's failure strategy. If not provided, the workflow's default is used.
            workflow_path (Path | None): Path to the workflow file (for domain variables)
        """
        self.workflow_dict = workflow_dict
        generate_from_dict(self.workflow_dict)
        self.records = get_global_data_store().records
        self.processors_config = self.workflow_dict.get("workflow", {}).get("processors")
        self.settings = settings
        self._cli_vars = cli_vars or {}
        self._cli_filters = cli_filters or {}
        self._cli_failure_strategy = cli_failure_strategy
        self.workflow_path = workflow_path
        self.vars = self.workflow_dict.get("workflow", {}).get("vars", {})
        self._vars_manager = None
        self._var_processor = None
        self._failure_processor = None

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
    def cli_filters(self) -> dict[str, Any]:
        """
        Get the CLI inventory filters with highest precedence.

        These filters override any inventory filters defined in the workflow YAML.
        Like CLI variables, they serve as a mechanism for the CLI to override
        workflow-defined settings.

        Returns:
            dict[str, Any]: Dictionary containing the CLI inventory filters.
        """
        return self._cli_filters

    @cli_filters.setter
    def cli_filters(self, value: dict[str, Any]) -> None:
        """
        Set CLI inventory filters. This supports both initialization-time setting and
        late-binding during the run() method.

        Args:
            value (dict[str, Any]): Dictionary of CLI inventory filters with highest precedence
        """
        self._cli_filters = value or {}

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
            raise WorkflowError("Missing 'workflow' key in workflow definition")

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

        If CLI inventory filters are provided, they completely override
        any workflow-defined filters. Otherwise, workflow filters are used.

        Returns:
            dict[str, Any]: Dictionary of inventory filters.
        """
        if self.cli_filters:
            return self.cli_filters

        return self.records["WorkflowModel"][0].inventory_filters or {}

    @property
    def failure_strategy(self) -> FailureStrategy:
        """
        Get the failure strategy for the workflow.

        If a CLI failure strategy is provided, it overrides the workflow's failure strategy.
        Otherwise, the workflow's default failure strategy is used.

        Returns:
            FailureStrategy: The active error handling strategy.
        """
        if self._cli_failure_strategy is not None:
            return self._cli_failure_strategy

        return self.records["WorkflowModel"][0].failure_strategy

    @property
    def vars_manager(self) -> NornFlowVariablesManager | None:
        """
        Get the variables manager instance.

        Returns:
            NornFlowVariablesManager | None: The variables manager, or None if not initialized.
        """
        return self._vars_manager

    @vars_manager.setter
    def vars_manager(self, value: NornFlowVariablesManager) -> None:
        """
        Set the variables manager instance.

        Args:
            value (NornFlowVariablesManager): The variables manager to set.
        """
        self._vars_manager = value

    @property
    def var_processor(self) -> NornFlowVariableProcessor | None:
        """
        Get the variable processor instance.

        Returns:
            NornFlowVariableProcessor | None: The variable processor, or None if not set.
        """
        return self._var_processor

    @var_processor.setter
    def var_processor(self, value: NornFlowVariableProcessor) -> None:
        """
        Set the variable processor instance.

        Args:
            value (NornFlowVariableProcessor): The variable processor to set.
        """
        self._var_processor = value

    @property
    def failure_processor(self) -> NornFlowFailureStrategyProcessor | None:
        """
        Get the failure strategy processor instance.

        Returns:
            NornFlowFailureStrategyProcessor | None: The failure processor, or None if not set.
        """
        return self._failure_processor

    @failure_processor.setter
    def failure_processor(self, value: NornFlowFailureStrategyProcessor) -> None:
        """
        Set the failure strategy processor instance.

        Args:
            value (NornFlowFailureStrategyProcessor): The failure processor to set.
        """
        self._failure_processor = value

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
            raise TaskError(f"Tasks not found in catalog: {missing_tasks}")

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
        raise WorkflowError(
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
            raise WorkflowError(
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
                vars_dir=self.settings.vars_dir,
                cli_vars=self.cli_vars,
                inline_workflow_vars=self.vars,
                workflow_path=self.workflow_path,
                workflow_roots=workflows_dirs,
            )

    def _with_processors(
        self,
        nornir_manager: NornirManager,
        processors: list[Processor] | None = None,
    ) -> None:
        """
        Apply processors to the Nornir instance based on configuration.

        IMPORTANT: Always adds NornFlowVariableProcessor as the first processor
        to ensure host context is available for variable resolution.
        Always adds NornFlowFailureStrategyProcessor as the second processor
        to handle error policies during task execution.

        This method handles the processor selection logic:
        1. Always add NornFlowVariableProcessor first (for variable resolution)
        2. Always add NornFlowFailureStrategyProcessor second (for failure strategy handling)
        3. Use workflow-specific processors from self.processors_config if defined
        4. Otherwise use the passed processors parameter
        5. If neither exists, do nothing (use NornFlow's global processors)

        Args:
            nornir_manager (NornirManager): The NornirManager instance to apply processors to
            processors (list[Processor] | None): List of processors to apply if no workflow-specific
                processors defined
        """
        # Create our variable processor for host-specific variable resolution
        self.var_processor = NornFlowVariableProcessor(self.vars_manager)

        # Create processor with the active failure strategy
        self.failure_processor = NornFlowFailureStrategyProcessor(self.failure_strategy)

        # Start with the variable processors
        all_processors = [self.var_processor]

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

        # we want the error processor to be the last one, so error summaries
        # appear last too
        all_processors.append(self.failure_processor)

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
        cli_filters: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> int:
        """
        This method orchestrates the complete workflow execution process:
        1. Updates CLI variables if provided (late binding support)
        2. Initializes the variable manager with the current variable state
        3. Applies inventory filters to narrow down target devices
        4. Sets up processors (always including NornFlowVariableProcessor first)
        5. Executes each task in the defined sequence
        6. If a task has the 'set_to' keyword, its result is saved as a runtime variable.
        7. Prints final workflow summary via processors
        8. Returns an int representing the execution status, that can be
        used as the POSIX exit code for this Workflow run

        Exit Codes: 0-100, indicates the percentage of failed task executions (rounded down)

        Any exceptions that might happen in the encapsulated logic will just bubble-up
        back to the caller of Workflow.run(). This is to allow the caller the flexibility
        to process and handle it as fits.

        Args:
            nornir_manager: The NornirManager instance for task execution
            tasks_catalog: Dictionary of available task functions
            filters_catalog: Dictionary of available filter functions
            processors: List of processors to apply (if no workflow-specific processors)
            cli_vars: Optional CLI variables with highest precedence. Can override
                those set during initialization, enabling late binding for maximum
                flexibility in variable management.
            cli_filters: Optional CLI inventory filters with highest precedence.
                Can override those set during initialization, enabling late binding.
            dry_run: Whether to execute the workflow in dry-run mode

        Returns:
            int: Exit code representing the execution status
        """
        # Update CLI variables if provided (late binding)
        if cli_vars is not None:
            self.cli_vars = cli_vars

        # Update CLI filters if provided (late binding)
        if cli_filters is not None:
            self.cli_filters = cli_filters

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
        self._with_processors(nornir_manager, processors)

        # Print comprehensive workflow overview after loading
        hosts_count = len(nornir_manager.nornir.inventory.hosts)
        print_workflow_overview(
            workflow_model=workflow_model,
            effective_dry_run=effective_dry_run,
            hosts_count=hosts_count,
            inventory_filters=self.inventory_filters,
            workflow_vars=self.vars,
            cli_vars=self._cli_vars,
            failure_strategy=self.failure_strategy,
        )

        # Set task count on processors that support it
        for processor in nornir_manager.nornir.processors:
            if hasattr(processor, "total_workflow_tasks"):
                processor.total_workflow_tasks = len(self.tasks)

        # Execute tasks in sequence with dry-run support
        for task in self.tasks:
            # Pass dry-run context to task execution
            nornir_manager.set_dry_run(effective_dry_run)

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

        exit_code = 0

        # Try to find a processor with task execution statistics
        for processor in nornir_manager.nornir.processors:
            try:
                task_executions = getattr(processor, "task_executions", 0)
                failed_executions = getattr(processor, "failed_executions", 0)

                # Ensure values are numeric and task_executions is not zero
                if (
                    isinstance(task_executions, int)
                    and isinstance(failed_executions, int)
                    and task_executions
                    and failed_executions
                ):
                    failure_percentage = int((failed_executions / task_executions) * 100)
                    return failure_percentage

            except Exception:  # noqa: S112, PERF203
                continue

        return exit_code


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
        settings: NornFlowSettings | None = None,
        cli_vars: dict[str, Any] | None = None,
        cli_filters: dict[str, Any] | None = None,
        cli_failure_strategy: FailureStrategy | None = None,
    ):
        """
        Initialize the WorkflowFactory.

        Args:
            workflow_path (str | Path | None): Path to the workflow file
            workflow_dict (dict[str, Any] | None): Dictionary representing the workflow
            settings (NornFlowSettings | None): NornFlow settings object. If not provided,
                a default one will be created.
            cli_vars (dict[str, Any] | None): Variables with highest precedence in the
                variable resolution chain. While named "CLI variables" due to their primary
                source being command-line arguments, these serve as a universal override
                mechanism. These variables can be overridden later during workflow execution
                if new CLI variables are provided to workflow.run().
            cli_filters (dict[str, Any] | None): Inventory filters with highest precedence.
                These override any inventory filters defined in the workflow YAML.
            cli_failure_strategy (FailureStrategy | None): Failure strategy with highest precedence.
                Overrides the workflow's failure strategy if provided.
        """
        self.workflow_path = workflow_path
        self.workflow_dict = workflow_dict
        self.settings = settings or NornFlowSettings()
        self.cli_vars = cli_vars or {}
        self.cli_filters = cli_filters or {}
        self.cli_failure_strategy = cli_failure_strategy

    def create(self) -> Workflow:
        """
        Create a Workflow object based on the provided parameters.

        Returns:
            Workflow: The created Workflow object with all configurations applied.

        Raises:
            WorkflowInitializationError: If neither workflow_path nor workflow_dict is provided.
        """
        if self.workflow_path:
            return self.create_from_file(
                self.workflow_path,
                settings=self.settings,
                cli_vars=self.cli_vars,
                cli_filters=self.cli_filters,
                cli_failure_strategy=self.cli_failure_strategy,
            )
        if self.workflow_dict:
            return self.create_from_dict(
                self.workflow_dict,
                settings=self.settings,
                cli_vars=self.cli_vars,
                cli_filters=self.cli_filters,
                cli_failure_strategy=self.cli_failure_strategy,
                workflow_path=None,
            )

        raise WorkflowError("Either workflow_path or workflow_dict must be provided.")

    @staticmethod
    def create_from_file(
        workflow_path: str | Path,
        settings: NornFlowSettings | None = None,
        cli_vars: dict[str, Any] | None = None,
        cli_filters: dict[str, Any] | None = None,
        cli_failure_strategy: FailureStrategy | None = None,
    ) -> Workflow:
        """
        Create a Workflow object from a file.

        Args:
            workflow_path (str | Path): Path to the workflow file
            settings (NornFlowSettings | None): NornFlow settings object. If not provided,
                a default one will be created.
            cli_vars (dict[str, Any] | None): Variables with highest precedence in the
                variable resolution chain
            cli_filters (dict[str, Any] | None): Inventory filters with highest precedence
            cli_failure_strategy (FailureStrategy | None): Failure strategy with highest precedence

        Returns:
            Workflow: The created Workflow object.
        """
        loaded_dict = load_file_to_dict(workflow_path)
        path_obj = Path(workflow_path) if isinstance(workflow_path, str) else workflow_path
        settings = settings or NornFlowSettings()
        return Workflow(
            loaded_dict,
            settings=settings,
            cli_vars=cli_vars,
            cli_filters=cli_filters,
            cli_failure_strategy=cli_failure_strategy,
            workflow_path=path_obj,
        )

    @staticmethod
    def create_from_dict(
        workflow_dict: dict[str, Any],
        settings: NornFlowSettings | None = None,
        cli_vars: dict[str, Any] | None = None,
        cli_filters: dict[str, Any] | None = None,
        cli_failure_strategy: FailureStrategy | None = None,
        workflow_path: Path | None = None,
    ) -> Workflow:
        """
        Create a Workflow object from a dictionary.

        Args:
            workflow_dict (dict[str, Any]): Dictionary representing the workflow
            settings (NornFlowSettings | None): NornFlow settings object. If not provided,
                a default one will be created.
            cli_vars (dict[str, Any] | None): Variables with highest precedence in the
                variable resolution chain
            cli_filters (dict[str, Any] | None): Inventory filters with highest precedence
            cli_failure_strategy (FailureStrategy | None): Failure strategy with highest precedence
            workflow_path (Path | None): Path to the workflow file (for domain variables)

        Returns:
            Workflow: The created Workflow object.
        """
        settings = settings or NornFlowSettings()
        return Workflow(
            workflow_dict,
            settings=settings,
            cli_vars=cli_vars,
            cli_filters=cli_filters,
            cli_failure_strategy=cli_failure_strategy,
            workflow_path=workflow_path,
        )
