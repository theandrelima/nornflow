# ruff: noqa: T201
import importlib
import inspect
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import click
from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from pydantic_serdes.custom_collections import HashableDict
from tabulate import tabulate

from nornflow.constants import FailureStrategy, JINJA_PATTERN, NORNFLOW_SUPPORTED_YAML_EXTENSIONS
from nornflow.exceptions import (
    CoreError,
    ProcessorError,
    WorkflowError,
)


def normalize_failure_strategy(
    value: str | FailureStrategy, exception_class: type[Exception]
) -> FailureStrategy:
    """
    Normalize and convert a failure strategy value to a FailureStrategy enum.

    Performs case-insensitive conversion from string to enum, with support for
    both underscore and hyphen variations.

    Args:
        value: The value to normalize (string or pre-validated enum).
        exception_class: The exception class to raise on invalid input.

    Returns:
        The normalized FailureStrategy enum.

    Raises:
        exception_class: If the value is invalid or of unsupported type.
    """
    if isinstance(value, FailureStrategy):
        return value
    if isinstance(value, str):
        # Try direct enum lookup (handles _missing_ method)
        try:
            return FailureStrategy(value)
        except ValueError as e:
            valid_options = [e.value for e in FailureStrategy]
            raise exception_class(
                f"Invalid failure strategy '{value}'. Valid options: {', '.join(valid_options)}"
            ) from e
    raise exception_class(
        f"Invalid failure strategy type '{type(value).__name__}'. Must be a string or FailureStrategy enum."
    )


def import_module_from_path(module_name: str, module_path: str) -> ModuleType:
    """
    Import a module from a given file path.

    Args:
        module_name (str): Name of the module.
        module_path (str): Path to the module file.

    Returns:
        ModuleType: Imported module.

    Raises:
        CoreError: If there is an error importing the module.
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        raise CoreError(
            f"Failed to import module '{module_name}' from '{module_path}': {e!s}",
            component="ModuleLoader",
        ) from e

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


def process_filter(attr: Callable) -> tuple[Callable, list[str]]:
    """
    Process a filter function to extract its parameters and return both the function and param info.

    This allows filter registration to capture parameter names for use in workflow definitions.

    Args:
        attr: The filter function to process

    Returns:
        Tuple containing (filter_function, parameter_names)
    """
    sig = inspect.signature(attr)
    # Skip the first parameter (host) and get remaining parameter names
    param_names = list(sig.parameters.keys())[1:]
    return (attr, param_names)


def is_workflow_file(file_path: str | Path) -> bool:
    """
    Check if a file is a valid NornFlow workflow file.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is a workflow file, False otherwise
    """
    path = Path(file_path)
    return path.is_file() and path.suffix in NORNFLOW_SUPPORTED_YAML_EXTENSIONS


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


def check_for_jinja2_recursive(obj: Any, path: str) -> None:
    """
    Recursively check for Jinja2 code in nested structures.

    Args:
        obj: Object to check (can be dict, list, string, etc.)
        path: Current path in the object structure (for error messages)

    Raises:
        WorkflowError: If Jinja2 code is found
    """
    if isinstance(obj, str):
        if JINJA_PATTERN.search(obj):
            raise WorkflowError(
                f"Jinja2 code found in '{path}' which is not allowed. "
                "Jinja2 expressions are only permitted in specific fields like task args."
            )
    elif isinstance(obj, dict):
        for key, value in obj.items():
            check_for_jinja2_recursive(value, f"{path}.{key}")
    elif isinstance(obj, list | tuple):
        for idx, item in enumerate(obj):
            check_for_jinja2_recursive(item, f"{path}[{idx}]")


def print_workflow_overview(
    workflow_model: Any,
    effective_dry_run: bool,
    hosts_count: int,
    inventory_filters: dict[str, Any],
    workflow_vars: dict[str, Any],
    cli_vars: dict[str, Any],
    failure_strategy: FailureStrategy | None,
) -> None:
    """
    Print a comprehensive workflow overview before execution.

    Args:
        workflow_model: The workflow model containing name and description
        effective_dry_run: Whether dry-run mode is enabled
        hosts_count: Number of hosts in the filtered inventory
        inventory_filters: Dictionary of applied inventory filters
        workflow_vars: Workflow-defined variables
        cli_vars: CLI variables with highest precedence
        failure_strategy: The active failure handling strategy
    """
    print("\n" + "━" * 80)
    click.secho(" Workflow: ", bold=True, nl=False)
    print(workflow_model.name)

    if workflow_model.description:
        click.secho(" Description: ", bold=True, nl=False)
        print(workflow_model.description)

    click.secho(" Dry-run mode: ", bold=True, nl=False)
    print("Enabled" if effective_dry_run else "Disabled")

    # Show inventory filters if any
    if inventory_filters:
        click.secho(" Inventory filters: ", bold=True, nl=False)
        print(inventory_filters)

    if failure_strategy:
        click.secho(" Failure strategy: ", bold=True, nl=False)
        print(failure_strategy.value)

    # Show filtered inventory overview
    click.secho(" Total hosts: ", bold=True, nl=False)
    print(f"{hosts_count} host(s)")

    # Show variables (excluding sensitive ones)
    all_vars = {}
    if workflow_vars:
        all_vars.update({"Workflow Variables": workflow_vars})
    if cli_vars:
        all_vars.update({"CLI Variables (highest precedence)": cli_vars})

    if all_vars:
        vars_table = []
        for var_type, var_dict in all_vars.items():
            vars_table.append([var_type, ""])
            for k, v in var_dict.items():
                # Mask passwords/secrets
                display_v = "********" if "password" in k.lower() or "secret" in k.lower() else str(v)
                vars_table.append([f"  {k}", display_v])

        if vars_table:
            print()
            click.secho(" Variables:", bold=True)
            print(tabulate(vars_table, tablefmt="simple"))

    print("━" * 80 + "\n")
