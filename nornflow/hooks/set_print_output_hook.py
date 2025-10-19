import logging
from typing import TYPE_CHECKING

from nornflow.hooks.base import (
    PreRunHook, 
    ConfigureTaskMixin, 
    RunOncePerTaskMixin,
    HookContext
)
from nornflow.hooks.registry import register_hook

if TYPE_CHECKING:
    from nornflow.models import TaskModel

logger = logging.getLogger(__name__)


@register_hook
class SetPrintOutputHook(PreRunHook, ConfigureTaskMixin, RunOncePerTaskMixin):
    """Hook that sets the print_output argument in task configuration.
    
    This hook uses:
    - ConfigureTaskMixin: To modify task configuration
    - RunOncePerTaskMixin: To run once for all hosts
        """
    
    hook_name = "output"
    
    def configure_task(self, task_model: "TaskModel", context: HookContext) -> None:
        """Modify task args to set print_output value."""
        if self.value is not None:
            if task_model.args is None:
                task_model.args = {}
            task_model.args['print_output'] = self.value
            logger.info(
                f"Set print_output to '{self.value}' for task '{task_model.name}'"
            )
