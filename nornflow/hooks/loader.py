from typing import TYPE_CHECKING

from nornflow.hooks.base import PostRunHook, PreRunHook
from nornflow.hooks.registry import HOOK_REGISTRY

if TYPE_CHECKING:
    from nornflow.models import TaskModel


def load_hooks(task_model: "TaskModel") -> tuple[list[PreRunHook], list[PostRunHook]]:
    """Load hooks from a task model.
    
    Gets hook instances from the model's fields.
    
    Args:
        task_model: The TaskModel to load hooks for
        
    Returns:
        Tuple of (pre_hooks, post_hooks) lists
    """
    pre_hooks = []
    post_hooks = []
    
    # Load hooks for each type
    for hook_getter, hooks_list in [
        (task_model.get_pre_hooks, pre_hooks),
        (task_model.get_post_hooks, post_hooks),
    ]:
        for field_name in hook_getter():
            hook = getattr(task_model, field_name)
            if hook is not None:
                hooks_list.append(hook)
    
    return pre_hooks, post_hooks
