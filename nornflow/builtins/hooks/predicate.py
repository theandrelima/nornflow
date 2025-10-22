from typing import TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Result, Task

from nornflow.hooks import Hook, register_hook
from nornflow.hooks.exceptions import HookError

if TYPE_CHECKING:
    from nornflow.models import TaskModel


class SkipHostError(HookError):
    """Exception raised by hooks to signal that a host should be skipped during execution.

    This exception is caught by NornFlowHookProcessor to mark the host as skipped
    instead of failed.
    """


@register_hook
class PredicateHook(Hook):
    """Hook that conditionally executes tasks per host based on a predicate function.

    This hook evaluates a predicate for each host in task_instance_started.
    If the predicate returns False, it raises SkipHostError to signal skipping,
    handled by the processor to mark the host as skipped.

    The predicate is a callable that takes (host: Host, context: dict) and returns bool.
    Context includes task_model, vars_manager, etc., for dynamic conditions.

    Attributes:
        hook_name: "predicate"
        run_once_per_task: False (evaluates per host)
    """

    hook_name = "predicate"
    run_once_per_task = False
    exception_handlers = {SkipHostError: "_handle_skip_host_error"}

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Evaluate the predicate and skip the host if it fails."""
        if self.value is None:
            return

        context = self.get_context(task)
        predicate_func = self.value

        if not predicate_func(host, context):
            raise SkipHostError(f"Predicate failed for host '{host.name}'")

    def _handle_skip_host_error(self, exception, task, args) -> None:
        """Handle SkipHostError by marking the host as skipped."""
        # Extract host from args (assuming it's in task_instance_* methods)
        host = None
        for arg in args:
            if isinstance(arg, Host):
                host = arg
                break
        
        if host:
            # Create a skipped MultiResult
            skipped_result = MultiResult(task.name)
            skipped_result.append(
                Result(
                    host=host,
                    result=None,
                    changed=False,
                    failed=False,
                    skipped=True,
                    exception=exception,
                )
            )
            # Note: initial implementation. For now, we log and assume 
            # the task function won't run for skipped hosts.
            print(f"Host '{host.name}' skipped by hook: {exception}")