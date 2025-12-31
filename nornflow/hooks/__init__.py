"""Task Hook Framework for NornFlow.

Hooks provide a clean way to extend task behavior without modifying task code.
Simply inherit from Hook and define a hook_name - registration is automatic!
"""

from nornflow.hooks.base import Hook, HOOK_REGISTRY
from nornflow.hooks.loader import load_hooks
from nornflow.hooks.mixins import Jinja2ResolvableMixin

__all__ = [
    "HOOK_REGISTRY",
    "Hook",
    "Jinja2ResolvableMixin",
    "load_hooks",
]
