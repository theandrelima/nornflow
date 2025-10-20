"""Task Hook Framework for NornFlow.

This package provides a structured system for extending task behavior through hooks.
"""

from nornflow.hooks.base import (
    Hook,
    PostRunHook,
    PreRunHook,
    RunPerHostMixin,
    FilterHostsMixin,
    ConfigureTaskMixin,
    RunOncePerTaskMixin,
)
from nornflow.hooks.loader import load_hooks
from nornflow.hooks.registry import register_hook

__all__ = [
    "Hook",
    "PostRunHook",
    "PreRunHook",
    "load_hooks",
    "register_hook",
    "RunPerHostMixin",
    "FilterHostsMixin",
    "ConfigureTaskMixin",
    "RunOncePerTaskMixin",
]
