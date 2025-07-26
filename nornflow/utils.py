import importlib
import inspect
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from pydantic_serdes.custom_collections import HashableDict

from nornflow.constants import JINJA_PATTERN
from nornflow.exceptions import ModuleImportError, ProcessorError


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
    Check if a function is a Nornir task based on its type annotations.

    Strict criteria (all must be met):
    - Must be callable
    - Must have type annotations
    - At least one parameter must be annotated as Task from nornir.core.task
    - Return type must be explicitly annotated as one of:
      - Result
      - MultiResult
      - AggregatedResult

    Args:
        attr (Callable): Attribute to check.

    Returns:
        bool: True if the attribute is a properly annotated Nornir task, False otherwise.
    """
    if callable(attr) and hasattr(attr, "__annotations__"):
        annotations = attr.__annotations__
        has_task_param = any(param == Task for param in annotations.values())
        returns_result = annotations.get("return") in {Result, MultiResult, AggregatedResult}
        return has_task_param and returns_result
    return False


def is_nornir_filter(attr: Callable) -> bool:  # noqa: PLR0911
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
        if return_type_annotation is bool:
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


def load_processor(processor_config: dict) -> Processor:
    """
    Dynamically load and instantiate a processor from config.

    Args:
        processor_config: Dict with class and args keys

    Returns:
        Instantiated processor

    Raises:
        ProcessorError: If processor cannot be loaded or instantiated
    """
    try:
        dotted_path = processor_config.get("class")
        if not dotted_path:
            raise ProcessorError("Missing class in processor configuration")

        args = processor_config.get("args", {})

        # Split the dotted path into module and class
        module_path, class_name = dotted_path.rsplit(".", 1)

        # Import the module
        module = importlib.import_module(module_path)

        # Get the class
        processor_class = getattr(module, class_name)

        # Instantiate the processor
        return processor_class(**args)
    except (ImportError, AttributeError) as e:
        raise ProcessorError(f"Failed to load processor {dotted_path}: {e!s}") from e
    except Exception as e:
        raise ProcessorError(f"Error instantiating processor {dotted_path}: {e!s}") from e


def convert_lists_to_tuples(dictionary: HashableDict[str, Any] | None) -> HashableDict[str, Any] | None:
    """
    Convert any lists in dictionary values to tuples for serialization.

    This is a common operation needed for HashableDict fields in models
    to ensure they can be properly serialized.

    Args:
        dictionary (HashableDict[str, Any] | None): The dictionary to process.

    Returns:
        HashableDict[str, Any] | None: A new HashableDict with lists converted to tuples,
                                      or None if input was None.
    """
    if dictionary is None:
        return None

    return HashableDict(
        {key: tuple(value) if isinstance(value, list) else value for key, value in dictionary.items()}
    )


def discover_items_in_dir(dir_path: str, register_func: Callable, error_context: str) -> None:
    """
    Discover and register items from Python modules in a directory.

    Args:
        dir_path: Path to the directory to scan
        register_func: Function to call for each module found
        error_context: Context for error messages (e.g., "tasks", "filters")

    Raises:
        DirectoryNotFoundError: If directory doesn't exist
        ModuleImportError: If module import fails
    """
    from nornflow.exceptions import DirectoryNotFoundError

    path = Path(dir_path)
    if not path.is_dir():
        raise DirectoryNotFoundError(directory=dir_path, extra_message=f"Couldn't load {error_context}.")

    for py_file in path.rglob("*.py"):
        module_name = py_file.stem
        module_path = str(py_file)
        try:
            module = import_module_from_path(module_name, module_path)
            register_func(module)
        except Exception as e:
            raise ModuleImportError(module_name, module_path, str(e)) from e


def process_module_attributes(module: Any, predicate_func: Callable, process_func: Callable) -> None:
    """
    Process module attributes that match a predicate function.

    Args:
        module: Module to process
        predicate_func: Function that determines if an attribute should be processed
        process_func: Function that processes the attribute
    """
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if predicate_func(attr):
            process_func(attr_name, attr)


def check_for_jinja2_recursive(obj: Any, path: str) -> None:
    """
    Recursively check for Jinja2 code in nested structures.

    Args:
        obj: Object to check (can be dict, list, string, etc.)
        path: Current path in the object structure (for error messages)

    Raises:
        ValueError: If Jinja2 code is found
    """
    if isinstance(obj, str):
        if JINJA_PATTERN.search(obj):
            raise ValueError(
                f"Jinja2 code found in '{path}' which is not allowed. "
                "Jinja2 expressions are only permitted in specific fields like task args."
            )
    elif isinstance(obj, dict):
        for key, value in obj.items():
            check_for_jinja2_recursive(value, f"{path}.{key}")
    elif isinstance(obj, list | tuple):
        for idx, item in enumerate(obj):
            check_for_jinja2_recursive(item, f"{path}[{idx}]")
