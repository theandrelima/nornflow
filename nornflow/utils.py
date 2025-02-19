import importlib.util
from pathlib import Path
from typing import Any

import yaml
from nornir.core.task import Result, Task
from nornir.core.task import MultiResult, AggregatedResult

from nornflow.constants import FALSY, TRUTHY
from nornflow.exceptions import ModuleImportError


def read_yaml_file(file_path: str) -> dict:
    """
    Reads a YAML file and returns its contents as a dictionary.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        Dict: Dictionary containing the YAML file contents.
    """
    path = Path(file_path)
    with path.open() as file:
        return yaml.safe_load(file)


def is_truthy(value: str | None) -> bool:
    """
    Checks if a value is truthy.

    Args:
        value (str): Value to check.

    Returns:
        bool: True if the value is truthy, False otherwise.
    """
    if not value:
        return False

    return value.lower() in TRUTHY


def is_falsy(value: str | None) -> bool:
    """
    Checks if a value is falsy.

    Args:
        value (str): Value to check.

    Returns:
        bool: True if the value is falsy, False otherwise.
    """
    if not value:
        return True

    return value.lower() in FALSY


def import_module_from_path(module_name: str, module_path: str) -> Any:
    """
    Import a module from a given file path.

    Args:
        module_name (str): Name of the module.
        module_path (str): Path to the module file.

    Returns:
        Any: Imported module.

    Raises:
        ModuleImportException: If there is an error importing the module.
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        raise ModuleImportError(module_name, module_path, str(e)) from e

    return module


def is_nornir_task(attr: Any) -> bool:
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
        returns_result = annotations.get("return") in {Result, MultiResult, AggregatedResult}
        return has_task_param and returns_result
    return False