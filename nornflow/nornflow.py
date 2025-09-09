import inspect  # noqa: I001
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornflow.builtins import DefaultNornFlowProcessor
from nornflow.builtins import filters as builtin_filters
from nornflow.builtins import tasks as builtin_tasks
from nornflow.constants import (
    NORNFLOW_INVALID_INIT_KWARGS,
    NORNFLOW_SUPPORTED_YAML_EXTENSIONS,
)
from nornflow.exceptions import (
    CatalogModificationError,
    DirectoryNotFoundError,
    EmptyTaskCatalogError,
    FilterLoadingError,
    NornFlowAppError,
    NornFlowInitializationError,
    NornFlowRunError,
    NornirConfigError,
    SettingsModificationError,
    TaskLoadingError,
)
from nornflow.nornir_manager import NornirManager
from nornflow.settings import NornFlowSettings
from nornflow.utils import (
    discover_items_in_dir,
    is_nornir_filter,
    is_nornir_task,
    load_processor,
    process_module_attributes,
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
        except NornFlowInitializationError:
            # Re-raise NornFlowInitializationError as is
            raise
        except Exception as e:
            # Wrap any other exception in NornFlowInitializationError
            raise NornFlowInitializationError(f"Failed to initialize NornFlow: {e!s}") from e

    def _load_processors(self) -> None:
        """
        Load processors from various sources by precedence:
        1. Processors passed through kwargs - Likely coming from CLI
        2. Settings file processors (settings.processors)
        3. Default processor (DefaultNornFlowProcessor)

        The loaded processors are stored in self._processors for later use during
        workflow execution.
        """
        # Check if processors were directly specified in constructor kwargs (CLI processors)
        if self._kwargs_processors:
            self._processors = []
            for processor_config in self._kwargs_processors:
                processor = load_processor(processor_config)
                self._processors.append(processor)

        # Otherwise, check if processors are defined in settings
        elif self.settings.processors:
            self._processors = []

            for processor_config in self.settings.processors:
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
        raise NornirConfigError()

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
        raise SettingsModificationError()

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
    def cli_vars(self, value: Any) -> None:
        """
        Prevent setting the CLI variables directly after initialization.

        CLI variables are set during NornFlow initialization and passed to workflows
        during execution. To modify variables at runtime, use the workflow.run()
        method's cli_vars parameter, which supports late binding. A NornFlow instance
        itself does not allow direct modification of its CLI variables after initialization.

        Args:
            value (Any): Attempted value to set.

        Raises:
            SettingsModificationError: Always raised to prevent direct modification.
        """
        raise SettingsModificationError("CLI variables cannot be modified after initialization")

    @property
    def tasks_catalog(self) -> dict[str, Callable]:
        """
        Get the tasks catalog.

        Returns:
            dict[str, Callable]: Dictionary of task names and their corresponding functions.
        """
        return self._tasks_catalog

    @tasks_catalog.setter
    def tasks_catalog(self, _: Any) -> None:
        """
        Prevent setting the tasks catalog directly.

        Raises:
            AttributeError: Always raised to prevent direct setting of the tasks catalog.
        """
        raise CatalogModificationError("tasks")

    @property
    def workflows_catalog(self) -> dict[str, Path]:
        """
        Get the workflows catalog.

        Returns:
            dict[str, Path]: Dictionary of workflows names and the correspoding file Path to it.
        """
        return self._workflows_catalog

    @workflows_catalog.setter
    def workflows_catalog(self, _: Any) -> None:
        """
        Prevent setting the workflows catalog directly.

        Raises:
            AttributeError: Always raised to prevent direct setting of the tasks catalog.
        """
        raise CatalogModificationError("workflows")

    @property
    def filters_catalog(self) -> dict[str, Callable]:
        """
        Get the filters catalog.

        Returns:
            dict[str, Callable]: Dictionary of filter names and their corresponding functions.
        """
        return self._filters_catalog

    @filters_catalog.setter
    def filters_catalog(self, _: Any) -> None:
        """
        Prevent setting the filters catalog directly.

        Raises:
            AttributeError: Always raised to prevent direct setting of the filters catalog.
        """
        raise CatalogModificationError("filters")

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
            raise NornFlowAppError(  # Changed from NornFlowError
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
        raise NornFlowInitializationError(
            message="Processors cannot be set directly, but must be loaded from nornflow settings file."
        )

    def _load_tasks_catalog(self) -> None:
        """
        Entrypoint method that will put in motion the logic to discover and load
        all Nornir tasks from directories specified in the NornFlow configuration.

        Tasks are loaded in two phases:
        1. Built-in tasks from nornflow.builtins.tasks module (always available)
        2. User-defined tasks from local_tasks_dirs (can override built-ins)
        """
        self._tasks_catalog = {}

        # Phase 1: Load built-in tasks
        self._register_nornir_tasks_from_module(builtin_tasks)

        # Phase 2: Load tasks from local directories (can override built-ins)
        for task_dir in self.settings.local_tasks_dirs:
            self._discover_tasks_in_dir(task_dir)

        if not self._tasks_catalog:
            raise EmptyTaskCatalogError()

    def _discover_tasks_in_dir(self, task_dir: str) -> None:
        """
        Discover and load tasks from a specific directory.

        Args:
            task_dir (str): Path to directory containing tasks.
        """
        try:
            # Use the utility function
            discover_items_in_dir(
                task_dir, lambda module: self._register_nornir_tasks_from_module(module), "tasks"
            )
        except DirectoryNotFoundError:
            # Just continue if directory doesn't exist
            pass
        except Exception as e:
            raise TaskLoadingError(f"Error loading tasks: {e!s}") from e

    def _register_nornir_tasks_from_module(self, module: Any) -> None:
        """
        Register tasks from a module.

        Args:
            module (Any): Imported module.
        """
        process_module_attributes(
            module, is_nornir_task, lambda attr_name, attr: self._tasks_catalog.update({attr_name: attr})
        )

    def _load_filters_catalog(self) -> None:
        """
        Load inventory filters in two phases:

        Phase 1: Load built-in filters from nornflow.filters module
        Phase 2: Load user-defined filters from configured local_filters_dirs

        The filters catalog stores each filter as a tuple of (function_object, parameter_names),
        where parameter_names is a list of parameter names excluding the first 'host' parameter.
        This structure enables the flexible parameter passing in workflow definitions.
        """
        self._filters_catalog = {}

        # Phase 1: Load built-in filters from nornflow.inventory_filters
        self._register_nornir_filters_from_module(builtin_filters)

        # Phase 2: Load filters from local directories (can override built-ins)
        if hasattr(self.settings, "local_filters_dirs"):
            for filter_dir in self.settings.local_filters_dirs:
                self._discover_filters_in_dir(filter_dir)

    def _discover_filters_in_dir(self, filter_dir: str) -> None:
        """
        Discover and load filters from a specific directory.

        Args:
            filter_dir (str): Path to directory containing filters.
        """
        try:
            discover_items_in_dir(
                filter_dir,
                lambda module: self._register_nornir_filters_from_module(module),
                "filters",
            )
        except DirectoryNotFoundError:
            # Just continue if directory doesn't exist
            pass
        except Exception as e:
            raise FilterLoadingError(f"Error loading filters: {e!s}") from e

    def _register_nornir_filters_from_module(self, module: Any) -> None:
        """
        Register filters from a module.

        Stores each filter as a tuple of (function_object, parameter_names),
        where parameter_names excludes the first 'host' parameter.

        Args:
            module (Any): Imported module.
        """

        def process_filter(attr_name: str, attr: Callable) -> None:
            # Get the function signature to extract parameter names
            sig = inspect.signature(attr)
            # Skip the first parameter (host) and get remaining parameter names
            param_names = list(sig.parameters.keys())[1:]
            # Store as tuple: (function_object, parameter_names)
            self._filters_catalog[attr_name] = (attr, param_names)

        process_module_attributes(module, is_nornir_filter, process_filter)

    def _load_workflows_catalog(self) -> None:
        """
        Entrypoint method that will put in motion the logic to discover and load
        all Nornir tasks from directories specified in the NornFlow configuration.
        """
        self._workflows_catalog = {}
        for workflow_dir in self.settings.local_workflows_dirs:
            self._discover_workflows_in_dir(workflow_dir)

    def _discover_workflows_in_dir(self, workflow_dir: str) -> None:
        """
        Discover and load workflows from all files in a specific directory that match the supported
        extensions.

        Args:
            workflow_dir (str): Path to the directory containing workflow files.

        Raises:
            DirectoryNotFoundError: If the specified directory does not exist.
        """
        workflow_path = Path(workflow_dir)
        if not workflow_path.is_dir():
            raise DirectoryNotFoundError(  # Changed from LocalDirectoryNotFoundError
                directory=workflow_dir, extra_message="Couldn't load workflows."
            )

        for file in workflow_path.rglob("*"):
            if file.suffix in NORNFLOW_SUPPORTED_YAML_EXTENSIONS:
                self._workflows_catalog[file.name] = file

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
            raise NornFlowInitializationError(invalid_kwargs=invalid_keys)

    def _ensure_workflow(self) -> None:
        """
        Checks if self.workflow is set. If not, raises NornFlowRunError.

        Otherwise, if self.workflow contains a string, assumes it is workflow name, and attempts to
        set self.workflow to a Workflow object created from a file path in self.workflows_catalog
        associated with that workflow name. If none is found, raises a NornFlowRunError.

        If self.workflow is a Workflow object, does nothing.

        Raises:
            NornFlowRunError: If self.workflow is not set or if the workflow name is not found in
            the workflows catalog.
        """
        if not self.workflow:
            raise NornFlowRunError("No Workflow object was provided.")

        if isinstance(self.workflow, str):
            workflow_name = self.workflow
            workflow_path = self.workflows_catalog.get(workflow_name)

            if not workflow_path:
                raise NornFlowRunError(f"Workflow '{workflow_name}' not found in the workflows catalog.")

            self.workflow = WorkflowFactory(
                workflow_path=workflow_path,
                settings=self.settings,
                cli_vars=self.cli_vars,
            ).create()

    def run(self, dry_run: bool = False) -> None:
        """
        Execute the configured workflow with the current NornFlow settings.

        This method orchestrates the complete workflow execution process:
        1. Ensures a workflow is configured and ready
        2. Applies processor precedence rules
        3. Passes all necessary catalogs and CLI variables to the workflow
        4. Executes the workflow tasks against the filtered inventory

        Processor Precedence:
        If processors were specified via constructor kwargs (typically from CLI), they take
        precedence over workflow-specific processors, which in turn take precedence over
        global processors from settings.

        CLI Variables:
        The CLI variables stored in this NornFlow instance are passed to the workflow
        and have the highest precedence in the variable resolution system. These variables
        can originate from actual CLI arguments or be set programmatically as overrides.

        The workflow's run() method supports late binding, allowing these CLI variables
        to be updated or overridden at runtime if needed.

        Args:
            dry_run: Whether to run the workflow in dry-run mode

        Raises:
            NornFlowRunError: If no workflow is configured or workflow execution fails
        """
        self._ensure_workflow()

        # If kwargs processors specified, disable workflow-specific processors
        if self._kwargs_processors and self.workflow.processors_config:
            # Simply disable workflow processors to enforce kwargs precedence
            self.workflow.processors_config = None

        # Pass nornir_manager, catalogs, processors and cli_vars to workflow.run
        # CLI variables are passed with highest precedence in variable resolution
        self.workflow.run(
            self.nornir_manager,
            self.tasks_catalog,
            self.filters_catalog,
            self.settings.local_workflows_dirs,
            self.processors,
            cli_vars=self.cli_vars,  # Pass CLI variables for highest precedence
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
    - Additional keyword arguments

    CLI Variables in Builder Context:
    The builder's `with_cli_vars()` method sets variables that will have the highest
    precedence in the variable resolution system. While termed "CLI variables" due to
    their primary use case (command-line arguments), these serve as a universal
    override mechanism in the builder pattern:

    - Can represent actual CLI arguments parsed by a command-line interface
    - Can be set programmatically for workflow customization
    - Always override any other variable source (workflow vars, defaults, etc.)
    - Are passed to the workflow during execution with late-binding support

    Usage Examples:
        # Basic usage
        builder = NornFlowBuilder()
        nornflow = builder.with_settings_path('settings.yaml')
                          .with_workflow_name('deploy')
                          .with_cli_vars({'env': 'prod', 'debug': True})
                          .build()

        # Programmatic override usage
        builder = NornFlowBuilder()
        if emergency_mode:
            cli_overrides = {'skip_tests': True, 'timeout': 300}
        else:
            cli_overrides = {'run_full_suite': True}

        nornflow = builder.with_workflow_object(workflow)
                          .with_cli_vars(cli_overrides)
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
                )
                workflow = workflow_factory.create()

        kwargs = self._kwargs.copy()
        if self._cli_vars is not None:
            kwargs["cli_vars"] = self._cli_vars

        return NornFlow(
            nornflow_settings=self._settings, workflow=workflow, processors=self._processors, **kwargs
        )
