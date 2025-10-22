import logging
from typing import TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Task

from nornflow.hooks import Hook, register_hook
from nornflow.hooks.exceptions import HookValidationError

if TYPE_CHECKING:
    from nornflow.models import TaskModel

logger = logging.getLogger(__name__)


@register_hook
class SetToHook(Hook):
    """Hook that stores task results in runtime variables.

    This hook captures task results and stores them in NornFlow's runtime
    variable namespace for the current host. It runs per host to handle
    individual results.

    Attributes:
        hook_name: "set_to"
        run_once_per_task: False (executes per host)
    """

    hook_name = "set_to"
    run_once_per_task = False

    def validate_task_compatibility(self, task_model: "TaskModel") -> None:
        """Validate that set_to is not used with incompatible tasks."""
        invalid_tasks = {"set", "echo", "set_to"}
        if task_model.name in invalid_tasks:
            raise HookValidationError(
                f"Hook '{self.__class__.__name__}' cannot be used with task '{task_model.name}'. "
                f"Incompatible tasks: {invalid_tasks}"
            )

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Store the task result in a runtime variable for this host."""
        if self.value is None or result is None:
            return

        context = self.get_context(task)
        vars_manager = context.get("vars_manager")

        if vars_manager:
            vars_manager.set_runtime_variable(self.value, result, host.name)
            logger.debug(f"Stored result in variable '{self.value}' for host '{host.name}'")