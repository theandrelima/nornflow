from typing import Any

from nornir.core.inventory import Host
from nornir.core.task import Task

from nornflow.hooks.exceptions import HookError
from nornflow.vars.constants import JINJA2_MARKERS, TRUTHY_STRING_VALUES


class Jinja2ResolvableMixin:
    """Mixin providing seamless Jinja2 template resolution to hooks.

    This mixin adds a single method `get_resolved_value()` that handles
    all Jinja2 detection and resolution automatically. Hooks just call
    this method and get back the final value ready to use.

    The mixin expects the hook to have:
        - self.value: The hook's configuration value
        - self.context: Property returning hook execution context

    The Hook base class provides both. The context will contain 'vars_manager'
    during hook lifecycle execution (task_started, task_instance_started, etc.)
    but NOT during initialization or validation.

    Important:
        Only call get_resolved_value() with Jinja2 expressions inside lifecycle
        methods where the execution context has been populated by the framework.

    Example:
        class MyHook(Hook, Jinja2ResolvableMixin):
            hook_name = "my_hook"

            def task_started(self, task: Task):
                should_run = self.get_resolved_value(task, as_bool=True)
    """

    def get_resolved_value(self, task: Task, as_bool: bool = False, default: Any = None) -> Any:
        """Get the final resolved value, handling Jinja2 automatically.

        This method checks if self.value is a Jinja2 expression, resolves it
        if needed, converts to the requested type, and returns the final value.

        Args:
            task: The task being executed.
            as_bool: If True, convert result to boolean.
            default: Default value if self.value is falsy.

        Returns:
            The resolved value, optionally converted to boolean.

        Raises:
            HookError: If vars_manager not available in context (likely called
                outside of hook lifecycle methods) or if task has no hosts
                when Jinja2 resolution is needed.
        """
        if not self.value:
            return default

        if self._is_jinja2_expression(self.value):
            host = self._extract_host_from_task(task)
            resolved = self._resolve_jinja2(self.value, host)
        else:
            resolved = self.value

        if as_bool:
            return self._to_bool(resolved)

        return resolved

    def _is_jinja2_expression(self, value: Any) -> bool:
        """Check if a value contains Jinja2 template markers.

        Args:
            value: The value to check.

        Returns:
            True if value is a string with Jinja2 markers, False otherwise.
        """
        if not isinstance(value, str):
            return False

        return any(marker in value for marker in JINJA2_MARKERS)

    def _extract_host_from_task(self, task: Task) -> Host:
        """Extract a host from task inventory.

        Args:
            task: The task to extract host from.

        Returns:
            First host from task's inventory.

        Raises:
            HookError: If task has no hosts.
        """
        if not task.nornir.inventory.hosts:
            raise HookError("Cannot extract host from task with empty inventory")

        return next(iter(task.nornir.inventory.hosts.values()))

    def _resolve_jinja2(self, value: str, host: Host) -> Any:
        """Resolve a Jinja2 template string.

        Args:
            value: The template string to resolve.
            host: The host to resolve for.

        Returns:
            The resolved value from the template.

        Raises:
            HookError: If vars_manager not available in context.
        """
        vars_manager = self.context.get("vars_manager")
        if not vars_manager:
            raise HookError(
                "vars_manager not available in hook context. "
                "get_resolved_value() can only be called from hook lifecycle methods "
                "(task_started, task_instance_started, etc.) where the execution "
                "framework has populated the context. It cannot be called from "
                "__init__() or execute_hook_validations()."
            )

        device_context = vars_manager.get_device_context(host.name)
        return device_context.resolve_value(value)

    def _to_bool(self, value: Any) -> bool:
        """Convert a value to boolean.

        Args:
            value: The value to convert.

        Returns:
            Boolean representation of the value.
        """
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in TRUTHY_STRING_VALUES

        return bool(value)
