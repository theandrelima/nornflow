import importlib.util
from pathlib import Path
from typing import Any, Callable
from types import ModuleType

import yaml
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

from nornflow.exceptions import ModuleImportError


def read_yaml_file(file_path: str) -> dict[str, Any]:
    """
    Reads a YAML file and returns its contents as a dictionary.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        dict[str, Any]: Dictionary containing the YAML file contents.
    """
    path = Path(file_path)
    with path.open() as file:
        return yaml.safe_load(file)


def import_module_from_path(module_name: str, module_path: str) -> ModuleType:
    """
    Import a module from a given file path.

    Args:
        module_name (str): Name of the module.
        module_path (str): Path to the module file.

    Returns:
        ModuleType: Imported module.

    Raises:
        ModuleImportError: If there is an error importing the module.
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        raise ModuleImportError(module_name, module_path, str(e)) from e

    return module


def is_nornir_task(attr: Callable) -> bool:
    """
    Check if an attribute is a Nornir task.

    Args:
        attr (Callable): Attribute to check.

    Returns:
        bool: True if the attribute is a Nornir task, False otherwise.
    """
    if callable(attr) and hasattr(attr, "__annotations__"):
        annotations = attr.__annotations__
        has_task_param = any(param == Task for param in annotations.values())
        returns_result = annotations.get("return") in {Result, MultiResult, AggregatedResult}
        return has_task_param and returns_result
    return False
