"""
NornFlow Variables System

This package provides the variable management functionality for NornFlow, including:
- Variable resolution with defined precedence order
- Per-device isolation
- Memory-efficient variable storage
- Template rendering with Jinja2
"""

from nornflow.vars.constants import JINJA2_MARKERS
from nornflow.vars.context import NornFlowDeviceContext
from nornflow.vars.exceptions import TemplateError, VariableError
from nornflow.vars.jinja2_utils import Jinja2EnvironmentManager
from nornflow.vars.manager import NornFlowVariablesManager
from nornflow.vars.processors import NornFlowVariableProcessor
from nornflow.vars.proxy import NornirHostProxy

__all__ = [
    "JINJA2_MARKERS",
    "Jinja2EnvironmentManager",
    "NornFlowDeviceContext",
    "NornFlowVariableProcessor",
    "NornFlowVariablesManager",
    "NornirHostProxy",
    "TemplateError",
    "VariableError",
]
