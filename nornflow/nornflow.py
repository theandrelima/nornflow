from pathlib import Path
from typing import Any

from nornflow.builtins import DefaultNornFlowProcessor, filters as builtin_filters, tasks as builtin_tasks
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
    WorkflowError,
)
from nornflow.nornir_manager import NornirManager
from nornflow.settings import NornFlowSettings
from nornflow.utils import (
    is_nornir_filter,
    is_nornir_task,
    is_workflow_file,
    load_processor,
    process_filter,
)
from nornflow.workflow import Workflow, WorkflowFactory


class NornFlow:
    """
    NornFlow extends Nornir with a structured workflow system, task discovery, and configuration
    management capabilities. It serves as the main entry point for executing network automation
    jobs that follow a defined workflow pattern.

    Key features:
    - Automated assets discovery from local directories
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

    CLI Variables - Dual Nature:
    CLI variables in NornFlow serve a dual purpose:
    1. Traditional CLI usage: Variables parsed from command-line arguments (--vars)
    2. Override mechanism: Programmatically set variables with highest precedence

    This dual nature allows CLI variables to be:
    - Set during NornFlow initialization for workflow creation
    - Updated at runtime during workflow execution for maximum flexibility
    - Used as a universal override mechanism in programmatic scenarios

    The term "CLI variables" reflects their highest precedence nature and primary
    source (command-line interface), while also serving as a flexible override
    mechanism for any high-priority variable needs.
    """

    def __init__(
        self,
        nornflow_settings: NornFlowSettings | None = None,
        workflow: Workflow | None = None,
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
            workflow: Pre-configured workflow object (optional)
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
            NornFlowInitializationError: If initialization fails due to invalid configuration
        """
        try:
            # Store processors from explicit parameter
            self._kwargs_processors = processors

            # Store CLI variables - these have highest precedence in variable resolution
            # and serve as both CLI-sourced variables and programmatic overrides
            self._cli_vars = cli_vars or {}

            # Store CLI inventory filters - these override workflow inventory filters
            self._cli_filters = cli_filters or {}

            # Store CLI failure strategy - this overrides workflow failure strategy
            self._cli_failure_strategy = cli_failure_strategy

            # Some kwargs should only be set through the YAML settings file.
            self._check_invalid_kwargs(kwargs)

            # a NornFlow object must have a NornFlowSettings object
            self._settings = nornflow_settings or NornFlowSettings(**kwargs)

            # a NornFlow object can exist without a Workflow object BEFORE the run() method is called
            self._workflow = workflow

            self._load_tasks_catalog()
            self._load_workflows_catalog()
            self._load_filters_catalog()
            self._load_processors()

            # Create NornirManager instead of directly initializing Nornir
            self.nornir_manager = NornirManager(
                nornir_settings=self.settings.nornir_config_file,
                **kwargs,
            )
        except CoreError:
            raise
        except Exception as e:
            # Wrap any other exception in InitializationError
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
        # Check if processors were wither passed directly, or set in NornFlow's settings
        processors_list = self._kwargs_processors or self.settings.processors
        if processors_list:
            self._processors = []
            for processor_config in processors_list:
                processor = load_processor(processor_config)
                self._processors.append(processor)

        # If no processors are specified anywhere, use default
        else:
            self._processors = [DefaultNornFlowProcessor()]

    @property
    def nornir_configs(self) -> dict[str, Any]:
        """
        Get the Nornir configurations as a dict.

        Returns:
            dict[str, Any]: Dictionary containing the Nornir configurations.
        """
        # Access nornir through nornir_manager
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
            SettingsModificationError: Always raised to prevent direct setting of the settings.
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
    def cli_failure_strategy(self) -> FailureStrategy | None:
        """
        Get the CLI failure strategy with highest precedence.

        This failure strategy overrides any failure strategy defined in the workflow YAML.

        Returns:
            FailureStrategy | None: The CLI failure strategy, or None if not set.
        """
        return self._cli_failure_strategy

    @cli_failure_strategy.setter
    def cli_failure_strategy(self, value: FailureStrategy | None) -> None:
        """Update CLI failure strategy that overrides workflow-defined failure strategy.

        Args:
            value: FailureStrategy enum value or None.

        Raises:
            CoreError: If value is not an FailureStrategy or None.
        """
        if value is not None and not isinstance(value, FailureStrategy):
            raise CoreError(
                f"CLI failure strategy must be an FailureStrategy enum or None, got {type(value).__name__}",
                component="NornFlow",
            )
        self._cli_failure_strategy = value

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
            AttributeError: Always raised to prevent direct setting of the tasks catalog.
        """
        raise CatalogError("Cannot set tasks catalog directly.", catalog_name="tasks")

    @property
    def workflows_catalog(self) -> FileCatalog:
        """
        Get the workflows catalog.

        Returns:
            FileCatalog: Catalog of workflows names and the correspoding file Path to it.
        """
        return self._workflows_catalog

    @workflows_catalog.setter
    def workflows_catalog(self, _: Any) -> None:
        """
        Prevent setting the workflows catalog directly.

        Raises:
            AttributeError: Always raised to prevent direct setting of the tasks catalog.
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
            AttributeError: Always raised to prevent direct setting of the filters catalog.
        """
        raise CatalogError("Cannot set filters catalog directly.", catalog_name="filters")

    @property
    def workflow(self) -> Workflow | str:
        """
        Get the workflow object.

        Returns:
            Workflow | str: The workflow object.
        """
        return self._workflow

    @workflow.setter
    def workflow(self, value: Workflow) -> None:
        """
        Set the workflow object.

        Args:
            value (Any): The workflow object to set.
        """
        if not isinstance(value, Workflow):
            raise WorkflowError(
                f"NornFlow.workflow MUST be a Workflow object, but an object of {type(value)} was "
                f"provided: {value}"
            )
        self._workflow = value

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
            SettingsModificationError: Always raised to prevent direct setting of processors.
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

        # Phase 1: Load built-in tasks
        self._tasks_catalog.register_from_module(builtin_tasks, predicate=is_nornir_task)

        # Phase 2: Load tasks from local directories
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

        # Phase 1: Load built-in filters
        self._filters_catalog.register_from_module(
            builtin_filters, predicate=is_nornir_filter, transform_item=process_filter
        )

        # Phase 2: Load filters from local directories
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

        # Process each workflow directory using FileCatalog's discover_items_in_dir
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
            NornFlowInitializationError: If any invalid keys are found in kwargs.
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

        If self.workflow is a string, resolve it to a Workflow object using
        the workflows catalog. If the workflow is not found or not set,
        raise an appropriate error.

        Raises:
            WorkflowError: If workflow is not set or not found in the catalog
        """
        if not self.workflow:
            raise WorkflowError("No Workflow object was provided.", component="NornFlow")

        if isinstance(self.workflow, str):
            workflow_name = self.workflow
            workflow_path = self._workflows_catalog.get(workflow_name)

            if not workflow_path:
                raise WorkflowError(
                    f"Workflow '{workflow_name}' not found in the workflows catalog.", component="NornFlow"
                )

            self.workflow = WorkflowFactory(
                workflow_path=workflow_path,
                settings=self.settings,
                cli_vars=self.cli_vars,
                cli_filters=self.cli_filters,
                cli_failure_strategy=self.cli_failure_strategy,
            ).create()

    def run(self, dry_run: bool = False) -> int:
        """
        Execute the configured workflow with the current NornFlow settings.

        This method orchestrates the complete workflow execution process:
        1. Ensures a workflow is configured and ready
        2. Applies processor precedence rules
        3. Passes all necessary catalogs, CLI variables, and CLI filters to the workflow
        4. Executes the workflow tasks against the filtered inventory

        Processor Precedence:
        If processors were specified via constructor kwargs (typically from CLI), they take
        precedence over workflow-specific processors, which in turn take precedence over
        global processors from settings.

        CLI Variables and CLI Filters:
        The CLI variables and CLI filters stored in this NornFlow instance are passed to the workflow
        and have the highest precedence in their respective systems. These can originate from
        actual CLI arguments or be set programmatically as overrides.

        Any exceptions that might happen in the encapsulated logic will just bubble-up
        back to the caller of NornFlow.run(). This is to allow the caller the flexibility
        to process and handle it as fits.

        Returns:
            int: Exit code representing the failure percentage (0-100), where 0 means no failures
            or no execution statistics available, and higher values indicate the percentage of
            failed task executions (rounded down).
        """
        self._ensure_workflow()

        # If kwargs processors specified, disable workflow-specific processors
        if self._kwargs_processors and self.workflow.processors_config:
            # Simply disable workflow processors to enforce kwargs precedence
            self.workflow.processors_config = None

        with self.nornir_manager:
            return self.workflow.run(
                self.nornir_manager,
                self.tasks_catalog,
                self.filters_catalog,
                self.settings.local_workflows_dirs,
                self.processors,
                cli_vars=self.cli_vars,
                cli_filters=self.cli_filters,
                dry_run=dry_run,
            )


class NornFlowBuilder:
    """
    Builder class for constructing NornFlow objects with a fluent interface.

    The builder provides a structured way to configure all aspects of a NornFlow instance:
    - Settings configuration (via object or file path)
    - Workflow configuration (via object, name, path or dictionary)
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
                          .with_workflow_name('deploy')
                          .with_cli_vars({'env': 'prod', 'debug': True})
                          .with_cli_filters({'hosts': ['router1', 'router2']})
                          .build()

    Order of preference for building a NornFlowSettings object:
      1. with_settings_object()
      2. with_settings_path()

    Order of preference for building a Workflow object:
      1. with_workflow_object()
      2. with_workflow_name()
      3. with_workflow_path()
      4. with_workflow_dict()

    NOTE: In this NornFlowBuilder class, we actually enforce only the order of items 1 and 2.
    It's only if neither are provided that NornFlowBuilder avails of the WorkflowFactory class
    which will enforce the preference order of items 3 and 4.
    """

    def __init__(self):
        """
        Initialize the NornFlowBuilder with default values.
        """
        self._settings: NornFlowSettings | None = None
        self._workflow_path: str | Path | None = None
        self._workflow_dict: dict[str, Any] | None = None
        self._workflow_object: Workflow | None = None
        self._workflow_name: str | None = None
        self._processors: list[dict[str, Any]] | None = None
        self._cli_vars: dict[str, Any] | None = None
        self._cli_filters: dict[str, Any] | None = None
        self._cli_failure_strategy: FailureStrategy | None = None
        self._kwargs: dict[str, Any] = {}

    def with_settings_object(self, settings_object: NornFlowSettings) -> "NornFlowBuilder":
        """
        Set the NornFlowSettings object for the builder.

        Args:
            settings_object (NornFlowSettings): The NornFlowSettings object.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        self._settings = settings_object
        return self

    def with_settings_path(self, settings_path: str | Path) -> "NornFlowBuilder":
        """
        Creates a NornFlowSettings for the builder, based on a file path.
        This only takes effect if the settings object has not been set yet.
        Initializing NorFlow with a fully formed NornFlowSettings object is preferred.

        Args:
            settings_path (str | Path): The path to a YAML file to be used by NornFlowSettings object.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        if not self._settings:
            settings_object = NornFlowSettings(settings_file=settings_path)
            self.with_settings_object(settings_object)
        return self

    def with_workflow_path(self, workflow_path: str | Path) -> "NornFlowBuilder":
        """
        Set the workflow path for the builder.

        Args:
            workflow_path (str | Path): Path to the workflow file.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        self._workflow_path = workflow_path
        return self

    def with_workflow_dict(self, workflow_dict: dict[str, Any]) -> "NornFlowBuilder":
        """
        Set the workflow dictionary for the builder.

        Args:
            workflow_dict (dict[str, Any]): Dictionary representing the workflow.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        self._workflow_dict = workflow_dict
        return self

    def with_workflow_object(self, workflow_object: Workflow) -> "NornFlowBuilder":
        """
        Set the workflow object for the builder.

        Args:
            workflow_object (Workflow): A fully formed Workflow object.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        self._workflow_object = workflow_object
        return self

    def with_workflow_name(self, workflow_name: str) -> "NornFlowBuilder":
        """
        Set the workflow name for the builder.

        Args:
            workflow_name (str): The name of the workflow to set.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        self._workflow_name = workflow_name
        return self

    def with_processors(self, processors: list[dict[str, Any]]) -> "NornFlowBuilder":
        """
        Set the processor configurations for the builder.

        Args:
            processors (list[dict[str, Any]]): List of processor configurations.
                Each must be a dict with 'class' and optional 'args' keys.

        Returns:
            NornFlowBuilder: The builder instance.
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
            NornFlowBuilder: The builder instance.
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
            NornFlowBuilder: The builder instance.
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
            NornFlowBuilder: The builder instance.
        """
        self._cli_failure_strategy = cli_failure_strategy
        return self

    def with_kwargs(self, **kwargs: Any) -> "NornFlowBuilder":
        """
        Set additional keyword arguments for the builder.

        Args:
            **kwargs (Any): Additional keyword arguments.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        self._kwargs.update(kwargs)
        return self

    def build(self) -> NornFlow:
        """
        Build and return a NornFlow object based on the provided configurations.

        The built NornFlow instance will include all configured components:
        - Settings (from object or file path)
        - Workflow (from various sources based on precedence)
        - Processors (if specified)
        - CLI variables (with highest precedence in variable resolution)
        - CLI inventory filters (with highest precedence for inventory filtering)

        Returns:
            NornFlow: The constructed NornFlow object with all configurations applied.
        """
        workflow = self._workflow_object or self._workflow_name

        if not workflow:
            # we pass both workflow_path and workflow_dict to WorkflowFactory
            # and leave it to the factory to decide which one to use
            if self._workflow_path or self._workflow_dict:
                workflow_factory = WorkflowFactory(
                    workflow_path=self._workflow_path,
                    workflow_dict=self._workflow_dict,
                    settings=self._settings,
                    cli_vars=self._cli_vars,
                    cli_filters=self._cli_filters,
                    cli_failure_strategy=self._cli_failure_strategy,
                )
                workflow = workflow_factory.create()

        return NornFlow(
            nornflow_settings=self._settings,
            workflow=workflow,
            processors=self._processors,
            cli_vars=self._cli_vars,
            cli_filters=self._cli_filters,
            cli_failure_strategy=self._cli_failure_strategy,
            **self._kwargs,
        )
