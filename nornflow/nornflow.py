from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.task import AggregatedResult, Task
from nornir_utils.plugins.functions import print_result

from nornflow.exceptions import TaskLoadingError, TasksCatalogModificationError
from nornflow.settings import NornFlowSettings
from nornflow.utils import import_module, is_nornir_task


class NornFlow:
    def __init__(self, nornflow_settings: NornFlowSettings = None, **kwargs: Any):
        self.settings = nornflow_settings or NornFlowSettings(**kwargs)
        self.nornir = InitNornir(
            config_file=self.settings.nornir_config_file,
            dry_run=self.settings.dry_run,
            **kwargs,
        )
        self._tasks_catalog: dict[str, Callable] = {}
        self._load_tasks()

    def _load_tasks(self) -> None:
        """
        Entrypoint method to find all Nornir tasks from directories specified in
        the NornFlow configuration.
        """
        self._tasks_catalog = {}
        for task_dir in self.settings.tasks:
            self._load_tasks_from_directory(task_dir)

    def _load_tasks_from_directory(self, task_dir: str) -> None:
        """
        Start the recursive loading process for all Nornir tasks found in
        all python modules from a specific directory.

        Args:
            task_dir (str): Path to the directory containing task files.
        """
        task_path = Path(task_dir)
        for py_file in task_path.rglob("*.py"):
            self._load_tasks_from_file(py_file)

    def _load_tasks_from_file(self, py_file: Path) -> None:
        """
        Load tasks from a specific Python module.

        Args:
            py_file (Path): Path to the Python file.

        Raises:
            TaskLoadingException: If there is an error loading tasks from the file.
        """
        try:
            module_name = py_file.stem
            module_path = str(py_file)
            module = import_module(module_name, module_path)
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

    def run(self) -> bool:
        """
        Runs the NornFlow job.
        """
        if self.settings.parallel_exec:
            self._run_tasks_individually()
        else:
            self._run_grouped_tasks()

    def _run_tasks_individually(self) -> None:
        """
        Run all tasks individually.
        """
        print("Running tasks individually")
        for task_name, task_func in self.tasks_catalog.items():
            print(f"Running task: {task_name}")
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

    def _parent_task(self, task: Task) -> AggregatedResult:
        """
        Parent task that runs all tasks in the tasks catalog.

        Args:
            task (Task): The Nornir task object.

        Returns:
            AggregatedResult: The aggregated result of all tasks.
        """
        aggregated_result = AggregatedResult(task.name)
        for task_func in self.tasks_catalog.values():
            result = task.run(task=task_func)
            aggregated_result[task_func.__name__] = result
        return aggregated_result


# for testing purposes only
if __name__ == "__main__":
    nornflow = NornFlow()
    nornflow.run()
