from contextvars import ContextVar, Token

BUILTIN_NAMESPACE = "nornflow"
LOCAL_NAMESPACE = "local"
TIER_BUILTIN = "builtin"
TIER_LOCAL = "local"
TIER_PACKAGE = "package"

_hook_registration: ContextVar[tuple[str, str] | None] = ContextVar("hook_registration", default=None)


def set_hook_registration(namespace: str, tier: str) -> Token:
    """Set namespace and tier for hook class registration during module import.

    Args:
        namespace: Catalog namespace (e.g. ``local`` or a package name).
        tier: Registration tier (``builtin``, ``local``, or ``package``).

    Returns:
        ContextVar token for resetting the context.
    """
    return _hook_registration.set((namespace, tier))


def reset_hook_registration(token: Token) -> None:
    """Reset hook registration context to its previous value.

    Args:
        token: Token returned by ``set_hook_registration``.
    """
    _hook_registration.reset(token)


def get_hook_registration() -> tuple[str, str] | None:
    """Return the active hook registration namespace and tier, if any."""
    return _hook_registration.get()
