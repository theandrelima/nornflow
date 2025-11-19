import logging
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

from nornir.core.inventory import Host
from nornir.core.task import Result, Task

from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookValidationError

if TYPE_CHECKING:
    from nornflow.models import TaskModel

logger = logging.getLogger(__name__)


def skip_if_condition_flagged(task_func: Callable) -> Callable:
    """
    Decorator that checks for the 'nornflow_skip_flag' in host.data before executing the task.

    If the flag is set to True, returns a skipped Result without executing the original task.
    Otherwise, executes the original task normally.

    This decorator is applied dynamically by IfHook when conditions are configured,
    allowing conditional task execution per host without global overhead.

    Args:
        task_func: The original Nornir task function to wrap.

    Returns:
        Wrapped function that checks the skip flag before execution.
    """

    @wraps(task_func)
    def wrapper(task: Task) -> Result:
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
        return task_func(task)

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

    Filter Functions:
        Filter functions must be registered in the filters catalog and should
        accept a Host object as the first parameter, followed by any custom
        parameters. They must return a boolean:
        - True: Host passes the condition, task will execute
        - False: Host fails the condition, task will be skipped

    Jinja2 Expressions:
        Expressions are resolved using NornFlow's variable system and must
        evaluate to a boolean value. Have access to:
        - host.* namespace (Nornir inventory data)
        - All NornFlow variables (runtime, CLI, inline, domain, default, env)
        - Jinja2 filters and functions

    Attributes:
        hook_name: "if"
        run_once_per_task: False (evaluates independently for each host)
    """

    hook_name = "if"
    run_once_per_task = False

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Validate condition configuration during task preparation."""
        super().execute_hook_validations(task_model)

        if isinstance(self.value, dict):
            # Filter function validation
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
        """Dynamically decorate the task function to enable per-host skipping."""
        # here we really need to check for 'None' specifically to not
        # return (and don't skip) when a falsy value is statically passed
        if self.value is None:
            return

        # Apply the skip decorator dynamically to the task function
        # This ensures the decorated version is executed instead of the original
        original_func = task.task
        task.task = skip_if_condition_flagged(original_func)

        logger.debug(f"Applied skip decorator to task '{task.name}' for condition evaluation")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Evaluate the filter condition and set skip flag if needed."""
        if self.value is None:
            return

        try:
            should_skip = False

            if isinstance(self.value, dict):
                # Filter function evaluation
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
