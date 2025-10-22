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
            # Custom handling logic here
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
from abc import ABC
from typing import Any, TYPE_CHECKING
from nornir.core.task import Task, AggregatedResult, MultiResult
from nornir.core.inventory import Host
from nornflow.hooks.exceptions import HookValidationError


if TYPE_CHECKING:
    from nornflow.models import TaskModel


class Hook(ABC):
    """Base class for all NornFlow hooks implementing Nornir's Processor protocol.
    
    Hooks are mini-processors that activate when their `hook_name` is present
    in a task's configuration. They have full access to Nornir's execution
    lifecycle and are cached globally via Flyweight pattern for performance.
    
    Subclasses must define `hook_name` and can override only the lifecycle methods
    that are relevant to their use cases.
    
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
            # Mark host as skipped
            pass
    """
    
    # Required: Identifies this hook in task configuration
    hook_name: str
    
    # Public: Control execution scope (True = once per task, False = per host)
    run_once_per_task: bool = False
    
    # Optional: Dict of exception classes to handler method names for custom handling
    exception_handlers: dict[type[Exception], str] = {}
    
    def __init__(self, value: Any = None):
        """Initialize hook with configuration value.
        
        Args:
            value: The value from task's hooks configuration
        """
        self.value = value
        self._execution_count = {}  # Track executions per task
        self._current_context: dict[str, Any] | None = None
    
    # Processor Protocol Methods (all optional to implement)
    
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
    
    # Hook-specific helpers
    
    def get_context(self, task: Task) -> dict[str, Any]:
        """Extract NornFlow context from task.
        
        Args:
            task: The Nornir task
            
        Returns:
            Context dict with task_model, vars_manager, etc.
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