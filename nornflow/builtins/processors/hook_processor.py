from typing import TYPE_CHECKING, Any, Callable

from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import AggregatedResult, MultiResult, Task

from .decorators import hook_delegator

if TYPE_CHECKING:
    from nornflow.hooks import Hook


class NornFlowHookProcessor(Processor):
    """Orchestrator processor that delegates to registered hooks.
    
    This processor is attached to the Nornir instance and manages all
    hook executions. It extracts hook information from task context
    and calls appropriate hook methods at each lifecycle point.
    
    Context Injection:
    ==================
    The NornFlowHookProcessor receives external NornFlow-specific data (e.g., task_model, vars_manager)
    through a pre-registration mechanism. Before a task is run, RunnableModel registers the context
    with this processor, associating it with the task function. When Nornir creates the Task
    instance and calls processor methods, we match the task.task (the function) to retrieve
    the registered context.
    
    Hook Retrieval Efficiency:
    ==========================
    _get_hooks_for_task() is called in every processor method because:
    1. Hooks are task-specific - different tasks may have different hook configurations
    2. Context is registered per-task function before execution
    3. Nornir's processor architecture doesn't provide task-level state persistence
    4. The overhead is minimal: dictionary lookup + list retrieval, cached per task
    5. For scale (100k hosts), this is negligible compared to actual task execution
    
    Cache Cleanup:
    ==============
    The _cleanup_task() method is needed because:
    - The processor maintains caches to avoid repeated context extraction
    - Without cleanup, these caches would grow indefinitely during workflow execution
    - Cleanup happens in task_completed() when the task finishes across all hosts
    """
    
    def __init__(self):
        """Initialize the hook processor."""
        self._active_hooks: dict[int, list["Hook"]] = {}
        self._task_contexts: dict[Callable, dict[str, Any]] = {}  # Maps task function to context
    
    def register_task_context(self, task_func: Callable, context: dict[str, Any]) -> None:
        """Register context for a task function before execution.
        
        Args:
            task_func: The task function that will be executed
            context: The NornFlow context containing hooks, vars_manager, etc.
        """
        self._task_contexts[task_func] = context
    
    def _get_context_for_task(self, task: Task) -> dict[str, Any]:
        """Get the registered context for a task.
        
        Args:
            task: The Nornir task
            
        Returns:
            The NornFlow context dict, or empty dict if not found
        """
        # task.task is the actual function being executed
        return self._task_contexts.get(task.task, {})
    
    def _get_hooks_for_task(self, task: Task) -> list["Hook"]:
        """Get active hooks for a task from context.
        
        Args:
            task: The Nornir task
            
        Returns:
            List of Hook instances for this task
        """
        task_id = id(task)
        
        if task_id in self._active_hooks:
            return self._active_hooks[task_id]
        
        context = self._get_context_for_task(task)
        hooks = context.get('hooks', [])
        self._active_hooks[task_id] = hooks
        return hooks
    
    def _cleanup_task(self, task: Task) -> None:
        """Clean up cached data for completed task.
        
        Args:
            task: The completed task
        """
        task_id = id(task)
        if task_id in self._active_hooks:
            del self._active_hooks[task_id]
        
        # Clean up the registered context for this task function
        if task.task in self._task_contexts:
            del self._task_contexts[task.task]
    
    @hook_delegator
    def task_started(self, task: Task) -> None:
        """Delegate to hooks' task_started methods."""
    
    @hook_delegator
    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Delegate to hooks' task_completed methods."""
        self._cleanup_task(task)
    
    @hook_delegator
    def task_instance_started(self, task: Task, host: Host) -> None:
        """Delegate to hooks' task_instance_started methods."""
    
    @hook_delegator
    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Delegate to hooks' task_instance_completed methods."""
    
    @hook_delegator
    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Delegate to hooks' subtask_instance_started methods."""
    
    @hook_delegator
    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Delegate to hooks' subtask_instance_completed methods."""
