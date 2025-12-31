import hashlib
import importlib
import inspect
import logging
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import yaml
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
    ResourceError,
    WorkflowError,
)

logger = logging.getLogger(__name__)

TYPE_DISPLAY_MAPPING: dict[str, str] = {
    "HashableDict": "map",
    "dict": "map",
    "list": "seq",
    "tuple": "seq",
    "NoneType": "none",
}

NORNIR_RESULT_TYPES: set[type] = {Result, MultiResult, AggregatedResult}


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


def import_module_from_path(module_name: str, module_path: str | Path) -> ModuleType:
    """
    Import a module from a given file path.

    Args:
        module_name: Name to assign to the module.
        module_path: Path to the module file.

    Returns:
        Imported module.

    Raises:
        CoreError: If there is an error importing the module.
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(module_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        raise CoreError(
            f"Failed to import module '{module_name}' from '{module_path}': {e!s}",
            component="ModuleLoader",
        ) from e


def _generate_module_name(py_file: Path, cwd: Path) -> str:
    """
    Generate a module name from a Python file path.

    Tries to create a relative dotted path from CWD first. Falls back to a
    hash-based unique name if the file is outside CWD.

    Args:
        py_file: Resolved absolute path to the Python file.
        cwd: Resolved current working directory.

    Returns:
        A valid Python module name.
    """
    try:
        relative_path = py_file.relative_to(cwd)
        parts = relative_path.with_suffix("").parts
        return ".".join(p for p in parts if p)
    except ValueError:
        return f"hook_{py_file.stem}_{abs(hash(str(py_file))) % 100000}"


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
    dir_path = dir_path.resolve()
    cwd = Path.cwd().resolve()

    for py_file in dir_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        py_file = py_file.resolve()
        module_name = _generate_module_name(py_file, cwd)

        try:
            try:
                importlib.import_module(module_name)
            except ImportError:
                import_module_from_path(module_name, py_file)
            imported_modules.append(module_name)
            logger.debug(f"Imported module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to import module {py_file}: {e}")

    return imported_modules


def is_nornir_task(attr: Callable) -> bool:
    """
    Check if a function is a Nornir task based on its type annotations.

    Strict criteria (all must be met):
    - Must be callable with type annotations
    - At least one parameter must be annotated as Task
    - Return type must be Result, MultiResult, or AggregatedResult

    Args:
        attr: Attribute to check.

    Returns:
        True if the attribute is a properly annotated Nornir task.
    """
    if not callable(attr) or not hasattr(attr, "__annotations__"):
        return False

    annotations = attr.__annotations__
    has_task_param = any(param == Task for param in annotations.values())
    returns_result = annotations.get("return") in NORNIR_RESULT_TYPES
    return has_task_param and returns_result


def _is_boolean_return_type(annotation: Any) -> bool:
    """
    Check if a return type annotation represents a boolean.

    Args:
        annotation: The return type annotation to check.

    Returns:
        True if the annotation is bool or Literal[True/False].
    """
    if annotation is bool:
        return True

    if hasattr(annotation, "__origin__") and annotation.__origin__ is Literal:
        args = getattr(annotation, "__args__", ())
        return set(args) <= {True, False}

    return False


def is_nornir_filter(attr: Callable) -> bool:
    """
    Check if a function is a Nornir inventory filter function.

    Strict criteria (all must be met):
    - Must be callable
    - First parameter MUST be annotated as Host
    - Return type MUST be bool or Literal[True, False]

    Args:
        attr: Attribute to check.

    Returns:
        True if the attribute is a properly annotated Nornir filter.
    """
    if not callable(attr):
        return False

    try:
        sig = inspect.signature(attr)
        params = list(sig.parameters.values())

        if not params or params[0].annotation != Host:
            return False

        return _is_boolean_return_type(sig.return_annotation)
    except (ValueError, TypeError):
        return False


def process_filter(attr: Callable) -> tuple[Callable, list[str]]:
    """
    Process a filter function to extract its parameters.

    Args:
        attr: The filter function to process.

    Returns:
        Tuple of (filter_function, parameter_names excluding 'host').
    """
    sig = inspect.signature(attr)
    param_names = list(sig.parameters.keys())[1:]
    return (attr, param_names)


def is_yaml_file(file_path: str | Path) -> bool:
    """
    Check if a file is a valid NornFlow workflow file.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the file is a workflow file.
    """
    path = Path(file_path)
    return path.is_file() and path.suffix in NORNFLOW_SUPPORTED_YAML_EXTENSIONS


def load_processor(processor_config: dict) -> Processor:
    """
    Dynamically load and instantiate a processor from config.

    Args:
        processor_config: Dict with 'class' (dotted path) and optional 'args'.

    Returns:
        Instantiated processor.

    Raises:
        ProcessorError: If processor cannot be loaded or instantiated.
    """
    dotted_path = processor_config.get("class")
    if not dotted_path:
        raise ProcessorError("Missing 'class' in processor configuration")

    args = processor_config.get("args", {})

    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        processor_class = getattr(module, class_name)
        return processor_class(**args)
    except (ImportError, AttributeError) as e:
        raise ProcessorError(f"Failed to load processor '{dotted_path}': {e!s}") from e
    except Exception as e:
        raise ProcessorError(f"Error instantiating processor '{dotted_path}': {e!s}") from e


def convert_lists_to_tuples(dictionary: HashableDict[str, Any] | None) -> HashableDict[str, Any] | None:
    """
    Convert any lists in dictionary values to tuples for serialization.

    Args:
        dictionary: The dictionary to process.

    Returns:
        A new HashableDict with lists converted to tuples, or None if input was None.
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
        obj: Object to check (dict, list, string, etc.)
        path: Current path in the object structure for error messages.

    Raises:
        WorkflowError: If Jinja2 code is found in a disallowed location.
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
    Format a variable value for display, masking protected keywords.

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


