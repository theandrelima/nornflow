"""
NornFlow Single-Host Execution Hook

This module implements the SingleHook, which restricts a task to execute on
exactly one host from the inventory. All other hosts are silently skipped —
they produce no output and are excluded from all execution statistics.

Host Selection
==============

The hook designates the first host whose task_instance_started fires as the
delegate. All subsequent hosts receive an nornflow_silent_skip_flag, causing
the decorator to short-circuit with a silent skip Result.

Thread safety is ensured via a threading lock around the delegate assignment,
since task_instance_started can be called concurrently from multiple threads.

No explicit failed-host filtering is needed. Nornir's failure strategy
(via NornFlowFailureStrategyProcessor) already ensures that only valid,
non-failed hosts reach task_instance_started.

Mutual Exclusion
================

The single hook cannot be combined with the if hook on the same task.
This is validated during workflow preparation.
"""

import threading
from collections.abc import Callable
from functools import wraps
from typing import Any, TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, Result, Task

from nornflow.builtins.constants import SILENT_SKIP_FLAG
from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookValidationError
from nornflow.logger import logger

if TYPE_CHECKING:
    from nornflow.models import TaskModel


def skip_if_silent_flagged(task_func: Callable) -> Callable:
    """Decorator that silently skips task execution for flagged hosts.

    Checks for nornflow_silent_skip_flag on the host's data. If present,
    returns a Result with skipped=True without executing the actual task
    function.
    """

    @wraps(task_func)
    def wrapper(task: Task, **kwargs: Any) -> Result:
        if task.host.data.get(SILENT_SKIP_FLAG, False):
            return Result(
                host=task.host,
                result=None,
                changed=False,
                failed=False,
                skipped=True,
            )

        return task_func(task, **kwargs)

    return wrapper


class SingleHook(Hook, Jinja2ResolvableMixin):
    """Restrict task execution to a single host from the inventory.

    When enabled, the task runs on exactly one host. All other hosts are
    silently skipped — no output printed, no statistics counted.

    Supported values:
        - Boolean: true/false for static control
        - Jinja2 expression: Dynamic resolution to boolean
        - None: No effect (default)

    Cannot be combined with the 'if' hook on the same task.

    Example:
        - task: gather_global_config
          single: true

        - task: conditional_single
          single: "{{ run_as_single }}"

    Attributes:
        hook_name: "single"
        run_once_per_task: False (needs task_instance_started per host)
    """

    hook_name = "single"
    run_once_per_task = False

    def __init__(self, value: Any = None):
        super().__init__(value)
        self._delegate_host: str | None = None
        self._lock = threading.Lock()
        self._active = False

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Validate hook configuration and mutual exclusion with 'if' hook.

        Args:
            task_model: The task model to validate against.

        Raises:
            HookValidationError: If validation fails.
        """
        super().execute_hook_validations(task_model)

        if not isinstance(self.value, bool) and isinstance(self.value, (dict, list, int, float)):
            raise HookValidationError(
                "SingleHook",
                [
                    (
                        "invalid_value_type",
                        f"Task '{task_model.name}': single value must be a boolean or "
                        f"Jinja2 expression string, got {type(self.value).__name__}",
                    )
                ],
            )

        if isinstance(self.value, str) and not self.value.strip():
            raise HookValidationError(
                "SingleHook",
                [("empty_string", f"Task '{task_model.name}': single value cannot be an empty string")],
            )

        if hasattr(task_model, "hooks") and task_model.hooks:
            hook_keys = set()
            if isinstance(task_model.hooks, dict):
                hook_keys = set(task_model.hooks.keys())
            if "if" in hook_keys:
                raise HookValidationError(
                    "SingleHook",
                    [
                        (
                            "mutual_exclusion",
                            f"Task '{task_model.name}': 'single' and 'if' hooks cannot be "
                            f"used on the same task. Use Jinja2 expressions in 'single' for "
                            f"conditional single-host execution.",
                        )
                    ],
                )

    def task_started(self, task: Task) -> None:
        """Resolve value and apply skip decorator if single-host mode is active.

        Args:
            task: The task that is starting.
        """
        should_activate = self.get_resolved_value(task, host=None, as_bool=True, default=False)

        if not should_activate:
            self._active = False
            return

        self._active = True
        self._delegate_host = None

        original_func = task.task
        task.task = skip_if_silent_flagged(original_func)

        logger.debug(f"Applied single-host decorator to task '{task.name}'")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Designate delegate host or flag others for silent skip.

        Args:
            task: The task about to execute.
            host: The host it will execute on.
        """
        if not self._active:
            return

        with self._lock:
            if not self._delegate_host:
                self._delegate_host = host.name
                logger.debug(f"Host '{host.name}' designated as delegate for task '{task.name}'")
                return

        host.data[SILENT_SKIP_FLAG] = True

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Reset delegate state and clean up skip flags after task completes.

        Clears SILENT_SKIP_FLAG from all hosts to prevent stale flags
        when running without DefaultNornFlowProcessor (custom processor chains).

        Args:
            task: The task that completed.
            result: Aggregated results from all hosts.
        """
        if self._active:
            for host in task.nornir.inventory.hosts.values():
                host.data.pop(SILENT_SKIP_FLAG, None)

        self._delegate_host = None
        self._active = False
