from pathlib import Path
from typing import Any

from pydantic_serdes.utils import load_file_to_dict

from nornflow.builtins import DefaultNornFlowProcessor, filters as builtin_filters, tasks as builtin_tasks
from nornflow.builtins.processors import NornFlowFailureStrategyProcessor, NornFlowHookProcessor
from nornflow.catalogs import CallableCatalog, FileCatalog
from nornflow.constants import FailureStrategy, NORNFLOW_INVALID_INIT_KWARGS
from nornflow.exceptions import (
    CatalogError,
    CoreError,
    ImmutableAttributeError,
    InitializationError,
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
    import_modules_recursively,
    is_nornir_filter,
    is_nornir_task,
    is_yaml_file,
    load_processor,
    print_workflow_overview,
    process_filter,
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
    1. Runtime Variables (dynamically set by the 'set' task or 'set_to' hook)
    2. CLI Variables (passed via --vars option or set programmatically)
    3. Inline Workflow Variables (defined in workflow YAML under vars: section)
    4. Domain-specific Default Variables (from vars_dir/<domain>/defaults.yaml)
    5. Default Variables (from vars_dir/defaults.yaml)
    6. Environment Variables (prefixed with NORNFLOW_VAR_)

    The 'host.' namespace provides read-only access to Nornir inventory data
    (e.g., {{ host.name }}, {{ host.platform }}).
    """

    def __init__(
        self,
        nornflow_settings: NornFlowSettings | None = None,
        workflow: WorkflowModel | str | None = None,
        processors: list[dict[str, Any]] | None = None,
        vars: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
        failure_strategy: FailureStrategy | None = None,
        dry_run: bool | None = None,
        **kwargs: Any,
    ):
        """
        Initialize a NornFlow instance.

        Args:
            nornflow_settings: NornFlow configuration settings object
            workflow: Pre-configured WorkflowModel instance or workflow name string (optional)
            processors: List of processor configurations to override default processors
            vars: Variables with highest precedence in the variable resolution chain.
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
            dry_run: Dry run mode with highest precedence. This overrides any dry_run
                setting defined in the workflow YAML or settings.
            **kwargs: Additional keyword arguments passed to NornFlowSettings

        Raises:
            InitializationError: If initialization fails due to invalid configuration
        """
        try:
            self._validate_init_kwargs(kwargs)
            self._initialize_settings(nornflow_settings, kwargs)
            self._initialize_instance_vars(vars, filters, failure_strategy, dry_run, processors)
            self._initialize_hooks()
            self._initialize_catalogs()
            self._initialize_processors()
            if workflow:
                self.workflow = workflow
        except CoreError:
            raise
        except Exception as e:
            raise InitializationError(f"Failed to initialize NornFlow: {e!s}", component="NornFlow") from e

    def _initialize_settings(
        self, nornflow_settings: NornFlowSettings | None, kwargs: dict[str, Any]
    ) -> None:
        """Initialize NornFlow settings from provided object or kwargs."""
        if nornflow_settings:
            self._settings = nornflow_settings
        else:
            try:
                self._settings = NornFlowSettings(**kwargs)
            except (SettingsError, ResourceError) as e:
                raise InitializationError(f"Failed to initialize NornFlow settings: {e}") from e

    def _initialize_instance_vars(
        self,
        vars: dict[str, Any] | None,
        filters: dict[str, Any] | None,
        failure_strategy: FailureStrategy | None,
        dry_run: bool | None,
        processors: list[dict[str, Any]] | None,
    ) -> None:
        """Initialize core instance variables."""
        self._vars = vars or {}
        self._filters = filters or {}
        self._failure_strategy = failure_strategy
        self._dry_run = dry_run
        self._processors = processors
        self._workflow = None
        self._workflow_path = None
        self._nornir_configs = None
        self._nornir_manager = None
        # System processors are initialized lazily in their property getters
        # when needed during workflow execution, not during __init__
        self._var_processor = None
        self._failure_strategy_processor = None
        self._hook_processor = None

    def _initialize_catalogs(self) -> None:
        """Initialize and load catalogs."""
        self._tasks_catalog = CallableCatalog("tasks")
        self._filters_catalog = CallableCatalog("filters")
        self._workflows_catalog = FileCatalog("workflows")
        self._blueprints_catalog = FileCatalog("blueprints")
        self._load_tasks_catalog()
        self._load_filters_catalog()
        self._load_workflows_catalog()
        self._load_blueprints_catalog()

    def _initialize_hooks(self) -> None:
        """Initialize hooks by importing modules from configured directories."""
        for dir_path in self.settings.local_hooks:
            dir_path_obj = Path(dir_path)
            if dir_path_obj.exists():
                import_modules_recursively(dir_path_obj)

    def _initialize_nornir(self) -> None:
        """Initialize Nornir configurations and manager."""
        if self._nornir_manager:
            return

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

    def _initialize_processors(self) -> None:
        """
        Load USER-CONFIGURABLE processors with proper precedence and store them in `self._processors`.

        This method ONLY handles processors that users can configure via:
        - CLI arguments (--processors)
        - Settings file (processors: section)
        - Default processor (if none specified)

        System processors (NornFlowVariableProcessor, NornFlowHookProcessor,
        NornFlowFailureStrategyProcessor) are NOT initialized here because:
        1. They require workflow context that may not be available during __init__
        2. They have fixed positions in the processor chain (first, second, last)
        3. They are always present and cannot be overridden by users

        System processors are added later in _apply_processors() when a workflow
        is being executed and all necessary context is available.

        Precedence for user-configurable processors:
        1. Processors passed through kwargs (likely from CLI)
        2. Processors from settings
        3. DefaultNornFlowProcessor
        """
        processors_list = self.processors or self.settings.processors
        if not processors_list:
            self._processors = [DefaultNornFlowProcessor()]
            return

        self._processors = []
        try:
            for processor_config in processors_list:
                processor = load_processor(processor_config)
                self._processors.append(processor)
        except ProcessorError as err:
            raise InitializationError(f"Failed to load processor: {err}") from err

    @property
    def nornir_configs(self) -> dict[str, Any]:
        """
        Get the Nornir configurations as a dict.

        Returns:
            dict[str, Any]: Dictionary containing the Nornir configurations.
        """
        if not self._nornir_manager:
            self._initialize_nornir()
        return self._nornir_configs

    @nornir_configs.setter
    def nornir_configs(self, value: Any) -> None:
        raise ImmutableAttributeError(
            "Nornir configurations cannot be modified directly. Use NornFlowSettings to configure Nornir."
        )

    @property
    def nornir_manager(self) -> NornirManager:
        """
        Get the Nornir manager instance.

        Returns:
            NornirManager: The Nornir manager instance.
        """
        if not self._nornir_manager:
            self._initialize_nornir()
        return self._nornir_manager

    @nornir_manager.setter
    def nornir_manager(self, value: Any) -> None:
        raise ImmutableAttributeError("Nornir manager cannot be set directly.")

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
            ImmutableAttributeError: Always raised to prevent direct setting of the settings.
        """
        raise ImmutableAttributeError(
            "Cannot set NornFlow settings directly. They must be either passed as a "
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
            raise CoreError(f"Vars must be a dictionary, got {type(value).__name__}", component="NornFlow")
        self._vars = value
        # Reset var processor since it depends on vars
        self._var_processor = None

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
            raise CoreError(f"Filters must be a dictionary, got {type(value).__name__}", component="NornFlow")
        self._filters = value

    @property
    def failure_strategy(self) -> FailureStrategy:
        """
        Get the effective failure strategy based on precedence chain.

        Precedence (highest to lowest):
        1. Failure strategy passed to the NornFlow constructor
        2. Workflow failure strategy
        3. Settings failure strategy

        Returns:
            FailureStrategy: The effective failure strategy.
        """
        if self._failure_strategy:
            return self._failure_strategy
        if self.workflow and self.workflow.failure_strategy:
            return self.workflow.failure_strategy
        return self.settings.failure_strategy

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
        self._failure_strategy_processor = None

    @property
    def dry_run(self) -> bool:
        """
        Get the effective dry_run value based on precedence chain.

        Precedence (highest to lowest):
        1. dry_run passed to NornFlow constructor
        2. Workflow dry_run setting
        3. Settings dry_run

        Returns:
            bool: The effective dry_run value.
        """
        if self._dry_run is not None:
            return self._dry_run
        if self.workflow and self.workflow.dry_run is not None:
            return self.workflow.dry_run
        return self.settings.dry_run

    @property
    def var_processor(self) -> NornFlowVariableProcessor | None:
        """
        Get the variable processor, creating it lazily if needed.

        This processor requires workflow context to initialize the variable manager.
        Returns None if no workflow is set, otherwise creates and caches the processor.

        Returns:
            NornFlowVariableProcessor | None: The variable processor instance or None if no workflow.
        """
        if not self._var_processor and self.workflow:
            vars_manager = self._create_variable_manager()
            self._var_processor = NornFlowVariableProcessor(vars_manager)
        return self._var_processor

    @property
    def failure_strategy_processor(self) -> NornFlowFailureStrategyProcessor:
        """
        Get the failure strategy processor, creating it lazily if needed.

        Returns:
            NornFlowFailureStrategyProcessor: The failure strategy processor instance.
        """
        if not self._failure_strategy_processor:
            self._failure_strategy_processor = NornFlowFailureStrategyProcessor(self.failure_strategy)
        return self._failure_strategy_processor

    @property
    def hook_processor(self) -> NornFlowHookProcessor:
        """
        Get the hook processor, creating it lazily with workflow context if needed.

        Returns:
            NornFlowHookProcessor: The hook processor instance.
        """
        if not self._hook_processor:
            workflow_context = {
                "vars_manager": self.var_processor.vars_manager if self.var_processor else None,
                "nornir_manager": self._nornir_manager,
                "tasks_catalog": self._tasks_catalog,
                "filters_catalog": self._filters_catalog,
                "workflows_catalog": self._workflows_catalog,
            }
            self._hook_processor = NornFlowHookProcessor(workflow_context=workflow_context)
        return self._hook_processor

    @property
    def tasks_catalog(self) -> CallableCatalog:
        """
        Get the tasks catalog.

        Returns:
            CallableCatalog: Catalog containing task names and their corresponding functions.
        """
        return self._tasks_catalog

    @tasks_catalog.setter
    def tasks_catalog(self, _: Any) -> None:
        """
        Prevent setting the tasks catalog directly.

        Raises:
            ImmutableAttributeError: Always raised to prevent direct setting of the tasks catalog.
        """
        raise ImmutableAttributeError("Cannot set tasks catalog directly.")

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
            ImmutableAttributeError: Always raised to prevent direct setting of the workflows catalog.
        """
        raise ImmutableAttributeError("Cannot set workflows catalog directly.")

    @property
    def filters_catalog(self) -> CallableCatalog:
        """
        Get the filters catalog.

        Returns:
            CallableCatalog: Catalog of filter names and their corresponding functions.
        """
        return self._filters_catalog

    @filters_catalog.setter
    def filters_catalog(self, _: Any) -> None:
        """
        Prevent setting the filters catalog directly.

        Raises:
            ImmutableAttributeError: Always raised to prevent direct setting of the filters catalog.
        """
        raise ImmutableAttributeError("Cannot set filters catalog directly.")

    @property
    def blueprints_catalog(self) -> FileCatalog:
        """
        Get the blueprints catalog.

        Returns:
            FileCatalog: Catalog of blueprint names and the corresponding file Path to it.
        """
        return self._blueprints_catalog

    @blueprints_catalog.setter
    def blueprints_catalog(self, _: Any) -> None:
        """
        Prevent setting the blueprints catalog directly.

        Raises:
            ImmutableAttributeError: Always raised to prevent direct setting of the blueprints catalog.
        """
        raise ImmutableAttributeError("Cannot set blueprints catalog directly.")

    @property
    def workflow(self) -> WorkflowModel | None:
        """
        Get the workflow model object.

        Returns:
            WorkflowModel | None: The workflow model object or None if not set.
        """
        return self._workflow

    @workflow.setter
    def workflow(self, value: WorkflowModel | str | None) -> None:
        """
        Set the workflow either from a WorkflowModel instance or by name.

        Args:
            value: Either a WorkflowModel instance, a string workflow name, or None to unset.

        Raises:
            WorkflowError: If value is invalid or workflow cannot be loaded.
        """
        if not value:
            self._workflow = None
            self._workflow_path = None
        elif isinstance(value, WorkflowModel):
            self._workflow = value
            self._workflow_path = None
        elif isinstance(value, str):
            self._workflow, self._workflow_path = self._load_workflow_from_name(value)
        else:
            raise WorkflowError(
                "Workflow must be a WorkflowModel instance, string name, or None, "
                f"got {type(value).__name__}",
                component="NornFlow",
            )

        # Reset system processors when workflow changes since they depend on workflow context
        self._var_processor = None
        self._failure_strategy_processor = None
        self._hook_processor = None

    @property
    def workflow_path(self) -> Path | None:
        """
        Get the path to the workflow file, if loaded from a file.

        Returns:
            Path | None: The workflow file path or None if not set.
        """
        return self._workflow_path

    @workflow_path.setter
    def workflow_path(self, value: Any) -> None:
        """
        Prevent setting the workflow path directly.

        Raises:
            ImmutableAttributeError: Always raised to prevent direct setting of the workflow path.
        """
        raise ImmutableAttributeError("Workflow path cannot be set directly.")

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
            ImmutableAttributeError: Always raised to prevent direct setting of processors.
        """
        raise ImmutableAttributeError(
            "Processors cannot be set directly, but must be loaded from nornflow settings file."
        )

    @property
    def nornir_config_file(self) -> str:
        """Get the Nornir config file path from settings."""
        return self.settings.nornir_config_file

    def _load_catalog(
        self,
        catalog_type: type,
        name: str,
        builtin_module: Any = None,
        predicate: Any = None,
        transform_item: Any = None,
        directories: list[str] | None = None,
        recursive: bool = False,
        check_empty: bool = False,
    ) -> Any:
        """
        Generic method to load a catalog with common logic for discovery and error handling.

        Args:
            catalog_type: The catalog class to instantiate (e.g., CallableCatalog, FileCatalog).
            name: Name of the catalog for error messages.
            builtin_module: Optional module to register builtins from (for CallableCatalog).
            predicate: Predicate function for filtering items during discovery.
            transform_item: Optional transform function for items (for CallableCatalog).
            directories: List of directories to scan for items.
            recursive: Whether to scan directories recursively (for FileCatalog).
            check_empty: Whether to raise an error if the catalog ends up empty.

        Returns:
            The loaded catalog instance.

        Raises:
            ResourceError: If directories don't exist or discovery fails.
            CatalogError: If check_empty is True and catalog is empty.
        """
        catalog = catalog_type(name)

        if builtin_module and predicate:
            catalog.register_from_module(builtin_module, predicate=predicate, transform_item=transform_item)

        errors = []
        for dir_path in directories or []:
            path = Path(dir_path)
            if not path.exists():
                errors.append(f"{name.capitalize()} directory does not exist: {dir_path}")
                continue

            try:
                if catalog_type == FileCatalog:
                    catalog.discover_items_in_dir(dir_path, predicate=predicate, recursive=recursive)
                else:
                    catalog.discover_items_in_dir(
                        dir_path, predicate=predicate, transform_item=transform_item
                    )
            except Exception as e:
                raise ResourceError(
                    f"Error loading {name} from {dir_path}: {e!s}",
                    resource_type=name,
                    resource_name=dir_path,
                ) from e

        if errors:
            raise ResourceError(
                f"Configuration errors found: {'; '.join(errors)}",
                resource_type=name,
                resource_name="directories",
            )

        if check_empty and catalog.is_empty:
            raise CatalogError(
                f"No {name} were found. The {name.capitalize()} Catalog can't be empty.", catalog_name=name
            )

        return catalog

    def _load_tasks_catalog(self) -> None:
        """
        Load all Nornir tasks from built-ins and from directories specified in settings.

        Tasks are loaded in two phases:
        1. Built-in tasks from nornflow.builtins.tasks module
        2. User-defined tasks from local_tasks
        """
        self._tasks_catalog = self._load_catalog(
            CallableCatalog,
            "tasks",
            builtin_module=builtin_tasks,
            predicate=is_nornir_task,
            directories=self.settings.local_tasks,
            check_empty=True,
        )

    def _load_filters_catalog(self) -> None:
        """
        Load inventory filters from built-ins and from directories specified in settings.

        Filters are loaded in two phases:
        1. Built-in filters from nornflow.builtins.filters module
        2. User-defined filters from configured local_filters
        """
        self._filters_catalog = self._load_catalog(
            CallableCatalog,
            "filters",
            builtin_module=builtin_filters,
            predicate=is_nornir_filter,
            transform_item=process_filter,
            directories=self.settings.local_filters,
        )

    def _load_workflows_catalog(self) -> None:
        """
        Discover and load workflow files from directories specified in settings.

        This catalogs the available workflow files for later use when a workflow
        is requested by name.
        """
        self._workflows_catalog = self._load_catalog(
            FileCatalog,
            "workflows",
            predicate=is_yaml_file,
            directories=self.settings.local_workflows,
            recursive=True,
        )

    def _load_blueprints_catalog(self) -> None:
        """
        Discover and load blueprint files from directories specified in settings.

        This catalogs the available blueprint files for later use.
        """
        self._blueprints_catalog = self._load_catalog(
            FileCatalog,
            "blueprints",
            predicate=is_yaml_file,
            directories=self.settings.local_blueprints,
            recursive=True,
        )

    def _validate_init_kwargs(self, kwargs: dict[str, Any]) -> None:
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

    def _apply_filters(self) -> None:
        """Apply inventory filters to the Nornir manager."""
        filter_kwargs_list = self._get_filtering_kwargs()

        for filter_kwargs in filter_kwargs_list:
            self.nornir_manager.apply_filters(**filter_kwargs)

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

    def _process_custom_filter(self, key: str, filter_values: Any) -> dict[str, Any]:
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
            return self._build_filter_kwargs_for_dict(filter_func, filter_values)
        if isinstance(filter_values, list):
            return self._build_filter_kwargs_for_list(filter_func, param_names, filter_values)
        return self._build_filter_kwargs_for_single(filter_func, param_names, filter_values)

    def _build_filter_kwargs_for_dict(
        self, filter_func: Any, filter_values: dict[str, Any]
    ) -> dict[str, Any]:
        """Build filter kwargs when filter_values is a dict."""
        filter_kwargs = {"filter_func": filter_func}
        filter_kwargs.update(filter_values)
        return filter_kwargs

    def _build_filter_kwargs_for_list(
        self, filter_func: Any, param_names: list[str], filter_values: list
    ) -> dict[str, Any]:
        """Build filter kwargs when filter_values is a list."""
        if len(param_names) == 1:
            return {"filter_func": filter_func, param_names[0]: filter_values}
        if len(filter_values) != len(param_names):
            raise WorkflowError(f"Filter expects {len(param_names)} parameters, got {len(filter_values)}")

        filter_kwargs: dict[str, Any] = dict(zip(param_names, filter_values, strict=False))
        filter_kwargs["filter_func"] = filter_func
        return filter_kwargs

    def _build_filter_kwargs_for_single(
        self, filter_func: Any, param_names: list[str], filter_values: Any
    ) -> dict[str, Any]:
        """Build filter kwargs when filter_values is a single value."""
        if len(param_names) != 1:
            raise WorkflowError(f"Filter expects {len(param_names)} parameters, got 1")
        return {"filter_func": filter_func, param_names[0]: filter_values}

    def _load_workflow_from_name(self, name: str) -> tuple[WorkflowModel, Path]:
        """
        Load a workflow from a string name by checking the catalog and parsing the file.

        Args:
            name: The workflow name to load.

        Returns:
            A tuple of the loaded WorkflowModel and its file path.

        Raises:
            WorkflowError: If the workflow is not found or loading fails.
        """
        if name not in self.workflows_catalog:
            raise WorkflowError(
                f"Workflow '{name}' not found in workflows catalog. "
                f"Available workflows: {', '.join(sorted(self.workflows_catalog.keys()))}",
                component="NornFlow",
            )

        workflow_path = self.workflows_catalog[name]
        try:
            workflow_dict = load_file_to_dict(workflow_path)
            workflow = WorkflowModel.create(
                workflow_dict,
                blueprints_catalog=dict(self.blueprints_catalog),
                vars_dir=self.settings.vars_dir,
                workflow_path=workflow_path,
                workflow_roots=self.settings.local_workflows,
                cli_vars=self._vars,
            )
            return workflow, workflow_path
        except Exception as e:
            raise WorkflowError(
                f"Failed to load workflow '{name}' from path '{workflow_path}': {e}",
                component="NornFlow",
            ) from e

    def _create_variable_manager(self) -> NornFlowVariablesManager:
        """
        Create a new variable manager instance with workflow context.

        Returns:
            The created NornFlowVariablesManager instance.
        """
        return NornFlowVariablesManager(
            vars_dir=self.settings.vars_dir,
            cli_vars=self.vars,
            inline_workflow_vars=dict(self.workflow.vars) if self.workflow.vars else {},
            workflow_path=self.workflow_path,
            workflow_roots=self.settings.local_workflows,
        )

    def _apply_processors(self) -> None:
        """
        Apply processors to the Nornir instance based on configuration.

        This method handles TWO distinct types of processors:

        1. SYSTEM PROCESSORS (always present, fixed positions):
           - NornFlowVariableProcessor: ALWAYS first (provides variable resolution)
           - NornFlowHookProcessor: ALWAYS second (handles hook execution)
           - NornFlowFailureStrategyProcessor: ALWAYS last (handles error policies)

        2. USER-CONFIGURABLE PROCESSORS (optional, middle position):
           - From workflow definition (self._workflow.processors)
           - From NornFlow settings (self._processors initialized in _initialize_processors)

        System processors are initialized lazily via their properties when first accessed.
        The var_processor is special as it requires workflow context to be available.

        Processor chain order:
        1. NornFlowVariableProcessor (system - variable resolution)
        2. NornFlowHookProcessor (system - hook execution)
        3. User-configurable processors (custom business logic)
        4. NornFlowFailureStrategyProcessor (system - error handling)
        """
        # Build processor chain with system processors at fixed positions
        # The var_processor property will handle lazy initialization if needed
        all_processors = [
            self.var_processor,
            self.hook_processor,
        ]

        # Add user-configurable processors in the middle
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
        elif self.processors:
            all_processors.extend(self.processors)

        all_processors.append(self.failure_strategy_processor)

        self.nornir_manager.apply_processors(all_processors)

    def _orchestrate_execution(self) -> None:
        """Orchestrate the execution of workflow tasks in sequence."""
        with self.nornir_manager:
            for task in self.workflow.tasks:
                self.nornir_manager.set_dry_run(self.dry_run)

                task.run(
                    nornir_manager=self.nornir_manager,
                    vars_manager=self.var_processor.vars_manager,
                    tasks_catalog=dict(self.tasks_catalog),
                )

    def _print_workflow_overview(self) -> None:
        """Print the workflow overview before execution."""
        print_workflow_overview(
            workflow_model=self.workflow,
            effective_dry_run=self.dry_run,
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

        Iterates through processors to find execution stats (failed_executions and task_executions).
        This is a FEATURE - the first processor with these attributes provides the stats.
        Uses the EXACT same calculation as the summary: failed_executions / task_executions * 100.

        If stats are available and failures occurred, returns the failure percentage (0-100).
        If no stats but failed hosts exist, returns 101. Otherwise, returns 0 for success.

        Returns:
            int: Exit code (0 for success, 1-100 for failure percentage, 101 for failures without stats).
        """
        for processor in self.nornir_manager.nornir.processors:
            failed_executions = getattr(processor, "failed_executions", 0)
            task_executions = getattr(processor, "task_executions", 0)

            if not task_executions:
                continue

            # Use EXACT same calculation as summary: failed_executions / task_executions * 100
            failure_percentage = int((failed_executions / task_executions) * 100)
            return failure_percentage

        if self.nornir_manager.nornir.data.failed_hosts:
            return 101

        return 0

    def run(self) -> int:
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

        Returns:
            int: Exit code representing execution status.
        """
        if not self.workflow:
            raise WorkflowError(
                "No workflow configured. Set a workflow before calling run().", component="NornFlow"
            )

        self._check_tasks()
        self._initialize_nornir()
        self._apply_filters()
        self._apply_processors()
        self._print_workflow_overview()
        self._orchestrate_execution()
        self._print_workflow_summary()
        return self._get_return_code()
