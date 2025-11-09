"""NornFlow Hook Framework: Processor-Based Architecture

This module implements NornFlow's extensible hook system, where hooks are
Nornir Processors (in disguise) that participate in the complete task execution lifecycle.
This provides complete control over execution flow while maintaining clean
separation between core logic and user-defined behaviors.

PHILOSOPHY
==========

Hooks provide a clean separation between NornFlow's core execution logic and
user-defined behaviors. They implement Nornir's Processor protocol directly,
enabling full lifecycle access. Hooks are selective, activating only when
their `hook_name` is present in a NornFLow task config. From an SW Eng. perspective
they follow the Flyweight pattern for memory efficiency.

Exception Handling
==================

Hooks can define custom exception handling for specific exceptions they raise.
This allows hooks to signal special conditions without breaking workflow execution.
Each hook subclass can optionally define an `exception_handlers` class attribute
as a dict mapping exception classes to handler method names (strings). When the
NornFlowHookProcessor catches such an exception from a hook method, it calls the
handler on the hook instance with (exception, task, args). Handlers perform custom
logic and do not re-raise. Uncaught exceptions bubble up to break execution.

Example:
    class MyHook(Hook):
        hook_name = "my_hook"
        exception_handlers = {MyCustomError: "_handle_my_error"}

        def _handle_my_error(self, exception, task, args):
            pass

EXECUTION SCOPES
================

Hooks control execution scope via `run_once_per_task`:
- True: Hook runs once per task across all hosts (e.g., task-level setup)
- False: Hook runs per host (e.g., per-host result processing)

VALIDATION
==========

Hooks validate at instantiation and execution:
- Method Implementation: Lifecycle methods are optional but must be callable
- Task Compatibility: validate_* methods can be used to sanitize parameters passed to hooks
- Execution Scope: Enforced via `run_once_per_task` flag
"""

# ruff: noqa: B027
from abc import ABC
from typing import Any, ClassVar, TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

if TYPE_CHECKING:
    from nornflow.models import TaskModel


class Hook(ABC):
    """Base class for all NornFlow hooks implementing Nornir's Processor protocol.

    Hooks are mini-processors that activate when their `hook_name` is present
    in a task's configuration. They have full access to Nornir's execution
    lifecycle and are cached globally via Flyweight pattern for performance.

    Subclasses must define `hook_name` and can override only the lifecycle methods
    that are relevant to their use cases.

    Context Injection:
    ==================
    The NornFlowHookProcessor automatically injects the complete context into
    `self._current_context` before calling any hook method. Hooks access this
    context via the `context` property, which returns the pre-injected dict
    containing task_model, vars_manager, and other workflow-level data.

    Exception Handling:
    ====================
    Hooks can define custom exception handling via the `exception_handlers` class
    attribute (dict mapping exception classes to handler method names). When the
    NornFlowHookProcessor catches a hook-raised exception in this dict, it calls
    the handler method on the hook instance with (exception, task, args). Handlers
    perform custom logic (e.g., skips) without re-raising. Uncaught exceptions
    bubble up.

    Example:
        exception_handlers = {SkipHostError: "_handle_skip"}

        def _handle_skip(self, exception, task, args):
            pass
    """

    hook_name: str

    run_once_per_task: bool = False

    exception_handlers: ClassVar[dict[type[Exception], str]] = {}

    def __init__(self, value: Any = None):
        """Initialize hook with configuration value.

        Args:
            value: The value from task's hooks configuration
        """
        self.value = value
        self._execution_count = {}
        self._current_context: dict[str, Any] | None = None

    def task_started(self, task: Task) -> None:
        """Called when task starts across all hosts."""
        pass

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Called when task completes across all hosts."""
        pass

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Called before task executes on specific host."""
        pass

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Called after task executes on specific host."""
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Called before subtask executes on host."""
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Called after subtask executes on host."""
        pass

    @property
    def context(self) -> dict[str, Any]:
        """Get the complete NornFlow context for this execution.

        The context is automatically injected by NornFlowHookProcessor before
        any hook method is called. It contains both workflow-level data
        (vars_manager, catalogs) and task-specific data (task_model, hooks).

        Returns:
            Context dict with task_model, vars_manager, and other execution data.
        """
        return self._current_context or {}

    def should_execute(self, task: Task) -> bool:
        """Check if this hook should execute for given task.

        Args:
            task: The Nornir task

        Returns:
            True if hook should execute
        """
        if self.run_once_per_task:
            task_id = id(task)
            if task_id in self._execution_count:
                return False
            self._execution_count[task_id] = 1
            return True
        return True

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Execute validation logic specific to this hook.

        This method is called during task preparation to allow hooks to validate
        their configuration and compatibility with the task.

        Args:
            task_model: The task model being validated

        Raises:
            HookValidationError: If validation fails
        """
        pass
