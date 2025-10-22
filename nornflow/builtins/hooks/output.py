import logging

from nornir.core.task import Task

from nornflow.hooks import Hook, register_hook

logger = logging.getLogger(__name__)


@register_hook
class SetPrintOutputHook(Hook):
    """Hook that controls output printing for tasks.

    This hook sets the 'print_output' parameter in task arguments to control
    whether task results are printed. It runs once per task across all hosts.

    Attributes:
        hook_name: "output"
        run_once_per_task: True (executes once per task)
    """

    hook_name = "output"
    run_once_per_task = True

    def task_started(self, task: Task) -> None:
        """Set print_output in task params for the task."""
        if self.value is not None:
            task.params["print_output"] = self.value
            logger.debug(f"Set print_output={self.value} for task via hook")
