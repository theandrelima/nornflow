"""Task Hook Framework for NornFlow.

This package provides a structured system for extending task behavior through hooks.
"""

from nornflow.hooks.base import (
    ConfigureTaskMixin,
    FilterHostsMixin,
    Hook,
    PostRunHook,
    PreRunHook,
    RunOncePerTaskMixin,
    RunPerHostMixin,
)
from nornflow.hooks.loader import load_hooks
from nornflow.hooks.registry import register_hook

__all__ = [
    "ConfigureTaskMixin",
    "FilterHostsMixin",
    "Hook",
    "PostRunHook",
    "PreRunHook",
    "RunOncePerTaskMixin",
    "RunPerHostMixin",
    "load_hooks",
    "register_hook",
]
