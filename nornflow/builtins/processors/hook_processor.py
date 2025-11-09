from typing import Any, TYPE_CHECKING

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

    Context Management:
    ==================
    The processor manages two types of context:

    1. Workflow Context (set once during initialization):
       - vars_manager: Variable resolution system
       - nornir_manager: Nornir operations manager
       - tasks_catalog: Available tasks
       - filters_catalog: Available inventory filters
       - workflows_catalog: Available workflows

    2. Task-Specific Context (set once per task execution):
       - task_model: The current TaskModel being executed
       - hooks: List of Hook instances for this task

    The `context` property always returns the merged dictionary of both contexts.
    Task-specific context is set at task start and cleared at task completion.

    Hook Retrieval:
    ==============
    Hooks are retrieved from the current task-specific context. The processor
    calls hook methods at appropriate lifecycle points, injecting the merged
    context into each hook's _current_context before execution.
    """

    def __init__(self, workflow_context: dict[str, Any] | None = None):
        """Initialize the hook processor.

        Args:
            workflow_context: Optional workflow-level context to set during initialization
        """
        # workflow_context is set once and remains for the duration of NornFlowHookProcessor
        self.workflow_context = workflow_context or {}
        # task_specific_context is ephemeral and re-set with each new task
        self.task_specific_context = {}

    @property
    def workflow_context(self) -> dict[str, Any]:
        """Get the workflow-level context shared across all tasks.

        Returns:
            The workflow context dictionary
        """
        return self._workflow_context

    @workflow_context.setter
    def workflow_context(self, value: dict[str, Any]) -> None:
        """Set the workflow-level context shared across all tasks.

        Args:
            value: The workflow context dictionary containing vars_manager, catalogs, etc.
        """
        self._workflow_context = value

    @property
    def task_specific_context(self) -> dict[str, Any]:
        """Get the current task-specific context.

        Returns:
            The task-specific context dictionary
        """
        return self._task_specific_context

    @task_specific_context.setter
    def task_specific_context(self, value: dict[str, Any]) -> None:
        """Set the task-specific context for the current task.

        Args:
            value: The task-specific context containing task_model and hooks
        """
        self._task_specific_context = value

    @property
    def context(self) -> dict[str, Any]:
        """Get the combined context (workflow + task-specific).

        Returns:
            Merged dictionary of workflow and task-specific contexts
        """
        return {**self.workflow_context, **self.task_specific_context}

    @property
    def task_hooks(self) -> list["Hook"]:
        """Get active hooks for the current task.

        Returns:
            List of Hook instances for this task
        """
        return self.task_specific_context.get("hooks", [])

    @hook_delegator
    def task_started(self, task: Task) -> None:
        """Delegate to hooks' task_started methods."""

    @hook_delegator
    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Delegate to hooks' task_completed methods."""
        self.task_specific_context = {}

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
