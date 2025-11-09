"""Task Hook Framework for NornFlow.

This package provides a structured system for extending task behavior through hooks.
"""

from nornflow.hooks.base import Hook
from nornflow.hooks.loader import load_hooks
from nornflow.hooks.registry import register_hook

__all__ = [
    "Hook",
    "load_hooks",
    "register_hook",
]
