from functools import lru_cache
from threading import Lock
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

from nornflow.builtins.jinja2_filters import ALL_BUILTIN_J2_FILTERS
from nornflow.catalogs import CallableCatalog
from nornflow.j2.constants import JINJA2_MARKERS, TRUTHY_STRING_VALUES
from nornflow.j2.exceptions import Jinja2ServiceError, TemplateError, TemplateValidationError
from nornflow.logger import logger
from nornflow.settings import NornFlowSettings
from nornflow.utils import is_public_callable


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
    - Assembles and exposes a shared catalog of J2 filters (built-ins + custom)
    """

    _instance = None
    _lock = Lock()
    _initialized = False

    @classmethod
    def _initialize_environment(cls, instance) -> None:
        """Initialize the Jinja2 environment and J2 filters catalog for the instance.

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

        instance._j2_filters_catalog = CallableCatalog("j2_filters")  # noqa: SLF001

        # Add ALL_BUILTIN_J2_FILTERS to instances j2_filters_catalog
        for name, func in ALL_BUILTIN_J2_FILTERS.items():
            instance.j2_filters_catalog.register(name, func, module_name="nornflow.builtins.jinja2_filters")

        # Update environment filters from catalog to ensure consistency
        instance.environment.filters.update(instance.j2_filters_catalog)

    @classmethod
    def initialize_with_settings(cls, settings: NornFlowSettings) -> None:
        """Initialize the service with NornFlow settings, registering custom filters.

        This method configures the Jinja2Service singleton using the provided settings,
        ensuring custom filters from local_j2_filters directories are registered.

        Args:
            settings: NornFlowSettings instance containing configuration.
        """
        cls.register_custom_filters(settings.local_j2_filters)

    @classmethod
    def register_custom_filters(cls, local_j2_filters_dirs: list[str]) -> None:
        """Register custom Jinja2 filters from specified directories into the catalog.

        This method can be called to register custom filters into the Jinja2
        environment and catalog. It allows multiple calls, with later calls overriding
        previous filters.

        Args:
            local_j2_filters_dirs: List of directory paths to scan for custom filters.
        """
        instance = cls()

        for dir_path in local_j2_filters_dirs:
            instance._j2_filters_catalog.discover_items_in_dir(dir_path, predicate=is_public_callable)

        # Update environment filters from catalog to reflect changes
        instance.environment.filters.update(instance._j2_filters_catalog)

    @classmethod
    def get_registered_j2_filters(cls) -> dict[str, Any]:
        """Retrieve the list of registered Jinja2 filters for display purposes.

        This is used by the CLI show command to list available filters.

        Returns:
            Dictionary of filter names to their callable functions.
        """
        instance = cls()
        return dict(instance.environment.filters)

    @property
    def j2_filters_catalog(self) -> CallableCatalog:
        """Get the shared J2 filters catalog (built-ins + custom).

        This catalog is assembled internally and cannot be set directly.

        Returns:
            CallableCatalog: The shared catalog of J2 filters.
        """
        return self._j2_filters_catalog

    @j2_filters_catalog.setter
    def j2_filters_catalog(self, value: Any) -> None:
        """Prevent setting the J2 filters catalog directly.

        Raises:
            Jinja2ServiceError: Always raised to prevent direct setting.
        """
        raise Jinja2ServiceError("J2 filters catalog cannot be set directly.")

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
            compiled = self._environment.from_string(template_str)
            logger.debug(f"Compiled template (length={len(template_str)})")
            return compiled
        except Exception as e:
            logger.exception(f"Unexpected error compiling template (length={len(template_str)}): {e}")
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
            result = template.render(context)
            logger.debug(f"Resolved template: input_len={len(template_str)}, output_len={len(result)}")
            return result
        except UndefinedError as e:
            context_info = f" ({error_context})" if error_context else ""
            raise TemplateError(f"Undefined variable in template{context_info}: {e}") from e
        except TemplateSyntaxError as e:
            context_info = f" ({error_context})" if error_context else ""
            raise TemplateError(f"Template syntax error{context_info}: {e}") from e
        except Exception as e:
            context_info = f" ({error_context})" if error_context else ""
            logger.exception(
                f"Unexpected error resolving template (length={len(template_str)}){context_info}: {e}"
            )
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
        result = self._render_data_recursive_impl(data, context, error_context)
        logger.debug(f"Resolved data structure with {len(str(data)) if data else 0} chars.")
        return result

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
