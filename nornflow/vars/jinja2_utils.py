from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

from nornflow.builtins.jinja2_filters import ALL_FILTERS
from nornflow.vars.exceptions import TemplateError, VariableError


class Jinja2EnvironmentManager:
    """Centralized Jinja2 environment management for NornFlow.

    Provides a single source of truth for Jinja2 environment configuration
    and template rendering with consistent error handling. All NornFlow custom
    filters are automatically registered during initialization.
    """

    def __init__(self):
        """Initialize the Jinja2 environment with NornFlow configuration.

        Creates a Jinja2 environment with:
        - StrictUndefined for catching missing variables
        - Loop controls extension
        - All NornFlow custom filters pre-registered
        """
        self.env = Environment(
            undefined=StrictUndefined,
            extensions=["jinja2.ext.loopcontrols"],
            autoescape=False,  # noqa: S701
        )

        for filter_name, filter_func in ALL_FILTERS.items():
            self.env.filters[filter_name] = filter_func

    def render_template(self, template_str: str, context: dict[str, Any], error_context: str = "") -> str:
        """Render a Jinja2 template string with the provided context.

        Args:
            template_str: The Jinja2 template string to render.
            context: Dictionary of variables to use in template rendering.
            error_context: Description of where this template is being used.

        Returns:
            The rendered template string.

        Raises:
            VariableError: If template contains undefined variables.
            TemplateError: If template has syntax errors or other rendering issues.
        """
        try:
            template = self.env.from_string(template_str)
            return template.render(context)
        except UndefinedError as e:
            context_info = f" ({error_context})" if error_context else ""
            raise VariableError(f"Undefined variable in template{context_info}: {e}") from e
        except TemplateSyntaxError as e:
            context_info = f" ({error_context})" if error_context else ""
            raise TemplateError(f"Template syntax error{context_info}: {e}") from e
        except Exception as e:
            context_info = f" ({error_context})" if error_context else ""
            raise TemplateError(f"Template rendering error{context_info}: {e}") from e


def render_string(template_str: str, context: dict[str, Any], error_context: str = "") -> str:
    """Convenience function for simple string rendering.

    Args:
        template_str: The template string to render.
        context: Dictionary of variables for rendering.
        error_context: Description for error messages.

    Returns:
        The rendered string.
    """
    manager = Jinja2EnvironmentManager()
    return manager.render_template(template_str, context, error_context)


def render_data_recursive(data: Any, context: dict[str, Any], error_context: str = "") -> Any:
    """Recursively render Jinja2 templates in data structures.

    Args:
        data: The data structure to process (dict, list, string, etc.).
        context: Dictionary of variables for rendering.
        error_context: Description for error messages.

    Returns:
        The data structure with all templates rendered.
    """
    manager = Jinja2EnvironmentManager()
    return _render_data_recursive_impl(data, context, manager, error_context)


def _render_data_recursive_impl(
    data: Any, context: dict[str, Any], manager: Jinja2EnvironmentManager, error_context: str
) -> Any:
    """Implementation of recursive data rendering.

    Args:
        data: The data to process.
        context: Variables for rendering.
        manager: The Jinja2 manager instance.
        error_context: Description for error messages.

    Returns:
        The processed data.
    """
    if isinstance(data, str):
        if any(marker in data for marker in ["{{", "{%", "{#"]):
            return manager.render_template(data, context, error_context)
        return data
    if isinstance(data, dict):
        return {k: _render_data_recursive_impl(v, context, manager, error_context) for k, v in data.items()}
    if isinstance(data, list):
        return [_render_data_recursive_impl(item, context, manager, error_context) for item in data]
    return data
