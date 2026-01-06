"""Jinja2-specific exceptions for NornFlow."""

from nornflow.exceptions import NornFlowError


class Jinja2ServiceError(NornFlowError):
    """Base exception for Jinja2Service-related errors."""


class TemplateError(Jinja2ServiceError):
    """
    Exception class for template rendering errors.
    """

    def __init__(self, message: str = "", template: str = ""):
        # Truncate very long templates
        template_preview = template[:97] + "..." if len(template) > 100 else template  # noqa: PLR2004

        context = f" Template: '{template_preview}'" if template else ""
        super().__init__(f"{message}{context}")
        self.template = template


class TemplateValidationError(TemplateError):
    """Exception raised when template validation fails."""
