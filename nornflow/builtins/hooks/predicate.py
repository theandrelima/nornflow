import logging
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from nornir.core.inventory import Host
from nornir.core.task import Result, Task

from nornflow.hooks import Hook, register_hook
from nornflow.hooks.exceptions import HookValidationError

if TYPE_CHECKING:
    from nornflow.models import TaskModel

logger = logging.getLogger(__name__)


def skip_if_predicate_flagged(task_func: Callable) -> Callable:
    """
    Decorator that checks for the 'nornflow_skip_flag' in host.data before executing the task.
    
    If the flag is set to True, returns a skipped Result without executing the original task.
    Otherwise, executes the original task normally.
    
    This decorator is applied dynamically by PredicateHook when predicates are configured,
    allowing conditional task execution per host without global overhead.
    
    Args:
        task_func: The original Nornir task function to wrap.
        
    Returns:
        Wrapped function that checks the skip flag before execution.
    """
    @wraps(task_func)
    def wrapper(task: Task) -> Result:
        if task.host.data.get('nornflow_skip_flag', False):
            # Clean up the flag after use to avoid stale state
            task.host.data.pop('nornflow_skip_flag', None)
            return Result(
                host=task.host,
                result=None,
                changed=False,
                failed=False,
                skipped=True,
            )
        return task_func(task)
    
    return wrapper


@register_hook
class PredicateHook(Hook):
    """Conditionally execute tasks per host based on filter predicates.

    This hook evaluates a filter predicate for each host before task execution.
    The predicate is specified as a single-entry dict where the outer-most key is
    a nornir filter function name that must be registered in the the filters catalog,
    and the value contains that filter function parameters.

    If the filter returns False for a host, the hook sets a skip flag on the host
    that the task wrapper checks before execution.

    Filter Value Formats can be provided in three formats:
        1. Dict (keyword arguments):
           predicate:
             platform_and_version: {platform: 'ios', version: '15.0'}

        2. List (positional arguments, mapped to filter's parameter names):
           predicate:
             location: ['dc1', 'rack5']

        3. Single value (single positional argument):
           predicate:
             is_production: true

    Filter Functions:
        Filter functions must be registered in the filters catalog and should
        accept a Host object as the first parameter, followed by any custom
        parameters. They must return a boolean:
        - True: Host passes the predicate, task will execute
        - False: Host fails the predicate, task will be skipped

    Filter Catalog Integration:
        The hook retrieves filter functions from the filters_catalog in the
        execution context. This catalog contains both built-in NornFlow filters
        and user-defined custom filters discovered from local_filters_dirs.

    Error Handling:
        - HookValidationError: Raised during validation if predicate config is invalid

    Attributes:
        hook_name: "predicate"
        run_once_per_task: False (evaluates independently for each host)
    """

    hook_name = "predicate"
    run_once_per_task = False

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Validate predicate configuration during task preparation."""
        if not isinstance(self.value, dict):
            raise HookValidationError(
                "PredicateHook",
                [("value_type", "predicate value must be a dict with filter_name as key")]
            )

        if len(self.value) != 1:
            raise HookValidationError(
                "PredicateHook",
                [("value_count", "predicate must specify exactly one filter")]
            )

    def task_started(self, task: Task) -> None:
        """Dynamically decorate the task function to enable per-host skipping."""
        if not self.value:
            return
        
        # Apply the skip decorator dynamically to the task function
        # This ensures the decorated version is executed instead of the original
        original_func = task.task
        task.task = skip_if_predicate_flagged(original_func)
        
        logger.debug(f"Applied skip decorator to task '{task.name}' for predicate evaluation")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Evaluate the filter predicate and set skip flag if needed."""
        if self.value is None:
            return

        filter_name, filter_values = next(iter(self.value.items()))
        filters_catalog = self.context.get("filters_catalog", {})

        if filter_name not in filters_catalog:
            available = ', '.join(sorted(filters_catalog.keys()))
            raise HookValidationError(
                "PredicateHook",
                [(filter_name, f"Filter '{filter_name}' not found in filters catalog. "
                              f"Available filters: {available}")]
            )

        filter_func, param_names = filters_catalog[filter_name]
        filter_kwargs = self._build_filter_kwargs(param_names, filter_values)

        if not filter_func(host, **filter_kwargs):
            host.data['nornflow_skip_flag'] = True

    def _build_filter_kwargs(
        self,
        param_names: list[str],
        filter_values: Any
    ) -> dict[str, Any]:
        """Build keyword arguments for the filter function based on value format."""
        if isinstance(filter_values, dict):
            return filter_values

        if isinstance(filter_values, list):
            if len(param_names) == 1:
                return {param_names[0]: filter_values}
            if len(filter_values) != len(param_names):
                raise HookValidationError(
                    "PredicateHook",
                    [("param_count", f"Filter expects {len(param_names)} parameters, "
                                   f"got {len(filter_values)}")]
                )
            return dict(zip(param_names, filter_values, strict=False))

        if len(param_names) != 1:
            raise HookValidationError(
                "PredicateHook",
                [("param_count", f"Filter expects {len(param_names)} parameters, got 1")]
            )
        return {param_names[0]: filter_values}