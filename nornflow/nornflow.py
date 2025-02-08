from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.task import AggregatedResult, Task
from nornir_utils.plugins.functions import print_result

from nornflow.exceptions import (
    EmptyTaskCatalogError,
    LocalTaskDirectoryNotFoundError,
    NornirConfigsModificationError,
    NoTasksToRunError,
    SettingsModificationError,
    TaskDoesNotExistError,
    TaskLoadingError,
    TasksCatalogModificationError,
    NornFlowInitializationError,
)
from nornflow.settings import NornFlowSettings
from nornflow.utils import import_module_from_path, is_nornir_task
from nornflow.constants import NONRFLOW_SETTINGS_OPTIONAL, NORNFLOW_INVALID_INIT_KWARGS


class NornFlow:
    def __init__(
        self, nornflow_settings: NornFlowSettings = None, tasks_to_run: list[str] = None, **kwargs: Any
    ):
        # Some kwargs should only be set through the YAML settings file.
        self._check_invalid_kwargs(kwargs)
        self._settings = nornflow_settings or NornFlowSettings(**kwargs)
        self._nornir_configs = self.settings.nornir_configs
        self.tasks_to_run = tasks_to_run
        self._load_tasks_catalog()
        # kwargs need to be cleaned up before passing them to InitNornir
        self._remove_optional_settings_from_kwargs(kwargs)

        self.nornir = InitNornir(
            config_file=self.settings.nornir_config_file,
            dry_run=self.settings.dry_run,
            **kwargs,
        )

    @property
    def nornir_configs(self) -> dict[str, Any]:
        return self._nornir_configs

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
    def tasks_catalog(self) -> dict[str, Any]:
        """
        Get the tasks catalog.

        Returns:
            Dict[str, Any]: Dictionary of task names and their corresponding functions.
        """
        return self._tasks_catalog

    @tasks_catalog.setter
    def tasks_catalog(self, value: dict[str, Any]) -> None:
        """
        Prevent setting the tasks catalog directly.

        Args:
            value (Dict[str, Any]): Dictionary of task names and their corresponding functions.

        Raises:
            AttributeError: Always raised to prevent direct setting of the tasks catalog.
        """
        raise TasksCatalogModificationError("Cannot set tasks catalog directly.")

    @property
    def filtered_tasks_catalog(self) -> dict[str, Any]:
        """
        Get the tasks catalog filtered by the tasks to run.

        Returns:
            Dict[str, Any]: Dictionary of task names and their corresponding functions.
        """
        return {k: v for k, v in self.tasks_catalog.items() if k in self.tasks_to_run}

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
            raise LocalTaskDirectoryNotFoundError(task_dir)

        for py_file in task_path.rglob("*.py"):
            try:
                module_name = py_file.stem
                module_path = str(py_file)
                module = import_module_from_path(module_name, module_path)
                self._register_tasks_from_module(module)
            except Exception as e:
                raise TaskLoadingError(f"Error loading tasks from file '{py_file}': {e}") from e

    def _register_tasks_from_module(self, module: Any) -> None:
        """
        Register tasks from a module.

        Args:
            module (Any): Imported module.
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if is_nornir_task(attr):
                self._tasks_catalog[attr_name] = attr

    def _check_tasks_to_run(self) -> None:
        """
        Check if the tasks to run are in the tasks catalog.

        Raises:
            TaskLoadingError: If a task to run is not in the tasks catalog.
        """
        missing_tasks = [task_name for task_name in self.tasks_to_run if task_name not in self.tasks_catalog]

        if missing_tasks:
            if not self.settings.ignore_missing_tasks:
                raise TaskDoesNotExistError(missing_tasks)

            print(
                "The following tasks were not found in the tasks catalog and will be ignored:\n"
                f"  - {'\n  - '.join(missing_tasks)}"
            )

    def run(self) -> None:
        """
        Runs the NornFlow job.
        """
        if not self.tasks_to_run:
            raise NoTasksToRunError("No tasks selected to run.")

        self._check_tasks_to_run()

        if self.settings.parallel_exec:
            self._run_tasks_individually()
        else:
            self._run_grouped_tasks()

    def _run_tasks_individually(self) -> None:
        """
        Run all tasks individually.
        """
        print("Running tasks individually")
        for task_func in self.filtered_tasks_catalog.values():
            result = self.nornir.run(task=task_func)
            print_result(result)

    def _run_grouped_tasks(self) -> None:
        """
        Run tasks grouped together.

        This method runs the tasks grouped by calling the `_parent_task` method
        and then prints the aggregated result.
        """
        print("Running grouped tasks")
        result = self.nornir.run(task=self._parent_task)
        print_result(result)

    # TODO: this should probably be extracted from here into the utils module.
    def _parent_task(self, task: Task) -> AggregatedResult:
        """
        Parent task that runs all tasks in the tasks catalog.

        Args:
            task (Task): The Nornir task object.

        Returns:
            AggregatedResult: The aggregated result of all tasks.
        """
        aggregated_result = AggregatedResult(task.name)
        for task_func in self.filtered_tasks_catalog.values():
            result = task.run(task=task_func)
            aggregated_result[task_func.__name__] = result
        return aggregated_result

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


# for testing purposes only
if __name__ == "__main__":
    nornflow = NornFlow(tasks_to_run=["task1", "task2", "no_task"])
    # nornflow.run()
    print(nornflow.settings)
    print(nornflow.nornir_configs)
    # nornflow.settings = {}
    # nornflow.nornir_configs = {}