"""
NornFlow Variable Processing Module

This module provides the NornFlowVariableProcessor, which integrates NornFlow's
variable system with Nornir's task execution. It handles Jinja2 template
resolution in task arguments and provides variable context for hooks and tasks.

Hook-Driven Template Resolution
==============================

The processor uses a capability-based architecture where hooks can declare
processing requirements via class attributes:

    class MyHook(Hook):
        requires_deferred_templates = True  # Enable two-phase processing

Processing Modes:
- **Immediate** (default): Templates resolved in task_instance_started()
- **Deferred**: Templates stored and resolved just-in-time via resolve_deferred_params()

The processor automatically selects the appropriate mode based on hook declarations.

Example deferred flow:
1. Hook declares requires_deferred_templates = True
2. Processor stores templates without resolving them
3. Hook evaluates inputs (potentially using variable context)
4. Hook decorator calls resolve_deferred_params() for non-skipped hosts
5. Task executes with resolved parameters

This is particularly useful for hooks that require evaluating Jinja2 template inputs
BEFORE anything else is evaluated by the Jinja2 Environment in the same task execution.
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
    Processor responsible for managing NornFlow's variable context and template resolution.

    This processor uses a hook-driven strategy for template resolution:
    - If any hook requests deferred processing, templates are stored for just-in-time resolution
    - If no hook requests deferred processing, templates are resolved immediately
    - Hooks declare their needs via the requires_deferred_templates property

    This processor integrates with the NornFlowVariablesManager to:
    1. Set up variable context that hooks can use for condition evaluation
    2. Conditionally defer template resolution based on hook requirements
    3. Provide just-in-time template resolution for hooks that need it
    4. Provide variable manager access for tasks (like the 'set' builtin task)
    5. Ensure variable operations are performed within correct per-device context
    """

    def __init__(self, vars_manager: NornFlowVariablesManager):
        """Initialize the processor with a variable manager.

        Args:
            vars_manager: Variable manager for template resolution and context management.
        """
        self.vars_manager = vars_manager
        self._deferred_params: dict[tuple[str, str], dict[str, Any]] = {}

    def task_started(self, task: Task) -> None:
        """Called when a task starts globally. Sets up Nornir object reference."""
        if hasattr(task, "nornir") and task.nornir:
            self.vars_manager.nornir_host_proxy.nornir = task.nornir
            logger.debug(f"Nornir object set on NornirHostProxy via task '{task.name}'.")

    def _requires_deferred_templates(self, task: Task) -> bool:
        """Check if any hook for this task requires deferred template processing.

        Uses capability discovery to detect hooks that declare requires_deferred_templates = True.

        Returns:
            True if any hook requires deferred templates, False otherwise.
        """
        for processor in task.nornir.processors:
            if hasattr(processor, "task_hooks"):
                for hook in processor.task_hooks:
                    if getattr(hook, "requires_deferred_templates", False):
                        return True
        return False

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Set up host context and conditionally defer template resolution.

        Processing strategy selection:
        - Deferred mode: Store templates if any hook requires it
        - Immediate mode: Process templates now (backward compatibility)
        """
        try:
            self.vars_manager.nornir_host_proxy.current_host_name = host.name
            logger.debug(f"Set current_host_name to '{host.name}' for task '{task.name}'.")

            if task.params:
                if self._requires_deferred_templates(task):
                    key = (task.name, host.name)
                    self._deferred_params[key] = task.params.copy()
                    task.params = {}
                    logger.debug(f"Deferred template processing for '{host.name}' in task '{task.name}'")
                else:
                    processed_params = self.vars_manager.resolve_data(task.params, host.name)
                    task.params = processed_params
                    logger.debug(f"Processed task.params for task '{task.name}' on host '{host.name}'")

        except Exception:
            logger.exception(f"Error processing variables for task '{task.name}' on host '{host.name}'")
            raise

    def resolve_deferred_params(self, task: Task, host: Host) -> dict[str, Any] | None:
        """Resolve stored templates just-in-time for task execution.

        Called by hook decorators to convert deferred templates into actual parameter values.

        Returns:
            Resolved parameters dict if deferred params exist, None otherwise.
        """
        key = (task.name, host.name)

        if key not in self._deferred_params:
            return None

        try:
            if self.vars_manager.nornir_host_proxy.current_host_name != host.name:
                self.vars_manager.nornir_host_proxy.current_host_name = host.name

            original_params = self._deferred_params.pop(key)
            resolved_params = self.vars_manager.resolve_data(original_params, host.name)
            logger.debug(f"Resolved templates for '{host.name}' in task '{task.name}'")
            return resolved_params

        except Exception:
            logger.exception(f"Error resolving templates for task '{task.name}' on host '{host.name}'")
            self._deferred_params.pop(key, None)
            raise

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Clean up host context and any unresolved deferred parameters."""
        self.vars_manager.nornir_host_proxy.current_host_name = None
        logger.debug(f"Cleared current_host_name after task '{task.name}' on host '{host.name}'.")

        key = (task.name, host.name)
        if key in self._deferred_params:
            self._deferred_params.pop(key)

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
