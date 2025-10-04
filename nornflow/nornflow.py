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
    1. CLI variables (passed via command line or set programmatically as overrides)
    2. Workflow variables (defined in workflow file)
    3. Environment variables
    4. Variables from external files
    """

    def __init__(
        self,
        nornflow_settings: NornFlowSettings | None = None,
        workflow: WorkflowModel | str | None = None,
        processors: list[dict[str, Any]] | None = None,
        cli_vars: dict[str, Any] | None = None,
        cli_filters: dict[str, Any] | None = None,
        cli_failure_strategy: FailureStrategy | None = None,
        **kwargs: Any,
    ):
        """
        Initialize a NornFlow instance.

        Args:
            nornflow_settings: NornFlow configuration settings object
            workflow: Pre-configured WorkflowModel instance or workflow name string (optional)
            processors: List of processor configurations to override default processors
            cli_vars: Variables with highest precedence in the resolution chain.
                While named "CLI variables" due to their primary source being command-line
                arguments, these serve as a universal override mechanism that can be:
                - Parsed from actual CLI arguments (--vars)
                - Set programmatically for workflow customization
                - Updated at runtime for dynamic behavior
                These variables always override any other variable source.
            cli_filters: Inventory filters with highest precedence. These completely override
                any inventory filters defined in the workflow YAML.
            cli_failure_strategy: Failure strategy with highest precedence. This overrides any failure
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

            self._cli_vars = cli_vars or {}
            self._cli_filters = cli_filters or {}
            self._cli_failure_strategy = cli_failure_strategy
            self._kwargs_processors = processors

            self._tasks_catalog = PythonEntityCatalog("tasks")
            self._filters_catalog = PythonEntityCatalog("filters")
            self._workflows_catalog = FileCatalog("workflows")

            self._load_tasks_catalog()
            self._load_filters_catalog()
            self._load_workflows_catalog()

            self._workflow = None
            self.workflow_path = None
            self._var_processor = None
            self._failure_processor_instance = None

            if workflow:
                self.workflow = workflow

            self._load_processors()

            try:
                self._nornir_configs = load_file_to_dict(self._settings.nornir_config_file)
            except Exception as e:
                raise CoreError(
                    f"Failed to load Nornir config from '{self._settings.nornir_config_file}': {e}",
                    component="NornFlow",
                ) from e

            self.nornir_manager = NornirManager(
                nornir_settings=self.settings.nornir_config_file,
                **kwargs,
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
        processors_list = self._kwargs_processors or self.settings.processors
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
        """Update CLI variables that override workflow-defined variables.

        Args:
            value: Dictionary of variable names and values.

        Raises:
            CoreError: If value is not a dictionary.
        """
        if not isinstance(value, dict):
            raise CoreError(
                f"CLI variables must be a dictionary, got {type(value).__name__}", component="NornFlow"
            )
        self._cli_vars = value

    @property
    def cli_filters(self) -> dict[str, Any]:
        """
        Get the CLI inventory filters with highest precedence.

        These inventory filters completely override any filters defined in the workflow YAML.
        Like CLI variables, they serve a dual purpose:
        1. Storage for inventory filters parsed from CLI arguments (--inventory-filters)
        2. Universal override mechanism for programmatic inventory filtering

        Returns:
            dict[str, Any]: Dictionary containing the CLI inventory filters.
        """
        return self._cli_filters

    @cli_filters.setter
    def cli_filters(self, value: dict[str, Any]) -> None:
        """Update CLI inventory filters that override workflow-defined filters.

        Args:
            value: Dictionary of filter names and arguments.

        Raises:
            CoreError: If value is not a dictionary.
        """
        if not isinstance(value, dict):
            raise CoreError(
                f"CLI filters must be a dictionary, got {type(value).__name__}", component="NornFlow"
            )
        self._cli_filters = value

    @property
    def failure_strategy(self) -> FailureStrategy:
        """
        Get the effective failure strategy based on precedence chain.

        Precedence (highest to lowest):
        1. CLI failure strategy
        2. Workflow failure strategy
        3. Settings failure strategy
        4. Default (SKIP_FAILED)

        Returns:
            FailureStrategy: The effective failure strategy.
        """
        return (
            self._cli_failure_strategy
            or (self._workflow.failure_strategy if self._workflow else None)
            or self._settings.failure_strategy
            or FailureStrategy.SKIP_FAILED
        )

    @failure_strategy.setter
    def failure_strategy(self, value: FailureStrategy) -> None:
        """
        Set the CLI failure strategy override.

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
        self._cli_failure_strategy = value
        self._failure_processor_instance = None

    @property
    def failure_processor(self) -> NornFlowFailureStrategyProcessor:
        """
        Get the failure processor, creating it lazily if needed.

        Returns:
            NornFlowFailureStrategyProcessor: The failure processor instance.
        """
        if self._failure_processor_instance is None:
            self._failure_processor_instance = NornFlowFailureStrategyProcessor(self.failure_strategy)
        return self._failure_processor_instance

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
            if value not in self._workflows_catalog:
                raise WorkflowError(
                    f"Workflow '{value}' not found in workflows catalog. "
                    f"Available workflows: {', '.join(sorted(self._workflows_catalog.keys()))}",
                    component="NornFlow",
                )
            
            workflow_path = self._workflows_catalog[value]
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
        
        self._failure_processor_instance = None

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

        self._tasks_catalog.register_from_module(builtin_tasks, predicate=is_nornir_task)

        errors = []
        for task_dir in self.settings.local_tasks_dirs:
            task_path = Path(task_dir)
            if not task_path.exists():
                errors.append(f"Tasks directory does not exist: {task_dir}")
                continue

            try:
                self._tasks_catalog.discover_items_in_dir(task_dir, predicate=is_nornir_task)
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

        if self._tasks_catalog.is_empty:
            raise CatalogError("No tasks were found. The Tasks Catalog can't be empty.", catalog_name="tasks")

    def _load_filters_catalog(self) -> None:
        """
        Load inventory filters from built-ins and from directories specified in settings.

        Filters are loaded in two phases:
        1. Built-in filters from nornflow.builtins.filters module
        2. User-defined filters from configured local_filters_dirs
        """
        self._filters_catalog = PythonEntityCatalog(name="filters")

        self._filters_catalog.register_from_module(
            builtin_filters, predicate=is_nornir_filter, transform_item=process_filter
        )

        errors = []
        for filter_dir in self.settings.local_filters_dirs:
            filter_path = Path(filter_dir)
            if not filter_path.exists():
                errors.append(f"Filters directory does not exist: {filter_dir}")
                continue

            try:
                self._filters_catalog.discover_items_in_dir(
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
                self._workflows_catalog.discover_items_in_dir(
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
        if not self._workflow:
            raise WorkflowError("No workflow configured. Set a workflow before calling run().", component="NornFlow")

    def _check_tasks(self) -> None:
        """
        Check if the tasks in the workflow are present in the tasks catalog.

        Raises:
            TaskError: If any tasks in the workflow are not found in the tasks catalog.
        """
        task_names = [task.name for task in self._workflow.tasks]

        missing_tasks = [task_name for task_name in task_names if task_name not in self._tasks_catalog]

        if missing_tasks:
            available_tasks = ", ".join(sorted(self._tasks_catalog.keys()))
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
        filters_to_apply = self._cli_filters or self._workflow.inventory_filters or {}
        
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
        if key not in self._filters_catalog:
            raise WorkflowError(f"Filter '{key}' not found in filters catalog")

        filter_func, param_names = self._filters_catalog[key]

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
            vars_dir=self._settings.vars_dir,
            cli_vars=self._cli_vars,
            inline_workflow_vars=dict(self._workflow.vars) if self._workflow.vars else {},
            workflow_path=self.workflow_path,
            workflow_roots=self._settings.local_workflows_dirs,
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
        
        if self._workflow and self._workflow.processors:
            try:
                workflow_processors = []
                for processor_config in self._workflow.processors:
                    processor = load_processor(dict(processor_config))
                    workflow_processors.append(processor)
                
                if workflow_processors:
                    all_processors.extend(workflow_processors)
            except ProcessorError as e:
                raise WorkflowError(f"Failed to initialize workflow processors: {e}") from e
        elif processors:
            all_processors.extend(processors)
        elif self._processors:
            all_processors.extend(self._processors)
        
        all_processors.append(self.failure_processor)
        
        nornir_manager.apply_processors(all_processors)

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
        self._ensure_workflow()
        self._check_tasks()
        
        nornir_manager = NornirManager(self.settings.nornir_config_file, **self._nornir_configs)
        
        self._apply_filters(nornir_manager)
        self._with_processors(nornir_manager)
    
        effective_dry_run = dry_run or self._workflow.dry_run
        
        print_workflow_overview(
            workflow_model=self._workflow,
            effective_dry_run=effective_dry_run,
            hosts_count=len(nornir_manager.nornir.inventory.hosts),
            inventory_filters=self._cli_filters or self._workflow.inventory_filters or {},
            workflow_vars=dict(self._workflow.vars) if self._workflow.vars else {},
            cli_vars=self._cli_vars,
            failure_strategy=self.failure_strategy,
        )
    
        for processor in nornir_manager.nornir.processors:
            if hasattr(processor, "total_workflow_tasks"):
                processor.total_workflow_tasks = len(self._workflow.tasks)
    
        with nornir_manager:
            for task in self._workflow.tasks:
                nornir_manager.set_dry_run(effective_dry_run)
                
                task.run(
                    nornir_manager=nornir_manager,
                    vars_manager=self._var_processor.vars_manager,
                    tasks_catalog=dict(self._tasks_catalog),
                )
    
        for processor in nornir_manager.nornir.processors:
            if hasattr(processor, "print_final_workflow_summary"):
                processor.print_final_workflow_summary()
    
        for processor in nornir_manager.nornir.processors:
            try:
                task_executions = getattr(processor, "task_executions", 0)
                failed_executions = getattr(processor, "failed_executions", 0)

                # some tasks failed and we want the return code to report 
                # the % of failed tasks
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
        
        # if we got here, none of the applied processors support executions stats
        if nornir_manager.nornir.data.failed_hosts:
            return 101
        
        # success: all tasks ran without any failured for any hosts
        return 0


class NornFlowBuilder:
    """
    Builder class for constructing NornFlow objects with a fluent interface.

    The builder provides a structured way to configure all aspects of a NornFlow instance:
    - Settings configuration (via object or file path)
    - Workflow configuration (via WorkflowModel object, file path, or dictionary)
    - Processor registration
    - CLI variables (with highest precedence in variable resolution)
    - CLI inventory filters (with highest precedence for inventory filtering)
    - Additional keyword arguments

    CLI Variables in Builder Context:
    The builder's `with_cli_vars()` method sets variables that will have the highest
    precedence in the variable resolution system. While termed "CLI variables" due to
    their primary use case (command-line arguments), these serve as a universal
    override mechanism in the builder pattern.

    CLI Inventory Filters in Builder Context:
    The builder's `with_cli_filters()` method sets inventory filters that will completely
    override any inventory filters defined in the workflow YAML.

    Usage Examples:
        # Basic usage
        builder = NornFlowBuilder()
        nornflow = builder.with_settings_path('settings.yaml')
                          .with_workflow_path('deploy.yaml')
                          .with_cli_vars({'env': 'prod', 'debug': True})
                          .with_cli_filters({'hosts': ['router1', 'router2']})
                          .build()

    Order of preference for building a NornFlowSettings object:
      1. with_settings_object()
      2. with_settings_path()

    Order of preference for building a WorkflowModel object:
      1. with_workflow_model()
      2. with_workflow_path()
      3. with_workflow_dict()
      4. with_workflow_name() (resolved during execution)
    """

    def __init__(self):
        """
        Initialize the NornFlowBuilder with default values.
        """
        self._settings: NornFlowSettings | None = None
        self._workflow: WorkflowModel | str | None = None
        self._processors: list[dict[str, Any]] | None = None
        self._cli_vars: dict[str, Any] | None = None
        self._cli_filters: dict[str, Any] | None = None
        self._cli_failure_strategy: FailureStrategy | None = None
        self._kwargs: dict[str, Any] = {}

    def with_settings_object(self, settings_object: NornFlowSettings) -> "NornFlowBuilder":
        """
        Set the NornFlowSettings object for the builder.

        Args:
            settings_object: The NornFlowSettings object.

        Returns:
            The builder instance for method chaining.
        """
        self._settings = settings_object
        return self

    def with_settings_path(self, settings_path: str | Path) -> "NornFlowBuilder":
        """
        Creates a NornFlowSettings for the builder, based on a file path.
        This only takes effect if the settings object has not been set yet.
        Initializing NornFlow with a fully formed NornFlowSettings object is preferred.

        Args:
            settings_path: The path to a YAML file to be used by NornFlowSettings object.

        Returns:
            The builder instance for method chaining.
        """
        if not self._settings:
            try:
                settings_object = NornFlowSettings(settings_file=settings_path)
                self._settings = settings_object
            except (SettingsError, ResourceError) as e:
                raise InitializationError(f"Failed to load settings from '{settings_path}': {e}") from e
        return self

    def with_workflow_path(self, workflow_path: str | Path) -> "NornFlowBuilder":
        """
        Set the workflow path for the builder.

        Args:
            workflow_path: Path to the workflow file.

        Returns:
            The builder instance for method chaining.
        """
        try:
            workflow_dict = load_file_to_dict(workflow_path)
            self._workflow = WorkflowModel.create(workflow_dict)
        except Exception as e:
            raise InitializationError(f"Failed to load workflow from '{workflow_path}': {e}") from e
        return self

    def with_workflow_dict(self, workflow_dict: dict[str, Any]) -> "NornFlowBuilder":
        """
        Set the workflow dictionary for the builder.

        Args:
            workflow_dict: Dictionary representing the workflow.

        Returns:
            The builder instance for method chaining.
        """
        try:
            self._workflow = WorkflowModel.create(workflow_dict)
        except Exception as e:
            raise InitializationError(f"Failed to create workflow from dict: {e}") from e
        return self

    def with_workflow_model(self, workflow_model: WorkflowModel) -> "NornFlowBuilder":
        """
        Set the workflow model for the builder.

        Args:
            workflow_model: A fully formed WorkflowModel object.

        Returns:
            The builder instance for method chaining.
        """
        self._workflow = workflow_model
        return self

    def with_workflow_name(self, workflow_name: str) -> "NornFlowBuilder":
        """
        Set the workflow name for the builder.
        
        The workflow will be resolved from the workflows catalog during NornFlow execution.
        This allows using workflow names instead of paths, which is particularly useful
        for CLI commands like `nornflow run some_workflow_name`.

        Args:
            workflow_name: The name of the workflow to set.

        Returns:
            The builder instance for method chaining.
        """
        self._workflow = workflow_name
        return self

    def with_processors(self, processors: list[dict[str, Any]]) -> "NornFlowBuilder":
        """
        Set the processor configurations for the builder.

        Args:
            processors: List of processor configurations.
                Each must be a dict with 'class' and optional 'args' keys.

        Returns:
            The builder instance for method chaining.
        """
        self._processors = processors
        return self

    def with_cli_vars(self, cli_vars: dict[str, Any]) -> "NornFlowBuilder":
        """
        Set CLI variables for the NornFlow instance.

        These variables have the highest precedence in the variable resolution order
        and serve a dual purpose:
        1. Primary: Storage for variables parsed from CLI arguments (--vars)
        2. Secondary: Universal override mechanism for programmatic variable setting

        They override any variables from other sources including workflow variables,
        domain defaults, and environment variables. The variables are passed to
        workflows during execution with support for late binding.

        Usage Examples:
            # Traditional CLI argument representation
            builder.with_cli_vars({'env': 'prod', 'debug': True})

            # Programmatic override usage
            emergency_vars = {'skip_validation': True, 'fast_mode': True}
            builder.with_cli_vars(emergency_vars)

        Args:
            cli_vars: Dictionary of variables with highest precedence

        Returns:
            The builder instance for method chaining.
        """
        self._cli_vars = cli_vars
        return self

    def with_cli_filters(self, cli_filters: dict[str, Any]) -> "NornFlowBuilder":
        """
        Set CLI inventory filters for the NornFlow instance.

        These filters have the highest precedence and completely override
        any inventory filters defined in the workflow YAML.

        Args:
            cli_filters: Dictionary of inventory filters with highest precedence

        Returns:
            The builder instance for method chaining.
        """
        self._cli_filters = cli_filters
        return self

    def with_cli_failure_strategy(self, cli_failure_strategy: FailureStrategy) -> "NornFlowBuilder":
        """
        Set CLI failure strategy for the NornFlow instance.

        This strategy has the highest precedence and overrides any failure strategy
        defined in the workflow YAML.

        Args:
            cli_failure_strategy: FailureStrategy enum value with highest precedence

        Returns:
            The builder instance for method chaining.
        """
        self._cli_failure_strategy = cli_failure_strategy
        return self

    def with_kwargs(self, **kwargs: Any) -> "NornFlowBuilder":
        """
        Set additional keyword arguments for the builder.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            The builder instance for method chaining.
        """
        self._kwargs.update(kwargs)
        return self

    def build(self) -> NornFlow:
        """
        Build and return a NornFlow object based on the provided configurations.

        The built NornFlow instance will include all configured components:
        - Settings (from object or file path)
        - Workflow model (from model, path, dictionary, or name)
        - Processors (if specified)
        - CLI variables (with highest precedence in variable resolution)
        - CLI inventory filters (with highest precedence for inventory filtering)

        Returns:
            The constructed NornFlow object with all configurations applied.
        """
        return NornFlow(
            nornflow_settings=self._settings,
            workflow=self._workflow,
            processors=self._processors,
            cli_vars=self._cli_vars,
            cli_filters=self._cli_filters,
            cli_failure_strategy=self._cli_failure_strategy,
            **self._kwargs,
        )