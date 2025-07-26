"""
NornFlow Variable Processing Module

This module provides the NornFlowVariableProcessor, which integrates NornFlow's
variable system with Nornir's task execution. It handles Jinja2 template
resolution in task arguments and manages the 'set' task for runtime variable
manipulation.
"""

import logging
from typing import Any

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
        This method sets the current host context for variable resolution,
        handles the 'set' task specifically, and processes Jinja2 templates
        in the parameters of other tasks.

        Raises:
            Exception: Propagates exceptions from variable processing or resolution.
        """
        try:
            # Set the current host name in the proxy to enable {{ host. }} variable access.
            self.vars_manager.nornir_host_proxy.current_host_name = host.name
            logger.debug(f"Set current_host_name to '{host.name}' for task '{task.name}'.")

            if task.name == "set":
                # The 'set' task's parameters are instructions for what variables to set.
                # _handle_set_task will resolve the *values* of these parameters internally.
                # The 'set' task itself doesn't need its params processed further by this
                # processor, as its action is entirely handled by _handle_set_task.
                if task.params:  # Ensure params exist to avoid errors if 'set' is called with no args
                    self._handle_set_task(task.params, host.name)
                else:
                    logger.warning(
                        f"Task 'set' for host '{host.name}' called with no arguments. "
                        "No variables will be set."
                    )
            # For all other tasks, resolve Jinja2 templates in their parameters.
            elif task.params:  # Ensure params exist
                # task.params is a dict; resolve_data will handle nested structures.
                processed_params = self.vars_manager.resolve_data(task.params, host.name)
                # Nornir tasks expect their params to be updated in place or reassigned.
                # Reassigning is generally safer and cleaner.
                task.params = processed_params
                logger.debug(f"Processed task.params for task '{task.name}' on host '{host.name}'.")

        except Exception:
            logger.exception(f"Error processing variables for task '{task.name}' on host '{host.name}'")
            # Re-raise the exception to allow Nornir or higher-level handlers to manage it.
            raise

    def _handle_set_task(self, task_args: dict[str, Any], host_name: str) -> None:
        """
        This method iterates through the arguments provided to the 'set' task.
        Each key-value pair is treated as a NornFlow Runtime Variable to be set
        for the current host. The values are resolved using Jinja2 templating
        before being stored.

        Args:
            task_args: The arguments (parameters) of the 'set' task.
            host_name: The name of the host for which variables are being set.
        """
        logger.debug(f"Handling 'set' task for host '{host_name}' with args: {task_args}")
        for key, value in task_args.items():
            # The value itself might be a Jinja2 template or a structure containing them.
            # Resolve it using the full variable context available to the host.
            resolved_value = self.vars_manager.resolve_data(value, host_name)

            # Set the variable as a NornFlow Runtime Variable (precedence #2)
            # for the current host.
            self.vars_manager.set_runtime_variable(key, resolved_value, host_name)
            logger.info(f"NornFlow variable '{key}' set for host '{host_name}' via 'set' task.")

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
