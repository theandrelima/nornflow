# ruff: noqa: SLF001, T201
import re

from nornflow.hooks import Hook
from nornflow.hooks.exceptions import HookValidationError


class ShushHook(Hook):
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

    def __init__(self, value: bool | str | None = None):
        """Initialize the shush hook.

        Args:
            value: Boolean, Jinja2 expression string, or None
        """
        super().__init__(value)
        self.is_jinja2_expression = self._detect_jinja2_expression(value)

    def _detect_jinja2_expression(self, value: bool | str | None) -> bool:
        """Detect if value is a Jinja2 expression.

        Args:
            value: The value to check

        Returns:
            True if value contains Jinja2 markers
        """
        if not isinstance(value, str):
            return False
        jinja2_patterns = [r"\{\{.*?\}\}", r"\{%.*?%\}", r"\{#.*?#\}"]
        return any(re.search(pattern, value) for pattern in jinja2_patterns)

    def _evaluate_suppression(self, task: "Task") -> bool:
        """Evaluate whether output should be suppressed.

        Args:
            task: The Nornir task

        Returns:
            True if output should be suppressed
        """
        if isinstance(self.value, bool):
            return self.value

        if self.value is None:
            return False

        if self.is_jinja2_expression:
            vars_manager = self.context.get("vars_manager")
            if vars_manager:
                host = next(iter(task.nornir.inventory.hosts.values()))
                resolved = vars_manager.resolve_string(self.value, host)
                return resolved.lower() in ("true", "yes", "1")
            return False

        return bool(self.value)

    def task_started(self, task: "Task") -> None:
        """Mark task for output suppression if conditions are met.

        Args:
            task: The Nornir task
        """
        should_suppress = self._evaluate_suppression(task)

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
        if isinstance(self.value, str) and not self.is_jinja2_expression:
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
