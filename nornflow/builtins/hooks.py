import logging
from typing import TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, AggregatedResult

from nornflow.hooks import (
    PreRunHook,
    PostRunHook,
    ConfigureTaskMixin,
    RunOncePerTaskMixin,
    RunPerHostMixin,
)
from nornflow.hooks.registry import register_hook

if TYPE_CHECKING:
    from nornflow.models import TaskModel
    from nornflow.hooks import HookContext

logger = logging.getLogger(__name__)


@register_hook
class SetPrintOutputHook(PreRunHook, ConfigureTaskMixin, RunOncePerTaskMixin):
    """Hook that sets the print_output argument in task configuration.

    This hook uses:
    - ConfigureTaskMixin: To modify task configuration
    - RunOncePerTaskMixin: To run once for all hosts
    """

    hook_name = "output"

    def configure_task(self, task_model: "TaskModel", context: "HookContext") -> None:
        """Modify task args to set print_output value."""
        if self.value is not None:
            if task_model.args is None:
                task_model.args = {}
            task_model.args["print_output"] = self.value
            logger.info(f"Set print_output to '{self.value}' for task '{task_model.name}'")


@register_hook
class SetToHook(PostRunHook, RunPerHostMixin):
    """Hook that stores task results in runtime variables.

    Uses:
    - RunPerHostMixin: To process each host's result individually
    """

    hook_name = "set_to"

    def process_results(
        self,
        task_model: "TaskModel",
        results: AggregatedResult | tuple[Host, MultiResult],
        context: "HookContext",
    ) -> None:
        """Store the task result in a runtime variable for this host."""
        if self.value is None:
            return

        # Since we use RunPerHostMixin, results is a tuple
        host, result = results

        if result is None:
            return

        variable_name = self.value
        context.vars_manager.set_runtime_variable(variable_name, result, host.name)
        logger.info(
            f"Stored result from task '{task_model.name}' "
            f"into variable '{variable_name}' for host '{host.name}'"
        )
