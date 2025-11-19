# ruff: noqa: SLF001, T201
from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookValidationError


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

    def task_started(self, task: "Task") -> None:
        """Mark task for output suppression if conditions are met.

        Args:
            task: The Nornir task
        """
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
        task.nornir._nornflow_suppressed_tasks.add(task.name)

    def task_completed(self, task: "Task", result: "AggregatedResult") -> None:
        """Remove task from suppression set after completion.

        Args:
            task: The Nornir task
            result: The aggregated result
        """
        if hasattr(task.nornir, "_nornflow_suppressed_tasks"):
            task.nornir._nornflow_suppressed_tasks.discard(task.name)

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Validate shush hook configuration.

        Args:
            task_model: The task model being validated

        Raises:
            HookValidationError: If string value lacks Jinja2 markers
        """
        if isinstance(self.value, str) and not self._is_jinja2_expression(self.value):
            raise HookValidationError(
                hook_class=self.hook_name,
                errors=[
                    (
                        "value",
                        f"Task '{task_model.name}': 'shush' hook received string value "
                        f"'{self.value}' without Jinja2 markers. Use boolean values "
                        f"(true/false) or Jinja2 expressions (e.g., '{{{{ condition }}}}')",
                    )
                ],
            )
