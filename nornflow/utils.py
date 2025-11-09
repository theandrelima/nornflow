import importlib
import inspect
import logging
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from pydantic_serdes.custom_collections import HashableDict
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nornflow.constants import (
    FailureStrategy,
    JINJA_PATTERN,
    NORNFLOW_SUPPORTED_YAML_EXTENSIONS,
    PROTECTED_KEYWORDS,
)
from nornflow.exceptions import (
    CoreError,
    ProcessorError,
    WorkflowError,
)

logger = logging.getLogger(__name__)


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


def import_modules_recursively(dir_path: Path) -> list[str]:
    """
    Recursively import all Python modules under a directory.

    Finds all .py files in the directory and subdirectories, converts them to
    module names, and imports them. Skips __init__.py files. Logs errors for
    failed imports but continues with others.

    Args:
        dir_path: The root directory to search for modules.

    Returns:
        List of successfully imported module names.
    """
    imported_modules = []

    # Ensure we're working with resolved absolute paths to avoid path issues
    dir_path = dir_path.resolve()
    cwd = Path.cwd().resolve()

    for py_file in dir_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        py_file = py_file.resolve()

        try:
            # Try to calculate relative path from CWD first
            try:
                relative_path = py_file.relative_to(cwd)
                module_name = path_to_module_name(relative_path)
            except ValueError:
                # If file is outside CWD, create a unique module name
                module_name = f"hook_{py_file.stem}_{abs(hash(str(py_file))) % 100000}"

            # Try direct import first (if module is in sys.path)
            try:
                importlib.import_module(module_name)
                imported_modules.append(module_name)
                logger.debug(f"Imported module: {module_name}")
            except ImportError:
                # If direct import fails, try importing from file path
                import_module_from_path(module_name, str(py_file))
                imported_modules.append(module_name)
                logger.debug(f"Imported module from path: {module_name}")

        except Exception as e:
            logger.error(f"Failed to import module {py_file}: {e}")

    return imported_modules


def path_to_module_name(py_file: Path) -> str:
    """
    Convert a Python file path to a module name.

    Assumes the file is importable from the project root.

    Args:
        py_file: The Python file path.

    Returns:
        The module name as a dotted string.
    """
    # Remove .py extension and convert path parts to module name
    parts = py_file.with_suffix("").parts
    # Filter out any empty parts
    parts = [p for p in parts if p]
    return ".".join(parts)


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


def format_variable_value(key: str, value: Any) -> str:
    """
    Format a variable value for display, masking protected keywords and adjusting tuple brackets.

    Args:
        key: The variable name.
        value: The variable value.

    Returns:
        The formatted display string.
    """
    if any(keyword in key.lower() for keyword in PROTECTED_KEYWORDS):
        return "********"
    display_value = str(value)
    if isinstance(value, tuple):
        display_value = display_value.replace("(", "[").replace(")", "]")
    return display_value


def print_workflow_overview(
    workflow_model: Any,
    effective_dry_run: bool,
    hosts_count: int,
    inventory_filters: dict[str, Any],
    workflow_vars: dict[str, Any],
    vars: dict[str, Any],
    failure_strategy: FailureStrategy | None,
) -> None:
    """
    Print a comprehensive workflow overview before execution using Rich for enhanced formatting.

    Args:
        workflow_model: The workflow model containing name and description.
        effective_dry_run: Whether dry-run mode is enabled.
        hosts_count: Number of hosts in the filtered inventory.
        inventory_filters: Dictionary of applied inventory filters.
        workflow_vars: Workflow-defined variables.
        vars: Vars with highest precedence.
        failure_strategy: The active failure handling strategy.
    """
    type_mapping = {"HashableDict": "map", "dict": "map", "list": "seq", "tuple": "seq", "NoneType": "none"}

    console = Console()

    # Create a table for workflow details
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="yellow")

    # Add rows in the specified order, conditionally
    if workflow_model.name:
        table.add_row("Workflow Name", workflow_model.name)
    if workflow_model.description:
        table.add_row("Description", workflow_model.description)
    if inventory_filters:
        filters_str = ", ".join(f"{k}={v}" for k, v in inventory_filters.items())
        table.add_row("Inventory Filters", filters_str)
    table.add_row("Dry Run", "Yes" if effective_dry_run else "No")
    table.add_row("Hosts Count", str(hosts_count))
    table.add_row(
        "Failure Strategy", failure_strategy.value.replace("_", "-") if failure_strategy else "None"
    )

    # Prepare vars table if any vars exist
    elements = [table]
    if vars or workflow_vars:
        elements.append(Text("\n"))  # Blank space before variables
        elements.append(Padding.indent(Text("Variables", style="bold cyan"), 1))
        vars_table = Table(show_header=True, box=None)
        vars_table.add_column("Source", style="bold magenta", no_wrap=True)
        vars_table.add_column("Name", style="cyan")
        vars_table.add_column("Value", style="yellow")
        vars_table.add_column("Type", style="blue", no_wrap=True)

        if workflow_vars:
            # Sort workflow variables by name lexicographically
            for k, v in sorted(workflow_vars.items(), key=lambda item: item[0]):
                vars_table.add_row(
                    "w", k, format_variable_value(k, v), type_mapping.get(type(v).__name__, type(v).__name__)
                )
        if vars:
            # Sort CLI/programmatic variables by name lexicographically
            for k, v in sorted(vars.items(), key=lambda item: item[0]):
                vars_table.add_row(
                    "c*",
                    k,
                    format_variable_value(k, v),
                    type_mapping.get(type(v).__name__, type(v).__name__),
                )

        legend_text = Text()
        legend_text.append("Sources", style="bold dim")
        legend_text.append("\nw: defined in workflow", style="dim")
        legend_text.append("\nc*: CLI/programmatic override", style="dim")
        elements.append(Padding.indent(Columns([vars_table, Align.right(legend_text)], expand=True), 2))

    # Create a panel with the grouped elements
    panel = Panel(
        Group(*elements),
        title=Text("Workflow Execution Overview", style="bold"),
        border_style="green",
        width=100,
    )

    console.print(panel)
