"""
Variable system exceptions.

This module defines exceptions specific to the variable management subsystem.
"""

from nornflow.exceptions import NornFlowError

###############################################################################
# VARIABLE EXCEPTIONS
###############################################################################


class VariableError(NornFlowError):
    """
    Base exception class for variable-related errors.

    These relate to variable loading, resolution, and access operations.
    """

    def __init__(self, message: str = "", var_name: str = "", host_name: str = ""):
        prefix = ""
        if var_name:
            prefix = f"Variable '{var_name}'"
            if host_name:
                prefix += f" for host '{host_name}'"
            prefix += ": "

        super().__init__(f"{prefix}{message}")
        self.var_name = var_name
        self.host_name = host_name


###############################################################################
# TEMPLATE EXCEPTIONS
###############################################################################


class TemplateError(VariableError):
    """
    Base exception class for template rendering errors.
    """

    def __init__(self, message: str = "", template: str = ""):
        # Truncate very long templates
        template_preview = template[:97] + "..." if len(template) > 100 else template  # noqa: PLR2004

        context = f" Template: '{template_preview}'" if template else ""
        super().__init__(f"{message}{context}")
        self.template = template
