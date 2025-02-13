from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.task import AggregatedResult, Task
from nornir_utils.plugins.functions import print_result

from nornflow.constants import NONRFLOW_SETTINGS_OPTIONAL, NORNFLOW_INVALID_INIT_KWARGS
from nornflow.exceptions import (
    EmptyTaskCatalogError,
    LocalTaskDirectoryNotFoundError,
    NornFlowInitializationError,
    NornirConfigsModificationError,
    NoTasksToRunError,
    SettingsModificationError,
    TaskDoesNotExistError,
    TaskLoadingError,
    TasksCatalogModificationError,
)
from nornflow.settings import NornFlowSettings
from nornflow.utils import import_module_from_path, is_nornir_task
from nornflow.inventory_filters import filter_by_hostname, filter_by_groups

class NornFlow:
    def __init__(
        self, nornflow_settings: NornFlowSettings = None, tasks_to_run: list[str] = None, inventory_filters: dict[str, list[str]] = None, **kwargs: Any
    ):
        # Some kwargs should only be set through the YAML settings file.
        self._check_invalid_kwargs(kwargs)
        self._settings = nornflow_settings or NornFlowSettings(**kwargs)
        self._load_tasks_catalog()
        self.tasks_to_run = tasks_to_run
        self.inventory_filters = inventory_filters

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
    def tasks_to_run(self) -> list[str]:
        """
        Get the tasks to run.

        Returns:
            list[str]: List of task names to run.
        """
        return self._tasks_to_run
    
    @tasks_to_run.setter
    def tasks_to_run(self, tasks_to_run: list[str]) -> list[str]:
        """
        Validates the tasks_to_run input and sets the self._tasks_to_run attribute.
    
        Args:
            tasks_to_run (list[str]): List of task names to run.
    
        Returns:
            list[str]: The validated tasks to run list.
    
        Raises:
            NornFlowInitializationError: If:
                - tasks_to_run is not a list
                - any item in the list is not a string
        """
        if not tasks_to_run:
            self._tasks_to_run = []
            return
    
        if not isinstance(tasks_to_run, list):
            raise NornFlowInitializationError(["tasks_to_run"], "is not a list")
    
        if not all(isinstance(task, str) for task in tasks_to_run):
            raise NornFlowInitializationError(
                ["tasks_to_run"], 
                "all items must be strings"
            )
    
        self._tasks_to_run = tasks_to_run
    
    @property
    def inventory_filters(self) -> dict[str, list[str]]:
        """
        Get the inventory filters.

        Returns:
            dict[str, list[str]]: Dictionary with 'hosts' and/or 'groups' keys,
                each containing a list of strings.
        """
        return self._inventory_filters
    
    @inventory_filters.setter
    def inventory_filters(self, inventory_filters: dict[str, list[str]]) -> dict[str, list[str]]:
        """
        Validates the inventory_filters input and sets the self._inventory_filters attribute.
    
        Args:
            inventory_filters (dict[str, list[str]]): Dictionary with 'hosts' and/or 'groups' keys,
                each containing a list of strings.
    
        Returns:
            dict[str, list[str]]: The validated inventory filters dictionary.
    
        Raises:
            NornFlowInitializationError: If:
                - inventory_filters is not a dict
                - contains invalid keys
                - values are not lists
                - list items are not strings
        """
        if not inventory_filters:
            self._inventory_filters = {}
            return
    
        if not isinstance(inventory_filters, dict):
            raise NornFlowInitializationError(["inventory_filters"], "is not a dict")
    
        valid_keys = {"hosts", "groups"}
        invalid_keys = set(inventory_filters.keys()) - valid_keys
        if invalid_keys:
            raise NornFlowInitializationError(
                ["inventory_filters"], 
                f"unknown filter keys included: {', '.join(invalid_keys)}"
            )
    
        # Validate that values are lists of strings
        for key, value in inventory_filters.items():
            if not isinstance(value, list):
                raise NornFlowInitializationError(
                    ["inventory_filters"], 
                    f"value for '{key}' is not a list"
                )
            
            if not all(isinstance(item, str) for item in value):
                raise NornFlowInitializationError(
                    ["inventory_filters"], 
                    f"all items in '{key}' must be strings"
                )
    
        self._inventory_filters = inventory_filters

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
        if not self.tasks_to_run:
            raise NoTasksToRunError("No tasks selected to run.")

        missing_tasks = [task_name for task_name in self.tasks_to_run if task_name not in self.tasks_catalog]

        if missing_tasks:
            if not self.settings.ignore_missing_tasks:
                raise TaskDoesNotExistError(missing_tasks)

            print(
                "The following tasks were not found in the tasks catalog and will be ignored:\n"
                f"  - {'\n  - '.join(missing_tasks)}"
            )

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

    def _filter_inventory(self) -> None:
        """
        Filter the inventory based on the inventory_filters attribute.
        """
        print("inventory_filters: ", self.inventory_filters)

        hosts, groups = self.inventory_filters.get("hosts"), self.inventory_filters.get("groups")
        
        if hosts:
            self.nornir = self.nornir.filter(filter_func=filter_by_hostname, hostnames=self.inventory_filters["hosts"])
        
        if groups:
            self.nornir = self.nornir.filter(filter_func=filter_by_groups, groups=self.inventory_filters["groups"])
        
    def run(self) -> None:
        """
        Runs the NornFlow job.
        """
        self._check_tasks_to_run()
        self._filter_inventory()

        if self.settings.parallel_exec:
            self._run_tasks_individually()
        else:
            self._run_grouped_tasks()

# for testing purposes only
if __name__ == "__main__":
    nornflow = NornFlow(tasks_to_run=["task1", "task2", "no_task"])
    # nornflow.run()
    # print(nornflow.settings)
    # print(dir(nornflow.nornir.inventory.hosts["leaf1-ios"]))
    # print(nornflow.nornir.inventory.hosts["leaf1-ios"].platform)
    from nornflow.inventory_filters import filter_by_groups, filter_by_hostname
    # print(nornflow.nornir.filter(filter_func=filter_by_hostname, hostnames=["leaf1-ios"]).inventory.hosts["leaf1-ios"].dict())
    print(nornflow.nornir.filter(filter_func=filter_by_groups, groups=["device_role__leaf"]).inventory.hosts)

    # print(nornflow.nornir.inventory.dict())