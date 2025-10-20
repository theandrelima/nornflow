from nornflow.hooks.exceptions import HookRegistrationError

HOOK_REGISTRY: dict[str, type[object]] = {}


def register_hook(hook_class: type[object]) -> type[object]:
    """
    Register a hook class in the global registry.

    Args:
        hook_class: The hook class to register

    Returns:
        The hook class (for decorator usage)
    """
    if not hasattr(hook_class, "hook_name") or not hook_class.hook_name:
        raise HookRegistrationError(
            f"Hook class {hook_class.__name__} must define a hook_name class attribute"
        )

    HOOK_REGISTRY[hook_class.hook_name] = hook_class
    return hook_class
