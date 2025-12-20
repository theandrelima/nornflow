# ruff: noqa: SLF001, T201
from nornir.core.task import AggregatedResult, Task

from nornflow.hooks import Hook, Jinja2ResolvableMixin


class ShushHook(Hook, Jinja2ResolvableMixin):
    """Hook to suppress task output printing.

    The shush hook allows conditional suppression of task output based on
    boolean values or Jinja2 expressions that evaluate to boolean.

    Supported values:
        - Boolean: True/False for static suppression control
        - Jinja2 expression: Dynamic suppression based on variables
        - None: No suppression (default)

    The hook works in conjunction with processors that support output
    suppression by marking tasks in a special set on the Nornir instance.
    """

    hook_name = "shush"
    run_once_per_task = True

    def task_started(self, task: Task) -> None:
        """Mark task for output suppression if conditions are met."""
        should_suppress = self.get_resolved_value(task, host=None, as_bool=True, default=False)

        if not should_suppress:
            return

        has_compatible_processor = any(
            getattr(proc, "supports_shush_hook", False) for proc in task.nornir.processors
        )

        if not has_compatible_processor:
            print(
                "Warning: 'shush' hook has no effect - "
                "no compatible processor found in chain. "
                "Outputs are not going to be suppressed."
            )
            return

        if not hasattr(task.nornir, "_nornflow_suppressed_tasks"):
            task.nornir._nornflow_suppressed_tasks = set()

        task_model = self.context.get("task_model")
        task.nornir._nornflow_suppressed_tasks.add(task_model.canonical_id)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Remove task from suppression set after completion."""
        if hasattr(task.nornir, "_nornflow_suppressed_tasks"):
            task_model = self.context.get("task_model")
            task.nornir._nornflow_suppressed_tasks.discard(task_model.canonical_id)
