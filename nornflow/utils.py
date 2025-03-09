import inspect
import importlib
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

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


def resolve_special_filter(
    key: str, 
    filter_values: Any,
    filter_module_name: str = 'nornflow.inventory_filters'
) -> Optional[dict[str, Any]]:
    """
    Resolve a filter key to a filter function and arguments according to Nornir conventions.
    
    Uses the convention that for a key 'x', there should be a function 
    named 'filter_by_x' in the specified module that can be used as a filter function.
    
    Important assumptions:
    - Filter functions should follow Nornir's standard pattern of exactly 2 parameters
    - First parameter must be 'host' (representing a Nornir Host object)
    - Second parameter receives the filter_values and should match the filter key semantically
    
    Args:
        key: The filter key name (e.g., 'hosts', 'groups')
        filter_values: The values to filter by (typically a list)
        filter_module_name: Name of module containing filter functions
        
    Returns:
        dict: Filter kwargs including 'filter_func' and appropriate parameters,
             or None if the filter function couldn't be resolved
    """
    # Use convention: filter_by_{key} should be the function name
    filter_func_name = f"filter_by_{key}"
    
    try:
        # Import the inventory filters module
        filters_module = importlib.import_module(filter_module_name)
        
        # Check if the function exists in the module
        if hasattr(filters_module, filter_func_name):
            filter_func = getattr(filters_module, filter_func_name)
            
            # Use the function's parameter names to determine the correct kwarg name
            sig = inspect.signature(filter_func)
            # Get the second parameter name (first is 'host', second should be our filter parameter)
            param_names = list(sig.parameters.keys())
            
            if len(param_names) >= 2:
                kwarg_name = param_names[1]  # Second parameter
                return {"filter_func": filter_func, kwarg_name: filter_values}
            else:
                # Fallback - use the key name as the kwarg name
                return {"filter_func": filter_func, key: filter_values}

    except (ImportError, AttributeError):
        pass
        
    return None


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
