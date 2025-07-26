"""
NornFlow Variables System

This package provides the variable management functionality for NornFlow, including:
- Variable resolution with defined precedence order
- Per-device isolation
- Memory-efficient variable storage
- Template rendering with Jinja2
"""

from nornflow.vars.context import NornFlowDeviceContext
from nornflow.vars.exceptions import (
    NornFlowVarsError,
    VariableDirectoryError,
    VariableLoadError,
    VariableNotFoundError,
    VariableResolutionError,
)
from nornflow.vars.manager import NornFlowVariablesManager
from nornflow.vars.processors import NornFlowVariableProcessor
from nornflow.vars.proxy import NornirHostProxy

__all__ = [
    "NornFlowDeviceContext",
    "NornFlowVariableProcessor",
    "NornFlowVariablesManager",
    "NornFlowVarsError",
    "NornirHostProxy",
    "VariableDirectoryError",
    "VariableLoadError",
    "VariableNotFoundError",
    "VariableResolutionError",
]
