from pathlib import Path
from typing import Any

from pydantic_serdes.utils import load_file_to_dict

from nornflow.constants import FailureStrategy
from nornflow.exceptions import InitializationError, ResourceError, SettingsError
from nornflow.models import WorkflowModel
from nornflow.nornflow import NornFlow
from nornflow.settings import NornFlowSettings


class NornFlowBuilder:
    """
    Builder class for constructing NornFlow objects with a fluent interface.

    The builder provides a structured way to configure all aspects of a NornFlow instance:
    - Settings configuration (via object or file path)
    - Workflow configuration (via WorkflowModel object, file path, or dictionary)
    - Processor registration
    - Vars
    - Inventory filters
    - Additional keyword arguments

    Vars in Builder Context:
    The builder's `with_vars()` method sets variables that will have the highest
    precedence in the variable resolution system. While termed "vars" due to
    their primary use case (command-line arguments), these serve as a universal
    override mechanism in the builder pattern.

    Inventory Filters in Builder Context:
    The builder's `with_filters()` method sets inventory filters that will completely
    override any inventory filters defined in the workflow YAML.

    Usage Examples:
        # Basic usage
        builder = NornFlowBuilder()
        nornflow = builder.with_settings_path('settings.yaml')
                          .with_workflow_path('deploy.yaml')
                          .build()

        # Advanced configuration
        builder = NornFlowBuilder()
        nornflow = builder.with_settings_object(custom_settings)
                          .with_workflow_name('backup')
                          .with_processors([{'class': 'CustomProcessor'}])
                          .with_vars({'env': 'prod', 'debug': True})
                          .with_filters({'hosts': ['router1', 'router2']})
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
        self._vars: dict[str, Any] | None = None
        self._filters: dict[str, Any] | None = None
        self._failure_strategy: FailureStrategy | None = None
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
                settings_object = NornFlowSettings.load(settings_file=str(settings_path))
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

    def with_vars(self, vars: dict[str, Any]) -> "NornFlowBuilder":
        """
        Set vars for the NornFlow instance.

        These variables have the highest precedence in the variable resolution order
        and serve a dual purpose:
        1. Primary: Storage for variables parsed from CLI arguments (--vars)
        2. Secondary: Universal override mechanism for programmatic variable setting

        They override any variables from other sources including workflow variables,
        domain defaults, and environment variables. The variables are passed to
        workflows during execution with support for late binding.

        Usage Examples:
            # Traditional CLI argument representation
            builder.with_vars({'env': 'prod', 'debug': True})

            # Programmatic override usage
            emergency_vars = {'skip_validation': True, 'fast_mode': True}
            builder.with_vars(emergency_vars)

        Args:
            vars: Dictionary of variables with highest precedence

        Returns:
            The builder instance for method chaining.
        """
        self._vars = vars
        return self

    def with_filters(self, filters: dict[str, Any]) -> "NornFlowBuilder":
        """
        Set inventory filters for the NornFlow instance.

        These filters have the highest precedence and completely override
        any inventory filters defined in the workflow YAML.

        Args:
            filters: Dictionary of inventory filters with highest precedence

        Returns:
            The builder instance for method chaining.
        """
        self._filters = filters
        return self

    def with_failure_strategy(self, failure_strategy: FailureStrategy) -> "NornFlowBuilder":
        """
        Set failure strategy for the NornFlow instance.

        This strategy has the highest precedence and overrides any failure strategy
        defined in the workflow YAML.

        Args:
            failure_strategy: FailureStrategy enum value with highest precedence

        Returns:
            The builder instance for method chaining.
        """
        self._failure_strategy = failure_strategy
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
        - Vars
        - Inventory filters

        Returns:
            The constructed NornFlow object with all configurations applied.
        """
        if not self._settings:
            self._settings = NornFlowSettings.load()

        return NornFlow(
            nornflow_settings=self._settings,
            workflow=self._workflow,
            processors=self._processors,
            vars=self._vars,
            filters=self._filters,
            failure_strategy=self._failure_strategy,
            **self._kwargs,
        )