def _get_type_display(value: Any) -> str:
    """Get display name for a value's type."""
    type_name = type(value).__name__
    return TYPE_DISPLAY_MAPPING.get(type_name, type_name)


def _add_vars_to_table(
    table: Table,
    vars_dict: dict[str, Any],
    source_label: str,
) -> None:
    """
    Add variables to a Rich table with consistent formatting.

    Args:
        table: The Rich Table to add rows to.
        vars_dict: Dictionary of variable name -> value.
        source_label: Label for the source column (e.g., 'w', 'c*').
    """
    for key, value in sorted(vars_dict.items(), key=lambda item: item[0]):
        table.add_row(
            source_label,
            key,
            format_variable_value(key, value),
            _get_type_display(value),
        )


def _build_vars_section(workflow_vars: dict[str, Any], cli_vars: dict[str, Any]) -> list[Any]:
    """
    Build the variables section for the workflow overview panel.

    Args:
        workflow_vars: Variables defined in the workflow.
        cli_vars: Variables from CLI/programmatic override.

    Returns:
        List of Rich renderables for the vars section, or empty list if no vars.
    """
    if not workflow_vars and not cli_vars:
        return []

    vars_table = Table(show_header=True, box=None)
    vars_table.add_column("Source", style="bold magenta", no_wrap=True)
    vars_table.add_column("Name", style="cyan")
    vars_table.add_column("Value", style="yellow")
    vars_table.add_column("Type", style="blue", no_wrap=True)

    if workflow_vars:
        _add_vars_to_table(vars_table, workflow_vars, "w")
    if cli_vars:
        _add_vars_to_table(vars_table, cli_vars, "c*")

    legend_text = Text()
    legend_text.append("Sources", style="bold dim")
    legend_text.append("\nw: defined in workflow", style="dim")
    legend_text.append("\nc*: CLI/programmatic override", style="dim")

    return [
        Text("\n"),
        Padding.indent(Text("Variables", style="bold cyan"), 1),
        Padding.indent(Columns([vars_table, Align.right(legend_text)], expand=True), 2),
    ]


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
    Print a comprehensive workflow overview before execution using Rich.

    Args:
        workflow_model: The workflow model containing name and description.
        effective_dry_run: Whether dry-run mode is enabled.
        hosts_count: Number of hosts in the filtered inventory.
        inventory_filters: Dictionary of applied inventory filters.
        workflow_vars: Workflow-defined variables.
        vars: Vars with highest precedence (CLI/programmatic).
        failure_strategy: The active failure handling strategy.
    """
    console = Console()

    table = Table(show_header=False, box=None)
    table.add_column("Property", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="yellow")

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
        "Failure Strategy",
        failure_strategy.value.replace("_", "-") if failure_strategy else "None",
    )

    elements: list[Any] = [table]
    elements.extend(_build_vars_section(workflow_vars, vars))

    panel = Panel(
        Group(*elements),
        title=Text("Workflow Execution Overview", style="bold"),
        border_style="green",
        width=100,
    )

    console.print(panel)


def get_file_content_hash(file_path: Path) -> str:
    """
    Generate a stable hash from file content for identity comparison.

    Normalizes YAML content before hashing to ensure equivalent content
    produces the same hash regardless of formatting differences.

    Args:
        file_path: Path to the file to hash.

    Returns:
        A 16-character hex string representing the content hash.

    Raises:
        ResourceError: If file cannot be read or parsed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        normalized = yaml.dump(data, sort_keys=True, default_flow_style=False)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    except Exception as e:
        raise ResourceError(
            f"Failed to hash file content: {e}", resource_type="file", resource_name=str(file_path)
        ) from e
