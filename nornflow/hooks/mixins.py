from typing import Any, TYPE_CHECKING

from jinja2 import TemplateSyntaxError
from nornir.core.inventory import Host
from nornir.core.task import Task

from nornflow.hooks.exceptions import HookError, HookValidationError
from nornflow.vars.constants import JINJA2_MARKERS, TRUTHY_STRING_VALUES
from nornflow.vars.jinja2_utils import Jinja2EnvironmentManager

if TYPE_CHECKING:
    from nornflow.models import TaskModel


class Jinja2ResolvableMixin:
    """Mixin providing automatic Jinja2 validation and resolution to hooks.

    This mixin automatically validates string values as Jinja2 expressions during
    workflow preparation and provides resolution methods for execution. Developers
    using this mixin don't need Jinja2 awareness - just include it in the inheritance
    chain and call get_resolved_value() in lifecycle methods.

    The mixin expects the hook to have:
        - self.value: The hook's configuration value
        - self.context: Property returning hook execution context
        - self.hook_name: The hook's name for error messages

    The Hook base class provides all of these.

    Automatic Validation:
        The mixin overrides execute_hook_validations() to automatically validate
        string values that contain Jinja2 markers. Plain strings (like "yes", "true")
        are allowed and later converted by _to_bool(). Works with any inheritance order
        thanks to cooperative super() calls in the Hook base class.

        NOTE: Empty string validation is NOT performed by this mixin. Individual hook
        implementations should validate empty strings if their specific use case
        requires it, as some hooks may legitimately accept empty strings.

    Important:
        Only call get_resolved_value() inside lifecycle methods where the execution
        context has been populated by the framework. When calling from task_instance_started(),
        you MUST pass the host parameter explicitly to ensure per-host resolution.

    Example:
        class MyHook(Hook, Jinja2ResolvableMixin):
            hook_name = "my_hook"

            def task_instance_started(self, task: Task, host: Host):
                should_run = self.get_resolved_value(task, host=host, as_bool=True)
    """

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Validate hook configuration, including automatic Jinja2 validation.

        If self.value is a string containing Jinja2 markers, validates it as a
        Jinja2 expression. Plain strings without markers are allowed.
        Subclasses can override to add additional validation, but must
        call super().execute_hook_validations(task_model) first.

        Args:
            task_model: The task model to validate against

        Raises:
            HookValidationError: If validation fails
        """
        if isinstance(self.value, str) and self._is_jinja2_expression(self.value):
            self._validate_jinja2_string(task_model)

        if hasattr(super(), "execute_hook_validations"):
            super().execute_hook_validations(task_model)

    def _validate_jinja2_string(self, task_model: "TaskModel") -> None:
        """Validate that string value is a proper Jinja2 expression.

        Args:
            task_model: The task model being validated

        Raises:
            HookValidationError: If string is empty or has syntax errors
        """
        if not self.value.strip():
            raise HookValidationError(
                self.hook_name,
                [("empty_expression", f"Task '{task_model.name}': Jinja2 expression cannot be empty")],
            )

        try:
            manager = Jinja2EnvironmentManager()
            manager.env.from_string(self.value)
        except TemplateSyntaxError as e:
            raise HookValidationError(
                self.hook_name,
                [("jinja2_syntax", f"Task '{task_model.name}': Jinja2 syntax error: {e}")],
            ) from e
        except Exception as e:
            raise HookValidationError(
                self.hook_name,
                [("jinja2_validation", f"Task '{task_model.name}': Jinja2 validation failed: {e}")],
            ) from e

    def get_resolved_value(
        self, task: Task, host: Host | None = None, as_bool: bool = False, default: Any = None
    ) -> Any:
        """Get the final resolved value, handling Jinja2 automatically.

        This method checks if self.value is a Jinja2 expression, resolves it
        if needed, converts to the requested type, and returns the final value.

        Args:
            task: The task being executed
            host: The specific host to resolve for. If None, extracts first host
            as_bool: If True, convert result to boolean
            default: Default value if self.value is falsy

        Returns:
            The resolved value, optionally converted to boolean

        Raises:
            HookError: If vars_manager not available or task has no hosts
        """
        if not self.value:
            return default

        if self._is_jinja2_expression(self.value):
            if not host:
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

        Warning: This returns the FIRST host from inventory, which is only safe
        when called from task_started (runs once per task). For task_instance_started,
        you MUST pass the host parameter explicitly.

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
            raise HookError(f"{self.hook_name or 'Hook'}: Variables manager not available in context.")

        return vars_manager.resolve_string(value, host.name)

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
