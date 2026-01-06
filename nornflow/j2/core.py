from functools import lru_cache
from threading import Lock
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

from nornflow.builtins.jinja2_filters import ALL_BUILTIN_J2_FILTERS
from nornflow.j2.constants import JINJA2_MARKERS, TRUTHY_STRING_VALUES
from nornflow.j2.exceptions import Jinja2ServiceError, TemplateError, TemplateValidationError
from nornflow.catalogs import CallableCatalog


class Jinja2Service:
    """Centralized Jinja2 management for NornFlow.

    Provides a single, cached Jinja2 environment and standardized
    template operations used throughout NornFlow.

    This service is a singleton that:
    - Maintains a single Jinja2 environment instance
    - Provides thread-safe template compilation and caching
    - Offers standardized resolution methods
    - Centralizes error handling
    - Supports registration of custom filters from external directories
    """

    _instance = None
    _lock = Lock()
    _initialized = False
    _custom_filters_registered = False

    @classmethod
    def _initialize_environment(cls, instance) -> None:
        """Initialize the Jinja2 environment and register filters for the instance.

        Args:
            instance: The Jinja2Service instance to initialize.
        """
        instance.environment = Environment(
            undefined=StrictUndefined,
            extensions=["jinja2.ext.loopcontrols"],
            # Autoescape disabled as NornFlow generates network configs, not HTML;
            # escaping would break outputs like XML/JSON.
            autoescape=False,  # noqa: S701
        )

        # Register all NornFlow filters
        instance.environment.filters.update(ALL_BUILTIN_J2_FILTERS)

    @classmethod
    def register_custom_filters(cls, local_j2_filters_dirs: list[str]) -> None:
        """Register custom Jinja2 filters from specified directories.

        This method can be called externally (e.g., from NornFlow initialization)
        to register custom filters into the Jinja2 environment. It ensures
        registration happens only once and after the environment is initialized.

        Args:
            local_j2_filters_dirs: List of directory paths to scan for custom filters.
        """
        if cls._custom_filters_registered:
            return  # Already registered

        instance = cls()  # Ensure environment is initialized
        catalog = CallableCatalog("custom_j2_filters")
        
        for dir_path in local_j2_filters_dirs:
            catalog.discover_items_in_dir(dir_path, predicate=callable)
        
        # Update the environment's filters with discovered items
        instance.environment.filters.update(catalog)

        cls._custom_filters_registered = True

    @classmethod
    def get_registered_j2_filters(cls) -> dict[str, Any]:
        """Retrieve the list of registered Jinja2 filters for display purposes.

        This is used by the CLI show command to list available filters.

        Returns:
            Dictionary of filter names to their callable functions.
        """
        instance = cls()
        return dict(instance.environment.filters)

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._initialize_environment(cls._instance)
                cls._initialized = True
        return cls._instance

    @property
    def environment(self) -> Environment:
        """Get the cached Jinja2 environment."""
        return self._environment

    @environment.setter
    def environment(self, value: Environment) -> None:
        """Set the Jinja2 environment."""
        if not isinstance(value, Environment):
            raise Jinja2ServiceError(f"Expected Environment instance, got {type(value).__name__}")
        self._environment = value

    # @lru_cache is safe here despite B019: as a singleton, only one instance exists,
    # so no risk of accumulating references that prevent garbage collection. Templates
    # are cached for the app's lifetime anyway, aligning with singleton behavior.
    @lru_cache(maxsize=256)  # noqa: B019
    def compile_template(self, template_str: str) -> Any:
        """Compile and cache a template string.

        Args:
            template_str: The template string to compile

        Returns:
            Compiled Template object

        Raises:
            TemplateValidationError: If template has syntax errors
        """
        try:
            return self._environment.from_string(template_str)
        except Exception as e:
            raise TemplateValidationError(f"Template compilation failed: {e}", template=template_str) from e

    def resolve_string(self, template_str: str, context: dict[str, Any], error_context: str = "") -> str:
        """Resolve a Jinja2 template string.

        Args:
            template_str: The template string to resolve
            context: Variables for resolution
            error_context: Description for error messages

        Returns:
            Resolved string

        Raises:
            TemplateError: If resolution fails
        """
        if not isinstance(template_str, str):
            raise TemplateValidationError(
                f"Expected string for 'template_str', got {type(template_str).__name__}"
            )

        if not self.is_template(template_str):
            return template_str

        try:
            template = self.compile_template(template_str)
            return template.render(context)
        except UndefinedError as e:
            context_info = f" ({error_context})" if error_context else ""
            raise TemplateError(f"Undefined variable in template{context_info}: {e}") from e
        except TemplateSyntaxError as e:
            context_info = f" ({error_context})" if error_context else ""
            raise TemplateError(f"Template syntax error{context_info}: {e}") from e
        except Exception as e:
            context_info = f" ({error_context})" if error_context else ""
            raise TemplateError(f"Template rendering error{context_info}: {e}") from e

    def resolve_to_bool(self, value: Any, context: dict[str, Any]) -> bool:
        """Resolve a value to boolean, handling templates and literals.

        Args:
            value: Value to resolve (bool, string, or template)
            context: Variables for template resolution

        Returns:
            Boolean result
        """
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            # Check if it's a template
            if self.is_template(value):
                resolved = self.resolve_string(value, context)
                return self.to_bool(resolved)
            # Plain string literal
            return self.to_bool(value)

        return bool(value)

    def resolve_data(self, data: Any, context: dict[str, Any], error_context: str = "") -> Any:
        """Recursively resolve templates in data structures.

        Args:
            data: Data structure to process
            context: Variables for resolution
            error_context: Description for error messages

        Returns:
            Data with all templates resolved
        """
        return self._render_data_recursive_impl(data, context, error_context)

    def validate_template(self, template_str: str) -> tuple[bool, str]:
        """Validate template syntax without rendering.

        Args:
            template_str: Template to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.compile_template(template_str)
            return (True, "")
        except Exception as e:
            return (False, str(e))

    def is_template(self, value: str) -> bool:
        """Check if string contains Jinja2 markers.

        Args:
            value: String to check

        Returns:
            True if string contains Jinja2 markers
        """
        return any(marker in value for marker in JINJA2_MARKERS)

    def to_bool(self, value: Any) -> bool:
        """Convert value to boolean using NornFlow conventions.

        Args:
            value: Value to convert

        Returns:
            Boolean result
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in TRUTHY_STRING_VALUES
        return bool(value)

    def _render_data_recursive_impl(self, data: Any, context: dict[str, Any], error_context: str) -> Any:
        """Implementation of recursive data rendering.

        Args:
            data: The data to process
            context: Variables for rendering
            error_context: Description for error messages

        Returns:
            The processed data
        """
        if isinstance(data, str):
            if self.is_template(data):
                return self.resolve_string(data, context, error_context)
            return data
        if isinstance(data, dict):
            return {k: self._render_data_recursive_impl(v, context, error_context) for k, v in data.items()}
        # Handle both lists and tuples, and normalize to list.
        # This preserves behavior where YAML-defined lists remain lists,
        # even if converted to tuples for internal use (e.g., hashability).
        if isinstance(data, (list, tuple)):
            return [self._render_data_recursive_impl(item, context, error_context) for item in data]
        return data