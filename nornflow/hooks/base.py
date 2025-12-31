from typing import Any, ClassVar, TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

from nornflow.hooks.exceptions import HookRegistrationError

if TYPE_CHECKING:
    from nornflow.models import TaskModel

HOOK_REGISTRY: dict[str, type["Hook"]] = {}


class Hook:
    """Base hook class with automatic registration and cooperative validation.

    Any class that inherits from Hook and defines a hook_name will be
    automatically registered when the class is defined (at import time).

    The execute_hook_validations method uses cooperative super() calls to ensure
    proper validation in multiple inheritance scenarios (e.g., with mixins).

    Example:
        class MyHook(Hook):
            hook_name = "my_hook"

            def task_started(self, task: Task) -> None:
                print(f"Task {task.name} starting")

    Attributes:
        hook_name: Unique identifier for this hook type. Required for registration.
        run_once_per_task: If True, hook executes once per task regardless of hosts.
        exception_handlers: Maps exception types to handler method names.
    """

    hook_name: ClassVar[str | None] = None
    run_once_per_task: bool = False
    exception_handlers: ClassVar[dict[type[Exception], str]] = {}

    def __init_subclass__(cls, **kwargs):
        """Automatically register hook subclasses when they are defined.

        Args:
            **kwargs: Any keyword arguments passed to the class definition.

        Raises:
            HookRegistrationError: If a different class already registered
                                   the same hook_name.
        """
        super().__init_subclass__(**kwargs)

        # Only register if hook_name is defined
        if not hasattr(cls, "hook_name") or not cls.hook_name:
            return

        # Check for duplicate registration
        if cls.hook_name in HOOK_REGISTRY:
            existing_class = HOOK_REGISTRY[cls.hook_name]
            if existing_class is not cls:
                raise HookRegistrationError(
                    f"Hook name '{cls.hook_name}' is already registered "
                    f"by {existing_class.__module__}.{existing_class.__name__}. "
                    f"Cannot register {cls.__module__}.{cls.__name__}"
                )

        HOOK_REGISTRY[cls.hook_name] = cls

    def __init__(self, value: Any = None):
        """Initialize hook with configuration value.

        Args:
            value: Configuration value for this hook instance.
        """
        self.value = value
        self._execution_count: dict[int, int] = {}
        self._current_context: dict[str, Any] | None = None

    @property
    def context(self) -> dict[str, Any]:
        """Get the current execution context.

        Returns:
            The current context dictionary, or empty dict if no context set.
        """
        return self._current_context or {}

    def should_execute(self, task: Task) -> bool:
        """Determine if hook should execute for this task.

        Args:
            task: The task being executed.

        Returns:
            True if hook should execute, False otherwise.
        """
        if not self.run_once_per_task:
            return True

        task_model = self.context.get("task_model")
        if not task_model:
            return True

        task_model_id = id(task_model)
        if task_model_id in self._execution_count:
            return False

        self._execution_count[task_model_id] = 1
        return True

    def task_started(self, task: Task) -> None:
        """Called when task starts (before any host).

        Args:
            task: The task that is starting.
        """
        pass

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Called when task completes (after all hosts).

        Args:
            task: The task that completed.
            result: Aggregated results from all hosts.
        """
        pass

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Called before task executes on a specific host.

        Args:
            task: The task about to execute.
            host: The host it will execute on.
        """
        pass

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Called after task executes on a specific host.

        Args:
            task: The task that executed.
            host: The host it executed on.
            result: The execution results.
        """
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Called before subtask executes on a specific host.

        Args:
            task: The subtask about to execute.
            host: The host it will execute on.
        """
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Called after subtask executes on a specific host.

        Args:
            task: The subtask that executed.
            host: The host it executed on.
            result: The execution results.
        """
        pass

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Validate hook configuration for the task.

        Uses cooperative super() to ensure validation methods in mixins and
        parent classes are called properly in multiple inheritance scenarios.

        Args:
            task_model: The task model to validate against.

        Raises:
            HookValidationError: If validation fails.
        """
        if hasattr(super(), "execute_hook_validations"):
            super().execute_hook_validations(task_model)
