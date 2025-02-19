from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir import InitNornir

from nornflow.constants import (
    NONRFLOW_SETTINGS_OPTIONAL,
    NORNFLOW_INVALID_INIT_KWARGS,
    NORNFLOW_SUPPORTED_WORKFLOW_EXTENSIONS,
)
from nornflow.exceptions import (
    CatalogModificationError,
    EmptyTaskCatalogError,
    LocalDirectoryNotFoundError,
    NornFlowError,
    NornFlowInitializationError,
    NornFlowRunError,
    NornirConfigsModificationError,
    SettingsModificationError,
    TaskLoadingError,
)
from nornflow.settings import NornFlowSettings
from nornflow.utils import import_module_from_path, is_nornir_task
from nornflow.workflow import Workflow, WorkflowFactory


class NornFlow:
    def __init__(
        self,
        nornflow_settings: NornFlowSettings | None = None,
        workflow: Workflow | None = None,
        **kwargs: Any,
    ):
        # Some kwargs should only be set through the YAML settings file.
        self._check_invalid_kwargs(kwargs)

        # a NornFlow object must have a NornFlowSettings object
        self._settings = nornflow_settings or NornFlowSettings(**kwargs)

        # a NornFlow object can exist without a Workflow object BEFORE the run() method is called
        self._workflow = workflow

        self._load_tasks_catalog()
        self._load_workflows_catalog()

        # kwargs need to be cleaned up before passing them to InitNornir
        self._remove_optional_settings_from_kwargs(kwargs)

        self.nornir = InitNornir(
            config_file=self.settings.nornir_config_file,
            dry_run=self.settings.dry_run,
            **kwargs,
        )

    @property
    def nornir_configs(self) -> dict[str, Any]:
        """
        Get the Nornir configurations as a dict.

        Returns:
            Dict[str, Any]: Dictionary containing the Nornir configurations.
        """
        return self.nornir.config.dict()

    @nornir_configs.setter
    def nornir_configs(self, value: Any) -> None:
        raise NornirConfigsModificationError()

    @property
    def settings(self) -> str:
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
    def tasks_catalog(self) -> dict[str, Callable]:
        """
        Get the tasks catalog.

        Returns:
            Dict[str, Callable]: Dictionary of task names and their corresponding functions.
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
            Dict[str, Callable]: Dictionary of workflows names and the correspoding file Path to it.
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
    def workflow(self) -> str | Workflow:
        """
        Get the workflow object.

        Returns:
            Union[str, Workflow]: The workflow object.
        """
        return self._workflow

    @workflow.setter
    def workflow(self, value: "Workflow") -> None:
        """
        Set the workflow object.

        Args:
            value (Any): The workflow object to set.
        """
        if not isinstance(value, Workflow):
            raise NornFlowError(
                f"NornFlow.workflow MUST be a Workflow object, but and object of  {type(value)} was "
                f"provided: {value}"
            )
        self._workflow = value

    def _load_tasks_catalog(self) -> None:
        """
        Entrypoint method that will put in motion the logic to discover and load
        all Nornir tasks from directories specified in the NornFlow configuration.
        """
        self._tasks_catalog = {}
        for task_dir in self.settings.local_tasks_dirs:
            self._discover_tasks_in_dir(task_dir)

        if not self._tasks_catalog:
            raise EmptyTaskCatalogError()

    def _discover_tasks_in_dir(self, task_dir: str) -> None:
        """
        Discover and load tasks from all Python modules in a specific directory.

        Args:
            task_dir (str): Path to the directory containing task files.

        Raises:
            LocalTaskDirectoryNotFoundError: If the specified directory does not exist.
            TaskLoadingError: If there is an error loading tasks from a file.
        """
        task_path = Path(task_dir)
        if not task_path.is_dir():
            raise LocalDirectoryNotFoundError(directory=task_dir, extra_message="Couldn't load tasks.")

        for py_file in task_path.rglob("*.py"):
            try:
                module_name = py_file.stem
                module_path = str(py_file)
                module = import_module_from_path(module_name, module_path)
                self._register_nornir_tasks_from_module(module)
            except Exception as e:
                raise TaskLoadingError(f"Error loading tasks from file '{py_file}': {e}") from e

    def _register_nornir_tasks_from_module(self, module: Any) -> None:
        """
        Register tasks from a module.

        Args:
            module (Any): Imported module.
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if is_nornir_task(attr):
                self._tasks_catalog[attr_name] = attr

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
            LocalTaskDirectoryNotFoundError: If the specified directory does not exist.
        """
        workflow_path = Path(workflow_dir)
        if not workflow_path.is_dir():
            raise LocalDirectoryNotFoundError(
                directory=workflow_dir, extra_message="Couldn't load workflows."
            )

        for file in workflow_path.rglob("*"):
            if file.suffix in NORNFLOW_SUPPORTED_WORKFLOW_EXTENSIONS:
                self._workflows_catalog[file.name] = file

    def _remove_optional_settings_from_kwargs(self, kwargs: dict[str, Any]) -> None:
        """
        Remove keys from kwargs that match the keys in NONRFLOW_OPTIONAL_SETTINGS.

        Args:
            kwargs (dict[str, Any]): The kwargs dictionary to modify.
        """
        for key in NONRFLOW_SETTINGS_OPTIONAL:
            if key in kwargs:
                del kwargs[key]

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
            raise NornFlowInitializationError(invalid_keys)

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
            raise NornFlowRunError("No Workflow object set was provided.")

        if isinstance(self.workflow, str):
            workflow_name = self.workflow
            workflow_path = self.workflows_catalog.get(workflow_name)

            if not workflow_path:
                raise NornFlowRunError(f"Workflow '{workflow_name}' not found in the workflows catalog.")

            self.workflow = WorkflowFactory(workflow_path=workflow_path).create()

    def run(self) -> None:
        """
        Runs the NornFlow job.
        """
        self._ensure_workflow()
        self.workflow.run(self.nornir, self.tasks_catalog)


class NornFlowBuilder:
    """
    Builder class for constructing NornFlow objects.

    Usage:
        - Use the with_settings(), with_workflow_path(), with_workflow_dict(), with_workflow_object(),
          with_workflow_name(), and with_kwargs() methods to set configurations.
        - Call the build() method to create a NornFlow object.
        - If both a workflow_object and a workflow_name are provided, the workflow object will be preferred.
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
        self._kwargs: dict[str, Any] = {}

    def with_settings(self, settings: NornFlowSettings) -> "NornFlowBuilder":
        """
        Set the NornFlowSettings for the builder.

        Args:
            settings (NornFlowSettings): The NornFlowSettings object.

        Returns:
            NornFlowBuilder: The builder instance.
        """
        self._settings = settings
        return self

    def with_workflow_path(self, workflow_path: str | Path) -> "NornFlowBuilder":
        """
        Set the workflow path for the builder.

        Args:
            workflow_path (Union[str, Path]): Path to the workflow file.

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

        Returns:
            NornFlow: The constructed NornFlow object.
        """
        workflow = self._workflow_object or self._workflow_name
        if not workflow:
            if self._workflow_path or self._workflow_dict:
                workflow_factory = WorkflowFactory(
                    workflow_path=self._workflow_path, workflow_dict=self._workflow_dict
                )
                workflow = workflow_factory.create()

        return NornFlow(nornflow_settings=self._settings, workflow=workflow, **self._kwargs)
