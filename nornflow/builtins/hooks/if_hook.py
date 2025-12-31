"""
NornFlow Conditional Execution Hook

This module implements the IfHook, which provides conditional task execution based on
filter functions or Jinja2 expressions.

Deferred Template Processing
===========================

The IfHook uses NornFlow's hook-driven template resolution system by declaring:
    requires_deferred_templates = True

This enables two-phase processing:
1. **Phase 1**: Evaluate conditions using variable context (templates not yet resolved)
2. **Phase 2**: Resolve templates just-in-time only for hosts that pass conditions

This prevents template resolution errors for hosts that would be skipped anyway,
enabling robust conditional workflows with variables that may not exist on all hosts.

Example:
    Task with "{{ some_var }}" parameter and if: hosts=['host1']
    - host1: has 'some_var', passes condition → template resolved → task executes
    - host2: missing 'some_var', fails condition → skipped, no template resolution
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import Result, Task

from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookValidationError

if TYPE_CHECKING:
    from nornflow.models import TaskModel

logger = logging.getLogger(__name__)


def skip_if_condition_flagged(task_func: Callable) -> Callable:
    """Decorator that implements deferred template resolution for conditional execution.

    Checks for skip flag and resolves templates just-in-time for non-skipped hosts.
    """

    @wraps(task_func)
    def wrapper(task: Task, **kwargs: Any) -> Result:
        if task.host.data.get("nornflow_skip_flag", False):
            # Clean up the flag after use to avoid stale state
            task.host.data.pop("nornflow_skip_flag", None)
            return Result(
                host=task.host,
                result=None,
                changed=False,
                failed=False,
                skipped=True,
            )

        resolved_kwargs = kwargs
        for processor in task.nornir.processors:
            if hasattr(processor, "resolve_deferred_params"):
                resolved = processor.resolve_deferred_params(task, task.host)
                # Use resolved params if deferred mode was active
                # otherwise fall back to original kwargs
                if resolved is not None:
                    resolved_kwargs = resolved
                break

        return task_func(task, **resolved_kwargs)

    return wrapper


class IfHook(Hook, Jinja2ResolvableMixin):
    """Conditionally execute tasks per host based on filter functions or Jinja2 expressions.

    This hook evaluates a condition for each host before task execution.
    Supports two condition types:

    1. Filter Functions: Dict-based configuration using registered filter functions
    2. Jinja2 Expressions: String-based boolean expressions evaluated per host

    Boolean Semantics (Python-style):
        - True (or truthy): Task EXECUTES for the host
        - False (or falsy): Task SKIPS for the host

    This follows Python's standard truthiness rules where True means "proceed"
    and False means "don't proceed".

    Filter Function Format:
        if:
          filter_name: {param1: value1, param2: value2}
        # OR
        if:
          filter_name: [value1, value2]  # positional args
        # OR
        if:
          filter_name: single_value  # single arg

    Jinja2 Expression Format:
        if: "{{ host.platform == 'ios' and host.data.site == 'dc1' }}"
        # OR
        if: "{{ some_variable | default(false) }}"
        # OR
        if: false

    Attributes:
        hook_name: "if"
        run_once_per_task: False (evaluates independently for each host)
        requires_deferred_templates: True (enables two-phase template processing)
    """

    hook_name = "if"
    run_once_per_task = False
    requires_deferred_templates = True

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Validate condition configuration during task preparation."""
        super().execute_hook_validations(task_model)

        if isinstance(self.value, dict):
            if len(self.value) != 1:
                raise HookValidationError("IfHook", [("value_count", "if must specify exactly one filter")])
        elif isinstance(self.value, str):
            if not self.value.strip():
                raise HookValidationError(
                    "IfHook", [("empty_string", f"Task '{task_model.name}': if value cannot be empty string")]
                )
        elif self.value is not None:
            raise HookValidationError(
                "IfHook",
                [("value_type", "if value must be a dict (Nornir filter) or string (Jinja2 expression)")],
            )

    def task_started(self, task: Task) -> None:
        """Apply skip decorator to enable per-host conditional execution."""
        if self.value is None:
            return

        # Apply the skip decorator dynamically to the task function
        # This ensures the decorated version is executed instead of the original
        original_func = task.task
        task.task = skip_if_condition_flagged(original_func)

        logger.debug(f"Applied skip decorator to task '{task.name}' for condition evaluation")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Evaluate condition and set skip flag for hosts that fail."""
        if self.value is None:
            return

        try:
            should_skip = False

            if isinstance(self.value, dict):
                should_skip = not self._evaluate_filter_condition(host)
            else:
                condition = self.get_resolved_value(task, host=host, as_bool=True, default=True)
                should_skip = not condition

            if should_skip:
                host.data["nornflow_skip_flag"] = True

        except Exception as e:
            logger.error(f"Error evaluating if condition for host '{host.name}': {e}")
            raise HookValidationError(
                "IfHook", [("evaluation_error", f"Failed to evaluate condition: {e}")]
            ) from e

    def _evaluate_filter_condition(self, host: Host) -> bool:
        """Evaluate filter-based condition for the host."""
        filter_name, filter_values = next(iter(self.value.items()))
        filters_catalog = self.context.get("filters_catalog", {})

        if filter_name not in filters_catalog:
            available = ", ".join(sorted(filters_catalog.keys()))
            raise HookValidationError(
                "IfHook",
                [
                    (
                        filter_name,
                        f"Filter '{filter_name}' not found in filters catalog. "
                        f"Available filters: {available}",
                    )
                ],
            )

        filter_func, param_names = filters_catalog[filter_name]
        filter_kwargs = self._build_filter_kwargs(param_names, filter_values)

        return filter_func(host, **filter_kwargs)

    def _build_filter_kwargs(self, param_names: list[str], filter_values: Any) -> dict[str, Any]:
        """Build keyword arguments for the filter function based on value format."""
        if isinstance(filter_values, dict):
            return filter_values

        if isinstance(filter_values, list):
            if len(param_names) == 1:
                return {param_names[0]: filter_values}
            if len(filter_values) != len(param_names):
                raise HookValidationError(
                    "IfHook",
                    [
                        (
                            "param_count",
                            f"Filter expects {len(param_names)} parameters, got {len(filter_values)}",
                        )
                    ],
                )
            return dict(zip(param_names, filter_values, strict=False))

        if len(param_names) != 1:
            raise HookValidationError(
                "IfHook", [("param_count", f"Filter expects {len(param_names)} parameters, got 1")]
            )
        return {param_names[0]: filter_values}
