from pathlib import Path
from typing import Any

from pydantic_serdes.utils import load_file_to_dict

from nornflow.builtins import DefaultNornFlowProcessor, filters as builtin_filters, tasks as builtin_tasks
from nornflow.builtins.processors import NornFlowFailureStrategyProcessor
from nornflow.catalogs import FileCatalog, PythonEntityCatalog
from nornflow.constants import FailureStrategy, NORNFLOW_INVALID_INIT_KWARGS
from nornflow.exceptions import (
    CatalogError,
    CoreError,
    InitializationError,
    NornirError,
    ProcessorError,
    ResourceError,
    SettingsError,
    TaskError,
    WorkflowError,
)
from nornflow.models import WorkflowModel
from nornflow.nornir_manager import NornirManager
from nornflow.settings import NornFlowSettings
from nornflow.utils import (
    is_nornir_filter,
    is_nornir_task,
    is_workflow_file,
    load_processor,
    process_filter,
    print_workflow_overview,
)
from nornflow.vars.manager import NornFlowVariablesManager
from nornflow.vars.processors import NornFlowVariableProcessor


class NornFlow:
    """
    NornFlow extends Nornir with a structured workflow system, task discovery, and configuration
    management capabilities. It serves as the main entry point for executing network automation
    jobs that follow a defined workflow pattern.

    Key features:
    - Assets auto-discovery from local directories
    - Workflow management and execution
    - Consistent configuration handling
    - Advanced inventory filtering with custom filter functions
    - Customizable execution processors
    - Variables system with multi-level precedence

    The NornFlow object lifecycle typically involves:
    1. Initialization with settings (from file or explicit object)
    2. Automatic discovery of available tasks
    3. Automatic discovery of available workflows (not mandatory)
    4. Automatic discovery of available filters (not mandatory)
    5. Selection of a workflow (by object, name, file path, or dictionary definition)
    6. Execution of the workflow against the filtered Nornir inventory

    Tasks are executed in order as defined in the workflow, providing a structured
    approach to network automation operations.

    Processor precedence follows this order (highest to lowest priority):
    1. Processors provided directly to the NornFlow constructor
    2. Processors specified in the workflow definition
    3. Processors specified in the NornFlow settings
    4. Default processor if none of the above are specified

    Variable precedence follows this order (highest to lowest priority):
    1. Vars (passed via command line or set programmatically as overrides)
    2. Workflow variables (defined in workflow file)
    3. Environment variables
    4. Variables from external files
    """

    def __init__(
        self,
        nornflow_settings: NornFlowSettings | None = None,
        workflow: WorkflowModel | str | None = None,
        processors: list[dict[str, Any]] | None = None,
        vars: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
        failure_strategy: FailureStrategy | None = None,
        **kwargs: Any,
    ):
        """
        Initialize a NornFlow instance.

        Args:
            nornflow_settings: NornFlow configuration settings object
            workflow: Pre-configured WorkflowModel instance or workflow name string (optional)
            processors: List of processor configurations to override default processors
            vars: Variables with highest precedence in the resolution chain.
                While named "vars" due to their primary source being command-line
                arguments, these serve as a universal override mechanism that can be:
                - Parsed from actual CLI arguments (--vars)
                - Set programmatically for workflow customization
                - Updated at runtime for dynamic behavior
                These variables always override any other variable source.
            filters: Inventory filters with highest precedence. These completely override
                any inventory filters defined in the workflow YAML.
            failure_strategy: Failure strategy with highest precedence. This overrides any failure
                strategy defined in the workflow YAML.
            **kwargs: Additional keyword arguments passed to NornFlowSettings

        Raises:
            InitializationError: If initialization fails due to invalid configuration
        """
        try:
            self._check_invalid_kwargs(kwargs)

            if nornflow_settings:
                self._settings = nornflow_settings
            else:
                try:
                    self._settings = NornFlowSettings(**kwargs)
                except (SettingsError, ResourceError) as e:
                    raise InitializationError(f"Failed to initialize NornFlow settings: {e}") from e

            self._vars = vars or {}
            self._filters = filters or {}
            self._failure_strategy = failure_strategy
            self._processors = processors

            self._tasks_catalog = PythonEntityCatalog("tasks")
            self._filters_catalog = PythonEntityCatalog("filters")
            self._workflows_catalog = FileCatalog("workflows")

            self._load_tasks_catalog()
            self._load_filters_catalog()
            self._load_workflows_catalog()

            self._workflow = None
            self.workflow_path = None
            self._var_processor = None
            self._failure_processor = None

            if workflow:
                self.workflow = workflow

            self._load_processors()

            try:
                self._nornir_configs = load_file_to_dict(self.settings.nornir_config_file)
            except Exception as e:
                raise CoreError(
                    f"Failed to load Nornir config from '{self.settings.nornir_config_file}': {e}",
                    component="NornFlow",
                ) from e

            self._nornir_manager = NornirManager(
                nornir_settings=self.settings.nornir_config_file,
                **self._nornir_configs,
            )
        except CoreError:
            raise
        except Exception as e:
            raise InitializationError(f"Failed to initialize NornFlow: {e!s}", component="NornFlow") from e

    def _load_processors(self) -> None:
        """
        Load processors from various sources by precedence:
        1. Processors passed through kwargs - Likely coming from CLI
        2. Settings file processors (settings.processors)
        3. Default processor (DefaultNornFlowProcessor)

        The loaded processors are stored in self._processors for later use during
        workflow execution.
        """
        processors_list = self.processors or self.settings.processors
        if processors_list:
            self._processors = []
            for processor_config in processors_list:
                try:
                    processor = load_processor(processor_config)
                    self._processors.append(processor)
                except ProcessorError as e:
                    raise InitializationError(f"Failed to load processor: {e}") from e
        else:
            self._processors = [DefaultNornFlowProcessor()]

    @property
    def nornir_configs(self) -> dict[str, Any]:
        """
        Get the Nornir configurations as a dict.

        Returns:
            dict[str, Any]: Dictionary containing the Nornir configurations.
        """
        return self.nornir_manager.nornir.config.dict()

    @nornir_configs.setter
    def nornir_configs(self, value: Any) -> None:
        raise NornirError(
            "Nornir configurations cannot be modified directly. Use NornFlowSettings to configure Nornir."
        )

    @property
    def nornir_manager(self) -> NornirManager:
        """
        Get the Nornir manager instance.

        Returns:
            NornirManager: The Nornir manager instance.
        """
        return self._nornir_manager

    @nornir_manager.setter
    def nornir_manager(self, value: Any) -> None:
        raise CoreError("Nornir manager cannot be set directly.")

    @property
    def settings(self) -> NornFlowSettings:
        """
        Get the NornFlow settings.

        Returns:
            NornFlowSettings: The NornFlow settings.
        """
        return self._settings

    @settings.setter
    def settings(self, value: Any) -> None:
        """
        Prevent setting the settings directly. Settings must be either passed as a
        NornFlowSettings object or as keyword arguments to the NornFlow initializer.

        Args:
            value (Any): Attempted value to set.

        Raises:
            SettingsError: Always raised to prevent direct setting of the settings.
        """
        raise SettingsError(
            "Cannot set settings directly. Settings must be either passed as a "
            "NornFlowSettings object or as keyword arguments to the NornFlow initializer."
        )

    @property
    def vars(self) -> dict[str, Any]:
        """
        Get the vars with highest precedence in the variable resolution chain.

        The primary source for this is the command-line arguments (--vars), although
        it might as well come from programmatic variable setting. In either case, these
        variables always have the highest precedence, overriding any other variable
        source including workflow variables, environment variables, and defaults.

        Returns:
            dict[str, Any]: Dictionary containing the vars.
        """
        return self._vars

    @vars.setter
    def vars(self, value: dict[str, Any]) -> None:
        """Update vars that override workflow-defined variables.

        Args:
            value: Dictionary of variable names and values.

        Raises:
            CoreError: If value is not a dictionary.
        """
        if not isinstance(value, dict):
            raise CoreError(
                f"Vars must be a dictionary, got {type(value).__name__}", component="NornFlow"
            )
        self._vars = value

    @property
    def filters(self) -> dict[str, Any]:
        """
        Get the inventory filters passed to the NornFlow constructor with highest precedence.

        These inventory filters completely override any filters defined in the workflow YAML.
        Like vars, they serve a dual purpose:
        1. Storage for inventory filters parsed from CLI arguments (--inventory-filters)
        2. Universal override mechanism for programmatic inventory filtering

        Returns:
            dict[str, Any]: Dictionary containing the inventory filters.
        """
        return self._filters

    @filters.setter
    def filters(self, value: dict[str, Any]) -> None:
        """Update inventory filters that override workflow-defined filters.

        Args:
            value: Dictionary of filter names and arguments.

        Raises:
            CoreError: If value is not a dictionary.
        """
        if not isinstance(value, dict):
            raise CoreError(
                f"Filters must be a dictionary, got {type(value).__name__}", component="NornFlow"
            )
        self._filters = value

    @property
    def failure_strategy(self) -> FailureStrategy:
        """
        Get the effective failure strategy based on precedence chain.

        Precedence (highest to lowest):
        1. Failure strategy passed to the NornFlow constructor
        2. Workflow failure strategy
        3. Settings failure strategy
        4. Default (SKIP_FAILED)

        Returns:
            FailureStrategy: The effective failure strategy.
        """
        return (
            self._failure_strategy
            or (self.workflow.failure_strategy if self.workflow else None)
            or self.settings.failure_strategy
            or FailureStrategy.SKIP_FAILED
        )

    @failure_strategy.setter
    def failure_strategy(self, value: FailureStrategy) -> None:
        """
        Set the failure strategy override.

        Args:
            value: FailureStrategy enum value.

        Raises:
            CoreError: If value is not a FailureStrategy.
        """
        if not isinstance(value, FailureStrategy):
            raise CoreError(
                f"Failure strategy must be a FailureStrategy enum, got {type(value).__name__}",
                component="NornFlow",
            )
        self._failure_strategy = value
        self._failure_processor = None

    @property
    def failure_processor(self) -> NornFlowFailureStrategyProcessor:
        """
        Get the failure processor, creating it lazily if needed.

        Returns:
            NornFlowFailureStrategyProcessor: The failure processor instance.
        """
        if self._failure_processor is None:
            self._failure_processor = NornFlowFailureStrategyProcessor(self.failure_strategy)
        return self._failure_processor

    @property
    def tasks_catalog(self) -> PythonEntityCatalog:
        """
        Get the tasks catalog.

        Returns:
            PythonEntityCatalog: Catalog containing task names and their corresponding functions.
        """
        return self._tasks_catalog

    @tasks_catalog.setter
    def tasks_catalog(self, _: Any) -> None:
        """
        Prevent setting the tasks catalog directly.

        Raises:
            CatalogError: Always raised to prevent direct setting of the tasks catalog.
        """
        raise CatalogError("Cannot set tasks catalog directly.", catalog_name="tasks")

    @property
    def workflows_catalog(self) -> FileCatalog:
        """
        Get the workflows catalog.

        Returns:
            FileCatalog: Catalog of workflows names and the corresponding file Path to it.
        """
        return self._workflows_catalog

    @workflows_catalog.setter
    def workflows_catalog(self, _: Any) -> None:
        """
        Prevent setting the workflows catalog directly.

        Raises:
            CatalogError: Always raised to prevent direct setting of the workflows catalog.
        """
        raise CatalogError("Cannot set workflows catalog directly.", catalog_name="workflows")

    @property
    def filters_catalog(self) -> PythonEntityCatalog:
        """
        Get the filters catalog.

        Returns:
            PythonEntityCatalog: Catalog of filter names and their corresponding functions.
        """
        return self._filters_catalog

    @filters_catalog.setter
    def filters_catalog(self, _: Any) -> None:
        """
        Prevent setting the filters catalog directly.

        Raises:
            CatalogError: Always raised to prevent direct setting of the filters catalog.
        """
        raise CatalogError("Cannot set filters catalog directly.", catalog_name="filters")

    @property
    def workflow(self) -> WorkflowModel | None:
        """
        Get the workflow model object.

        Returns:
            WorkflowModel | None: The workflow model object or None if not set.
        """
        return self._workflow

    @workflow.setter
    def workflow(self, value: WorkflowModel | str) -> None:
        """
        Set the workflow either from a WorkflowModel instance or by name.

        Args:
            value: Either a WorkflowModel instance or a string workflow name.
        
        Raises:
            WorkflowError: If value is invalid or workflow cannot be loaded.
        """
        if isinstance(value, WorkflowModel):
            self._workflow = value
        elif isinstance(value, str):
            if value not in self.workflows_catalog:
                raise WorkflowError(
                    f"Workflow '{value}' not found in workflows catalog. "
                    f"Available workflows: {', '.join(sorted(self.workflows_catalog.keys()))}",
                    component="NornFlow",
                )
            
            workflow_path = self.workflows_catalog[value]
            try:
                workflow_dict = load_file_to_dict(workflow_path)
                self._workflow = WorkflowModel.create(workflow_dict)
                self.workflow_path = workflow_path
            except Exception as e:
                raise WorkflowError(
                    f"Failed to load workflow '{value}' from path '{workflow_path}': {e}",
                    component="NornFlow",
                ) from e
        else:
            raise WorkflowError(
                f"Workflow must be a WorkflowModel instance or string name, got {type(value).__name__}",
                component="NornFlow",
            )
        
        self._failure_processor = None

    @property
    def processors(self) -> list:
        """
        Get the list of processor instances that will be applied to workflows.

        Returns:
            list: List of processor instances used during workflow execution.
        """
        return self._processors

    @processors.setter
    def processors(self, _: Any) -> None:
        """
        Prevent setting the processors directly.

        Raises:
            ProcessorError: Always raised to prevent direct setting of processors.
        """
        raise ProcessorError(
            message="Processors cannot be set directly, but must be loaded from nornflow settings file.",
            component="NornFlow",
        )

    def _load_tasks_catalog(self) -> None:
        """
        Load all Nornir tasks from built-ins and from directories specified in settings.

        Tasks are loaded in two phases:
        1. Built-in tasks from nornflow.builtins.tasks module
        2. User-defined tasks from local_tasks_dirs
        """
        self._tasks_catalog = PythonEntityCatalog(name="tasks")

        self.tasks_catalog.register_from_module(builtin_tasks, predicate=is_nornir_task)

        errors = []
        for task_dir in self.settings.local_tasks_dirs:
            task_path = Path(task_dir)
            if not task_path.exists():
                errors.append(f"Tasks directory does not exist: {task_dir}")
                continue

            try:
                self.tasks_catalog.discover_items_in_dir(task_dir, predicate=is_nornir_task)
            except Exception as e:
                raise ResourceError(
                    f"Error loading tasks from {task_dir}: {e!s}",
                    resource_type="tasks",
                    resource_name=task_dir,
                ) from e

        if errors:
            raise ResourceError(
                f"Configuration errors found: {'; '.join(errors)}",
                resource_type="tasks",
                resource_name="directories",
            )

        if self.tasks_catalog.is_empty:
            raise CatalogError("No tasks were found. The Tasks Catalog can't be empty.", catalog_name="tasks")

    def _load_filters_catalog(self) -> None:
        """
        Load inventory filters from built-ins and from directories specified in settings.

        Filters are loaded in two phases:
        1. Built-in filters from nornflow.builtins.filters module
        2. User-defined filters from configured local_filters_dirs
        """
        self._filters_catalog = PythonEntityCatalog(name="filters")

        self.filters_catalog.register_from_module(
            builtin_filters, predicate=is_nornir_filter, transform_item=process_filter
        )

        errors = []
        for filter_dir in self.settings.local_filters_dirs:
            filter_path = Path(filter_dir)
            if not filter_path.exists():
                errors.append(f"Filters directory does not exist: {filter_dir}")
                continue

            try:
                self.filters_catalog.discover_items_in_dir(
                    filter_dir, predicate=is_nornir_filter, transform_item=process_filter
                )
            except Exception as e:
                raise ResourceError(
                    f"Error loading filters from {filter_dir}: {e!s}",
                    resource_type="filters",
                    resource_name=filter_dir,
                ) from e

        if errors:
            raise ResourceError(
                f"Configuration errors found: {'; '.join(errors)}",
                resource_type="filters",
                resource_name="directories",
            )

    def _load_workflows_catalog(self) -> None:
        """
        Discover and load workflow files from directories specified in settings.

        This catalogs the available workflow files for later use when a workflow
        is requested by name.
        """
        self._workflows_catalog = FileCatalog(name="workflows")

        errors = []
        for workflow_dir in self.settings.local_workflows_dirs:
            workflow_path = Path(workflow_dir)
            if not workflow_path.exists():
                errors.append(f"Workflows directory does not exist: {workflow_dir}")
                continue

            try:
                self.workflows_catalog.discover_items_in_dir(
                    workflow_dir, predicate=is_workflow_file, recursive=True
                )
            except Exception as e:
                raise ResourceError(
                    f"Error loading workflows from {workflow_dir}: {e!s}",
                    resource_type="workflows",
                    resource_name=workflow_dir,
                ) from e

        if errors:
            raise ResourceError(
                f"Configuration errors found: {'; '.join(errors)}",
                resource_type="workflows",
                resource_name="directories",
            )

    def _check_invalid_kwargs(self, kwargs: dict[str, Any]) -> None:
        """
        Check if kwargs contains any keys in NORNFLOW_INVALID_INIT_KWARGS and raise an error if found.

        Args:
            kwargs (dict[str, Any]): The kwargs dictionary to check.

        Raises:
            InitializationError: If any invalid keys are found in kwargs.
        """
        invalid_keys = [key for key in kwargs if key in NORNFLOW_INVALID_INIT_KWARGS]
        if invalid_keys:
            raise InitializationError(
                f"Invalid kwarg(s) passed to NornFlow initializer: {', '.join(invalid_keys)}",
                component="NornFlow",
            )

    def _ensure_workflow(self) -> None:
        """
        Ensure a valid workflow is available before execution.

        Raises:
            WorkflowError: If no workflow is configured.
        """
        if not self.workflow:
            raise WorkflowError("No workflow configured. Set a workflow before calling run().", component="NornFlow")

    def _check_tasks(self) -> None:
        """
        Check if the tasks in the workflow are present in the tasks catalog.

        Raises:
            TaskError: If any tasks in the workflow are not found in the tasks catalog.
        """
        task_names = [task.name for task in self.workflow.tasks]

        missing_tasks = [task_name for task_name in task_names if task_name not in self.tasks_catalog]

        if missing_tasks:
            available_tasks = ", ".join(sorted(self.tasks_catalog.keys()))
            raise TaskError(
                f"Task(s) not found in tasks catalog: {', '.join(missing_tasks)}. "
                f"Available tasks: {available_tasks}"
            )

    def _get_filtering_kwargs(self) -> list[dict[str, Any]]:
        """
        Process and prepare inventory filters for application.
        
        Returns:
            List of filter kwargs dictionaries ready to apply.
        """
        filters_to_apply = self.filters or self.workflow.inventory_filters or {}
        
        if not filters_to_apply:
            return []

        filter_kwargs_list = []
        for key, filter_values in filters_to_apply.items():
            filter_kwargs = self._process_custom_filter(key, filter_values)
            if filter_kwargs:
                filter_kwargs_list.append(filter_kwargs)

        return filter_kwargs_list

    def _process_custom_filter(
        self, key: str, filter_values: Any
    ) -> dict[str, Any]:
        """
        Process a custom filter configuration.
        
        Args:
            key: The filter name.
            filter_values: The filter values.
            
        Returns:
            Dictionary of filter kwargs.
            
        Raises:
            WorkflowError: If the filter is not found or parameter count doesn't match.
        """
        if key not in self.filters_catalog:
            raise WorkflowError(f"Filter '{key}' not found in filters catalog")

        filter_func, param_names = self.filters_catalog[key]

        if isinstance(filter_values, dict):
            filter_kwargs = {"filter_func": filter_func}
            filter_kwargs.update(filter_values)
        elif isinstance(filter_values, list):
            if len(param_names) == 1:
                filter_kwargs = {"filter_func": filter_func, param_names[0]: filter_values}
            else:
                if len(filter_values) != len(param_names):
                    raise WorkflowError(
                        f"Filter '{key}' expects {len(param_names)} parameters, "
                        f"got {len(filter_values)}"
                    )
                filter_kwargs = {"filter_func": filter_func}
                for param_name, value in zip(param_names, filter_values):
                    filter_kwargs[param_name] = value
        else:
            if len(param_names) != 1:
                raise WorkflowError(f"Filter '{key}' expects {len(param_names)} parameters, got 1")
            filter_kwargs = {"filter_func": filter_func, param_names[0]: filter_values}

        return filter_kwargs

    def _apply_filters(self, nornir_manager: NornirManager) -> None:
        """
        Apply inventory filters to the Nornir manager.
        
        Args:
            nornir_manager: The Nornir manager to apply filters to.
        """
        filter_kwargs_list = self._get_filtering_kwargs()
        
        for filter_kwargs in filter_kwargs_list:
            nornir_manager.apply_filters(**filter_kwargs)

    def _init_variable_manager(self) -> NornFlowVariablesManager:
        """
        Initialize the variable manager with workflow context.
        
        Returns:
            The initialized NornFlowVariablesManager.
        """
        return NornFlowVariablesManager(
            vars_dir=self.settings.vars_dir,
            cli_vars=self.vars,
            inline_workflow_vars=dict(self.workflow.vars) if self.workflow.vars else {},
            workflow_path=self.workflow_path,
            workflow_roots=self.settings.local_workflows_dirs,
        )

    def _with_processors(
        self,
        nornir_manager: NornirManager,
        processors: list | None = None,
    ) -> None:
        """
        Apply processors to the Nornir instance based on configuration.

        IMPORTANT: Always adds NornFlowVariableProcessor as the first processor
        to ensure host context is available for variable resolution.
        Always adds NornFlowFailureStrategyProcessor as the second processor
        to handle error policies during task execution.

        This method handles the processor selection logic:
        1. Always add NornFlowVariableProcessor first (for variable resolution)
        2. Use workflow-specific processors from self._workflow.processors if defined
        3. Otherwise use the passed processors parameter
        4. If neither exists, use NornFlow's global processors (self._processors)
        5. Always add NornFlowFailureStrategyProcessor last (for failure strategy handling)

        Args:
            nornir_manager: The NornirManager instance to apply processors to
            processors: List of processors to apply if no workflow-specific processors defined
        """
        vars_manager = self._init_variable_manager()
        self._var_processor = NornFlowVariableProcessor(vars_manager)
        
        all_processors = [self._var_processor]
        
        if self.workflow and self.workflow.processors:
            try:
                workflow_processors = []
                for processor_config in self.workflow.processors:
                    processor = load_processor(dict(processor_config))
                    workflow_processors.append(processor)
                
                if workflow_processors:
                    all_processors.extend(workflow_processors)
            except ProcessorError as e:
                raise WorkflowError(f"Failed to initialize workflow processors: {e}") from e
        elif processors:
            all_processors.extend(processors)
        elif self.processors:
            all_processors.extend(self.processors)
        
        all_processors.append(self.failure_processor)
        
        nornir_manager.apply_processors(all_processors)

    def _orchestrate_execution(self, effective_dry_run: bool) -> None:
        """
        Orchestrate the execution of workflow tasks in sequence.

        This method handles the core workflow execution logic, including setting
        the dry-run mode and running each task with the necessary context.

        Args:
            effective_dry_run: Whether to execute in dry-run mode.
        """
        with self.nornir_manager:
            for task in self.workflow.tasks:
                self.nornir_manager.set_dry_run(effective_dry_run)
                
                task.run(
                    nornir_manager=self.nornir_manager,
                    vars_manager=self._var_processor.vars_manager,
                    tasks_catalog=dict(self.tasks_catalog),
                )

    def _print_workflow_overview(self, effective_dry_run: bool) -> None:
        """
        Print the workflow overview before execution.

        Args:
            effective_dry_run: Whether to execute in dry-run mode.
        """
        print_workflow_overview(
            workflow_model=self.workflow,
            effective_dry_run=effective_dry_run,
            hosts_count=len(self.nornir_manager.nornir.inventory.hosts),
            inventory_filters=self.filters or self.workflow.inventory_filters or {},
            workflow_vars=dict(self.workflow.vars) if self.workflow.vars else {},
            vars=self.vars,
            failure_strategy=self.failure_strategy,
        )

    def _print_workflow_summary(self) -> None:
        """
        Print the final workflow summary by invoking summary methods on processors.

        Iterates through all processors and calls print_final_workflow_summary
        on those that support it, allowing for post-execution reporting.
        """
        for processor in self.nornir_manager.nornir.processors:
            if hasattr(processor, "print_final_workflow_summary"):
                processor.print_final_workflow_summary()

    def _get_return_code(self) -> int:
        """
        Calculate the return code based on processor execution statistics and failed hosts.

        Iterates through processors to find execution stats (task_executions and failed_executions).
        If stats are available and failures occurred, returns the failure percentage (0-100).
        If no stats but failed hosts exist, returns 101. Otherwise, returns 0 for success.

        Returns:
            int: Exit code (0 for success, 1-100 for failure percentage, 101 for failures without stats).
        """
        for processor in self.nornir_manager.nornir.processors:
            try:
                task_executions = getattr(processor, "task_executions", 0)
                failed_executions = getattr(processor, "failed_executions", 0)

                if (
                    isinstance(task_executions, int)
                    and isinstance(failed_executions, int)
                    and task_executions
                    and failed_executions
                ):
                    failure_percentage = int((failed_executions / task_executions) * 100)
                    return failure_percentage

            except Exception:
                continue

        if self.nornir_manager.nornir.data.failed_hosts:
            return 101

        return 0

    def run(self, dry_run: bool = False) -> int:
        """
        Execute the configured workflow with the current NornFlow settings.
    
        This method orchestrates the complete workflow execution process:
        1. Ensures a workflow is configured and ready
        2. Validates that all tasks exist in the catalog
        3. Initializes the Nornir manager
        4. Applies inventory filters
        5. Sets up variable management
        6. Configures processors
        7. Executes tasks in sequence
        8. Calls print_final_workflow_summary on processors that support it
        9. Returns exit code based on execution results
    
        Exit Codes:
        - 0: Success (all tasks passed)
        - 1-100: Failure with percentage information (% of failed task executions, rounded down)
        - 101: Failure without percentage information (no processor provided statistics)
        - 102+: Reserved for exceptions/internal errors (this must be handled by the caller)
    
        Any exceptions that might happen in the encapsulated logic will just bubble-up
        back to the caller of NornFlow.run(). This is to allow the caller the flexibility
        to process and handle it as fits.
    
        Args:
            dry_run: Whether to execute in dry-run mode.
    
        Returns:
            int: Exit code representing execution status.
        """
        effective_dry_run = dry_run or self.workflow.dry_run
        self._ensure_workflow()
        self._check_tasks()
        self._apply_filters(self.nornir_manager)
        self._with_processors(self.nornir_manager)
        self._print_workflow_overview(effective_dry_run)
        self._orchestrate_execution(effective_dry_run)
        self._print_workflow_summary()
        return self._get_return_code()
