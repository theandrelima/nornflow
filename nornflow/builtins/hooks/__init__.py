"""NornFlow built-in hooks subpackage.

This subpackage contains built-in hook implementations for NornFlow.
"""

from .output import SetPrintOutputHook
from .predicate import PredicateHook, SkipHostError
from .set_to import SetToHook

__all__ = ["SetPrintOutputHook", "SetToHook", "PredicateHook", "SkipHostError"]