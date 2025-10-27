from typing import Any
from colorama import Fore, Style
from nornir.core.task import Task
from nornflow.hooks import Hook, register_hook


@register_hook
class ShushHook(Hook):
    """Signals to output processors that task results should be suppressed.
    
    This hook does NOT implement output suppression itself. Instead, it marks tasks
    for suppression by setting a flag that output-aware processors further down the
    processor chain can check and act upon. The hook verifies that at least one
    processor in the chain has the 'supports_shush_hook' attribute set to True,
    warning the user if no compatible processor is found.
    
    The actual suppression logic is delegated to processors that handle output
    (like DefaultNornFlowProcessor), allowing this hook to remain decoupled from
    specific output implementations while preserving all result data for other
    hooks and processors to consume.
    
    Configuration:
        True: Mark task for output suppression
        False: Normal output behavior (default)
    
    Examples:
        # Suppress output for noisy tasks while preserving data for other hooks
        tasks:
          - name: backup_configs
            task: netmiko_send_config
            shush: true
            set_to: backup_results  # Result data still available
            
        # Normal output behavior
        tasks:
          - name: show_version
            task: netmiko_send_command
            shush: false
    """
    
    hook_name = "shush"
    run_once_per_task = True
    
    def __init__(self, value: Any = None):
        """Initialize shush hook.
        
        Args:
            value: Boolean indicating whether to suppress output display
        """
        super().__init__(value)
        self.should_suppress = bool(value) if value is not None else False
    
    def task_started(self, task: Task) -> None:
        """Check for processor support and mark task for output suppression."""
        if not self.should_suppress:
            return
            
        has_support = any(
            getattr(processor, 'supports_shush_hook', False)
            for processor in task.nornir.processors
        )
        
        if not has_support:
            print(
                f"{Fore.YELLOW}{Style.BRIGHT}Warning: 'shush' hook has no effect - "
                f"no compatible processor found in chain. Outputs are not going to be suppressed.{Style.RESET_ALL}"
            )
            return
            
        if not hasattr(task.nornir, '_nornflow_suppressed_tasks'):
            task.nornir._nornflow_suppressed_tasks = set()
        task.nornir._nornflow_suppressed_tasks.add(task.name)
    
    def task_completed(self, task: Task, result: Any) -> None:
        """Clean up the suppression marker."""
        if hasattr(task.nornir, '_nornflow_suppressed_tasks'):
            task.nornir._nornflow_suppressed_tasks.discard(task.name)
