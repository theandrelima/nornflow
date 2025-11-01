"""
NornFlow Variables System

This package provides the variable management functionality for NornFlow, including:
- Variable resolution with defined precedence order
- Per-device isolation
- Memory-efficient variable storage
- Template rendering with Jinja2
"""

from nornflow.vars.context import NornFlowDeviceContext
from nornflow.vars.exceptions import TemplateError, VariableError
from nornflow.vars.manager import NornFlowVariablesManager
from nornflow.vars.processors import NornFlowVariableProcessor
from nornflow.vars.proxy import NornirHostProxy
from nornflow.vars.constants import JINJA2_MARKERS

__all__ = [
    "NornFlowDeviceContext",
    "NornFlowVariableProcessor",
    "NornFlowVariablesManager",
    "NornirHostProxy",
    "TemplateError",
    "VariableError",
    "JINJA2_MARKERS",
]
