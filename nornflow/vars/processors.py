"""
NornFlow Variable Processing Module

This module provides the NornFlowVariableProcessor, which integrates NornFlow's
variable system with Nornir's task execution. It handles Jinja2 template
resolution in task arguments and manages the 'set' task for runtime variable
manipulation.
"""

import logging

from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import MultiResult, Task

from nornflow.vars.manager import NornFlowVariablesManager

logger = logging.getLogger(__name__)


class NornFlowVariableProcessor(Processor):
    """
    Processor responsible for substituting variables in task arguments and managing
    NornFlow's variable context during task execution.

    This processor integrates with the NornFlowVariablesManager to:
    1. Resolve Jinja2 templates in task arguments using variables from the NornFlow
       Default Namespace and the Nornir Host (`host.`) Namespace.
    2. Manage the current host context for the NornirHostProxy to enable `host.`
       variable access.
    3. Handle the NornFlow built-in 'set' task, which creates or updates
       Runtime Variables in the NornFlow Default Namespace for the current device.
    4. Ensure that variable resolution and setting are performed within the correct,
       isolated per-device context.
    """

    def __init__(self, vars_manager: NornFlowVariablesManager):
        """
        Initializes the NornFlowVariableProcessor.

        Args:
            vars_manager: An instance of NornFlowVariablesManager to handle
                          variable resolution and management.
        """
        self.vars_manager = vars_manager

    def task_started(self, task: Task) -> None:
        """
        Called when a Nornir task is about to start globally (before any host).
        Sets the Nornir object on the host proxy if available.
        """
        # Provide the Nornir object to the proxy if it's available on the task.
        # This allows the proxy to access the full Nornir inventory if needed.
        if hasattr(task, "nornir") and task.nornir:
            self.vars_manager.nornir_host_proxy.nornir = task.nornir
            logger.debug(f"Nornir object set on NornirHostProxy via task '{task.name}'.")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """
        This method sets the current host context for variable resolution
        and processes Jinja2 templates in task parameters.

        Raises:
            Exception: Propagates exceptions from variable processing or resolution.
        """
        try:
            # Set the current host name in the proxy to enable {{ host. }} variable access
            self.vars_manager.nornir_host_proxy.current_host_name = host.name
            logger.debug(f"Set current_host_name to '{host.name}' for task '{task.name}'.")

            # Process task parameters for all tasks uniformly
            if task.params:  # Ensure params exist
                processed_params = self.vars_manager.resolve_data(task.params, host.name)
                task.params = processed_params
                logger.debug(f"Processed task.params for task '{task.name}' on host '{host.name}'")

        except Exception:
            logger.exception(f"Error processing variables for task '{task.name}' on host '{host.name}'")
            raise

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """
        Called after a task instance completes for a specific host.
        Clears the current host context from the NornirHostProxy.
        """
        # Clear the host reference to prevent stale context between task executions on different hosts
        # or subsequent tasks for the same host if the proxy were reused without proper reset.
        self.vars_manager.nornir_host_proxy.current_host_name = None
        logger.debug(f"Cleared current_host_name after task '{task.name}' on host '{host.name}'.")

    def task_completed(self, task: Task, result: MultiResult) -> None:
        pass

    def subtask_started(self, task: Task, host: Host) -> None:
        pass

    def subtask_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass

    def subtask_instance_failed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass

    def task_failed(self, task: Task, result: MultiResult) -> None:
        pass
