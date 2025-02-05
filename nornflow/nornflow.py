import importlib.util
from nornir import InitNornir
from pathlib import Path
from typing import Any, Dict
from nornir.core.task import Task, Result
from settings import NornFlowSettings

class NornFlow:
    def __init__(self, nornflow_settings: NornFlowSettings = None, **kwargs: Any):
        self.config = nornflow_settings or NornFlowSettings(**kwargs)
        self.nornir = InitNornir(config_file=self.config.nornir_config_file, dry_run=self.config.dry_run, **kwargs)
        self._tasks_catalog: Dict[str, Any] = {}
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
            returns_result = annotations.get('return') == Result
            return has_task_param and returns_result
        return False

    @property
    def tasks_catalog(self) -> Dict[str, Any]:
        """
        Get the tasks catalog.

        Returns:
            Dict[str, Any]: Dictionary of task names and their corresponding functions.
        """
        return self._tasks_catalog


    def run(self) -> bool:
        """
        Run NornFlow.

        Returns:
            bool: True if successful, False otherwise.
        """
        pass
