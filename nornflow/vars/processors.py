from nornir.core.processor import Processor
from nornir.core.task import Result, Task

from nornflow.vars.manager import VariablesManager


class NornFlowVariableProcessor(Processor):
    """
    Processor that manages host context for variable resolution.
    
    This processor sets the current host in the variable manager's
    proxy object before a task is executed on a host, enabling
    host-specific variable resolution.
    """
    
    def __init__(self, vars_manager: VariablesManager):
        """Initialize with a reference to the variable manager."""
        super().__init__()
        self.vars_manager = vars_manager
    
    def task_instance_started(self, task: Task, host: str) -> None:
        """
        Set the current host in the proxy when a task starts on a host.
        
        Args:
            task: The task being executed
            host: The host name
        """
        if task.host:
            # Simply set the current host in the proxy - no data copying needed
            self.vars_manager.nornir_host_proxy.current_host = task.host
    
    def task_instance_completed(self, task: Task, host: str, result: Result) -> None:
        """
        Clear the current host when task execution on a host completes.
        
        This is optional but helps prevent potential issues with
        references to stale host data.
        
        Args:
            task: The task that was executed
            host: The host name
            result: The task result
        """
        # Clear the host reference when done with this host
        self.vars_manager.nornir_host_proxy.current_host = None
