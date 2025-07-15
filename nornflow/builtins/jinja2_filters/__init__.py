"""Jinja2 filters for NornFlow variable resolution."""

from nornflow.builtins.jinja2_filters.custom_filters import CUSTOM_FILTERS
from nornflow.builtins.jinja2_filters.py_wrapper_filters import PY_WRAPPER_FILTERS

# Combine all filters into a single registry
ALL_FILTERS = {**PY_WRAPPER_FILTERS, **CUSTOM_FILTERS}

__all__ = [
    "ALL_FILTERS",
    "PY_WRAPPER_FILTERS", 
    "CUSTOM_FILTERS",
]