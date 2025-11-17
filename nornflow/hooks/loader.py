from typing import Any, TYPE_CHECKING

from nornflow.hooks.base import HOOK_REGISTRY

if TYPE_CHECKING:
    from nornflow.hooks import Hook


def load_hooks(hooks_dict: dict[str, Any]) -> list["Hook"]:
    """Load hooks from a hooks dictionary.

    Processes the hooks configuration dict and returns instantiated Hook instances.

    Args:
        hooks_dict: Dictionary mapping hook names to hook configurations

    Returns:
        List of instantiated Hook instances
    """
    hooks = []
    if not hooks_dict:
        return hooks

    for hook_name, hook_config in hooks_dict.items():
        hook_class = HOOK_REGISTRY.get(hook_name)
        if hook_class:
            hook_instance = hook_class(hook_config)
            hooks.append(hook_instance)

    return hooks
