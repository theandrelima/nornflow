from typing import TYPE_CHECKING

from nornir.core.processor import Processor
from nornir.core.task import AggregatedResult, MultiResult, Task
from nornir.core.inventory import Host

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
    through a '_nornflow_context' dictionary injected into the task's params. This context is set
    by TaskModel before task execution and allows hooks to access NornFlow components without
    direct coupling.
    
    Hook Retrieval Efficiency:
    ==========================
    _get_hooks_for_task() is called in every processor method because:
    1. Hooks are task-specific - different tasks may have different hook configurations
    2. Context is injected per-task via task params, not stored globally
    3. Nornir's processor architecture doesn't provide task-level state persistence
    4. The overhead is minimal: dictionary lookup + list retrieval, cached per task
    5. For scale (100k hosts), this is negligible compared to actual task execution
    
    Cache Cleanup:
    ==============
    The _cleanup_task() method is needed because:
    - The processor maintains a cache (_active_hooks) to avoid repeated context extraction
    - Without cleanup, this cache would grow indefinitely during workflow execution
    - Cleanup happens in task_completed() when the task finishes across all hosts
    """
    
    def __init__(self):
        """Initialize the hook processor."""
        self._active_hooks: dict[int, list["Hook"]] = {}
    
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
        
        if hasattr(task, 'params') and task.params:
            context = task.params.get('_nornflow_context', {})
            hooks = context.get('hooks', [])
            self._active_hooks[task_id] = hooks
            return hooks
        
        return []
    
    def _cleanup_task(self, task: Task) -> None:
        """Clean up cached data for completed task.
        
        Args:
            task: The completed task
        """
        task_id = id(task)
        if task_id in self._active_hooks:
            del self._active_hooks[task_id]
    
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