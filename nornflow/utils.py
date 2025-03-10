import importlib
import inspect
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import yaml
from nornir.core.inventory import Host
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


def is_nornir_filter(attr: Callable) -> bool:
    """
    Check if an function is a Nornir inventory filter function.
    
    Strict criteria (all must be met):
    - Must be callable
    - First parameter MUST be explicitly annotated as Host from nornir.core.inventory
    - Return type MUST be explicitly annotated as either:
      - The built-in bool type
      - A typing.Literal containing only boolean values (True/False)
    
    This function enforces explicit type annotations to ensure filter functions
    follow a consistent pattern.
    
    Args:
        attr (Callable): Attribute to check.
        
    Returns:
        bool: True if the attribute is a properly annotated Nornir filter, False otherwise.
    """
    if not callable(attr):
        return False
        
    try:
        sig = inspect.signature(attr)
        params = list(sig.parameters.values())
        
        # Must have at least one parameter (host)
        if not params:
            return False
        
        # First parameter annotation must be Host
        if params[0].annotation != Host:
            return False
        
        # Check for various boolean-like return types
        return_type_annotation = sig.return_annotation
            
        # Check for built-in bool
        if return_type_annotation == bool:
            return True
        
        # Checking kind of an edge case here: typing.Literal with boolean values
        if hasattr(return_type_annotation, "__origin__") and return_type_annotation.__origin__ is Literal:
            args = getattr(return_type_annotation, "__args__", ())
            # If all args are True or False, it's a boolean Literal
            if set(args) <= {True, False}:
                return True
            
        return False

    except (ValueError, TypeError):
        return False
