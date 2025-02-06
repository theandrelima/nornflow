import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nornir import InitNornir
from nornir.core.task import AggregatedResult, Result, Task
from nornir_utils.plugins.functions import print_result

from nornflow.settings import NornFlowSettings


class NornFlow:
    def __init__(self, nornflow_settings: NornFlowSettings = None, **kwargs: Any):
        self.config = nornflow_settings or NornFlowSettings(**kwargs)
        self.nornir = InitNornir(
            config_file=self.config.nornir_config_file,
            dry_run=self.config.dry_run,
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
        for task_dir in self.config.tasks:
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
        """
        module_name = py_file.stem
        module_path = str(py_file)
        module = self._import_module(module_name, module_path)
        self._register_tasks_from_module(module)

    def _import_module(self, module_name: str, module_path: str) -> Any:
        """
        Import a module from a given file path.

        Args:
            module_name (str): Name of the module.
            module_path (str): Path to the module file.

        Returns:
            Any: Imported module.
        """
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _register_tasks_from_module(self, module: Any) -> None:
        """
        Register tasks from a module.

        Args:
            module (Any): Imported module.
        """
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if self._is_nornir_task(attr):
                self._tasks_catalog[attr_name] = attr

    def _is_nornir_task(self, attr: Any) -> bool:
        """
        Check if an attribute is a Nornir task.

        Args:
            attr (Any): Attribute to check.

        Returns:
            bool: True if the attribute is a Nornir task, False otherwise.
        """
        if callable(attr) and hasattr(attr, "__annotations__"):
            annotations = attr.__annotations__
            has_task_param = any(param == Task for param in annotations.values())
            returns_result = annotations.get("return") == Result
            return has_task_param and returns_result
        return False

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
        raise AttributeError("Cannot set tasks catalog directly.")

    def run(self) -> bool:
        """
        Runs the NornFlow job.
        """
        if self.config.parallel_exec:
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
