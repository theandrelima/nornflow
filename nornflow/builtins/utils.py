import json
from typing import Any

from nornir.core.task import Task

from nornflow.exceptions import ProcessorError
from nornflow.vars import NornFlowVariablesManager


def get_task_vars_manager(task: Task) -> NornFlowVariablesManager:
    """
    Find the NornFlowVariableProcessor in the task's processor chain and return its vars_manager.

    Args:
        task: The Nornir Task object.

    Returns:
        The vars_manager instance.

    Raises:
        VarsManagerNotFoundError: If no vars_manager is found in any processor.
    """
    for processor in task.nornir.processors:
        if hasattr(processor, "vars_manager"):
            return processor.vars_manager

    raise ProcessorError(
        "Could not find NornFlowVariableProcessor in the processor chain. "
        "NornFlow variable processing is not available for this task."
    )


def format_value_for_display(value: Any) -> str:
    """
    Format a value for display in the set task output.

    Args:
        value: The value to format.

    Returns:
        A formatted string representation of the value.
    """
    if isinstance(value, str):
        # For strings, show them with quotes
        return f'"{value}"'
    if isinstance(value, (dict | list)):
        # For complex structures, show the full JSON representation with 2-space indentation
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            # Fallback for non-JSON-serializable objects
            return str(value)
    else:
        # For other types (bool, int, float, etc.), show as-is
        return str(value)


def get_resolved_runtime_values(task: Task, var_names: list[str]) -> dict[str, Any]:
    """
    Get the resolved runtime variable values for the given variable names.

    Args:
        task: The Nornir Task object.
        var_names: List of variable names to retrieve.

    Returns:
        Dictionary mapping variable names to their resolved values.
        If a variable is not found, it maps to a special error message.
    """
    vars_manager = get_task_vars_manager(task)

    if not vars_manager:
        return {}

    device_context = vars_manager.get_device_context(task.host.name)
    resolved_values = {}

    for var_name in var_names:
        if var_name in device_context.runtime_vars:
            resolved_values[var_name] = device_context.runtime_vars[var_name]
        else:
            resolved_values[var_name] = "<value not found in runtime vars>"

    return resolved_values


def build_set_task_report(task: Task, kwargs: dict[str, Any]) -> str:
    """
    Build a detailed report of what variables were set and their resolved values.

    Args:
        task: The Nornir Task object.
        kwargs: The arguments passed to the set task.

    Returns:
        A formatted report string showing what variables were set.
    """
    if not kwargs:
        return "No variables were set (no arguments provided to 'set' task)"

    vars_manager = get_task_vars_manager(task)

    if not vars_manager:
        # Fallback: show unresolved values if we can't access the vars manager
        report_lines = [
            f"Set {len(kwargs)} variable(s) for host '{task.host.name}' (showing unresolved templates):"
        ]
        for var_name, var_value in kwargs.items():
            value_display = format_value_for_display(var_value)
            report_lines.append(f"  • {var_name} = {value_display}")
        return "\n".join(report_lines)

    # Get resolved values from runtime variables
    resolved_values = get_resolved_runtime_values(task, list(kwargs.keys()))

    # Build the report with resolved values
    report_lines = [f"Set {len(kwargs)} variable(s) for host '{task.host.name}':"]

    for var_name in kwargs:
        resolved_value = resolved_values.get(var_name, "<value not found>")
        value_display = format_value_for_display(resolved_value)
        report_lines.append(f"  • {var_name} = {value_display}")

    return "\n".join(report_lines)
