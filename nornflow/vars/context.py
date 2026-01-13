from typing import Any, ClassVar

from nornflow.logger import logger


class NornFlowDeviceContext:
    """
    Maintains an isolated variable context for a specific device's NornFlow Variables.

    This class handles only the default namespace (NornFlow Variables) that are accessed
    without prefixes like {{ variable_name }}. It does NOT manage 'host.' or 'global.'
    namespaces, which are handled separately by other components.

    Each device gets its own view of variables from all sources within the NornFlow
    Default Namespace, enabling per-device isolation during task execution.

    It uses a copy-on-write strategy for shared initial state variables (CLI, Inline Workflow,
    Domain, Default, Environment) to minimize memory usage, only storing values that
    differ from the shared state at the device level. Runtime variables are always
    device-specific.

    This class provides:
    1. Memory-efficient variable storage using class-level shared initial state.
    2. Complete isolation between devices during parallel execution.
    3. Variable access methods that enforce the documented precedence order.
    4. Support for device-specific runtime variables.
    """

    _initial_cli_vars: ClassVar[dict[str, Any]] = {}
    _initial_workflow_inline_vars: ClassVar[dict[str, Any]] = {}
    _initial_domain_vars: ClassVar[dict[str, Any]] = {}
    _initial_default_vars: ClassVar[dict[str, Any]] = {}
    _initial_env_vars: ClassVar[dict[str, Any]] = {}
    _shared_state_initialized: ClassVar[bool] = False

    @classmethod
    def initialize_shared_state(
        cls,
        cli_vars: dict[str, Any],
        inline_workflow_vars: dict[str, Any],
        domain_vars: dict[str, Any],
        default_vars: dict[str, Any],
        env_vars: dict[str, Any],
    ) -> None:
        """
        Initialize the shared state for all future device contexts.

        This method should be called once at NornFlowVariablesManager initialization.
        All future DeviceContext instances will reference this shared state
        for their initial variable layers. Device-specific modifications
        are stored as overrides.

        Args:
            cli_vars: Variables from CLI arguments.
            inline_workflow_vars: Variables from the workflow definition's 'vars' section.
            domain_vars: Domain-specific default variables.
            default_vars: Global default variables.
            env_vars: Environment variables with NORNFLOW_VAR_ prefix.
        """
        cls._initial_cli_vars = cli_vars.copy()
        cls._initial_workflow_inline_vars = inline_workflow_vars.copy()
        cls._initial_domain_vars = domain_vars.copy()
        cls._initial_default_vars = default_vars.copy()
        cls._initial_env_vars = env_vars.copy()
        cls._shared_state_initialized = True
        logger.info("NornFlowDeviceContext shared state initialized.")

    def __init__(self, host_name: str) -> None:
        """
        Create a new device context.

        Args:
            host_name: Name of the device this context belongs to.

        Raises:
            RuntimeError: If shared state hasn't been initialized via initialize_shared_state.
        """
        if not self._shared_state_initialized:
            raise RuntimeError(
                "NornFlowDeviceContext shared state must be initialized by calling "
                "NornFlowDeviceContext.initialize_shared_state() before creating instances."
            )

        self.host_name = host_name

        self._cli_overrides: dict[str, Any] = {}
        self._workflow_inline_overrides: dict[str, Any] = {}
        self._domain_overrides: dict[str, Any] = {}
        self._default_overrides: dict[str, Any] = {}
        self._env_overrides: dict[str, Any] = {}

        self.runtime_vars: dict[str, Any] = {}

    @property
    def cli_vars(self) -> dict[str, Any]:
        """Get CLI variables with device-specific overrides applied."""
        if not self._cli_overrides:
            return self._initial_cli_vars

        result = self._initial_cli_vars.copy()
        result.update(self._cli_overrides)
        return result

    @cli_vars.setter
    def cli_vars(self, value: dict[str, Any]) -> None:
        """Set all CLI variables as overrides for this device."""
        self._cli_overrides = value.copy() if value else {}

    @property
    def workflow_inline_vars(self) -> dict[str, Any]:
        """Get inline workflow variables with device-specific overrides applied."""
        if not self._workflow_inline_overrides:
            return self._initial_workflow_inline_vars

        result = self._initial_workflow_inline_vars.copy()
        result.update(self._workflow_inline_overrides)
        return result

    @workflow_inline_vars.setter
    def workflow_inline_vars(self, value: dict[str, Any]) -> None:
        """Set all inline workflow variables as overrides for this device."""
        self._workflow_inline_overrides = value.copy() if value else {}

    @property
    def domain_vars(self) -> dict[str, Any]:
        """Get domain variables with device-specific overrides applied."""
        if not self._domain_overrides:
            return self._initial_domain_vars

        result = self._initial_domain_vars.copy()
        result.update(self._domain_overrides)
        return result

    @domain_vars.setter
    def domain_vars(self, value: dict[str, Any]) -> None:
        """Set all domain variables as overrides for this device."""
        self._domain_overrides = value.copy() if value else {}

    @property
    def default_vars(self) -> dict[str, Any]:
        """Get default variables with device-specific overrides applied."""
        if not self._default_overrides:
            return self._initial_default_vars

        result = self._initial_default_vars.copy()
        result.update(self._default_overrides)
        return result

    @default_vars.setter
    def default_vars(self, value: dict[str, Any]) -> None:
        """Set all default variables as overrides for this device."""
        self._default_overrides = value.copy() if value else {}

    @property
    def env_vars(self) -> dict[str, Any]:
        """Get environment variables with device-specific overrides applied."""
        if not self._env_overrides:
            return self._initial_env_vars

        result = self._initial_env_vars.copy()
        result.update(self._env_overrides)
        return result

    @env_vars.setter
    def env_vars(self, value: dict[str, Any]) -> None:
        """Set all environment variables as overrides for this device."""
        self._env_overrides = value.copy() if value else {}

    def _build_precedence_layers(self) -> list[dict[str, Any]]:
        """
        Build precedence layers in order from lowest to highest priority.

        This order is crucial for the flattening process where higher precedence
        layers (later in this list) will override keys from lower precedence layers.

        Returns ordered list of variable sources according to documented precedence:
        1. Environment Variables (lowest priority - precedence #6 in docs)
        2. Default Variables (precedence #5 in docs)
        3. Domain-specific Default Variables (precedence #4 in docs)
        4. Inline Workflow Variables (precedence #3 in docs)
        5. CLI Variables (precedence #2 in docs)
        6. Runtime Variables (highest priority - precedence #1 in docs)
        """
        return [
            self.env_vars,
            self.default_vars,
            self.domain_vars,
            self.workflow_inline_vars,
            self.cli_vars,
            self.runtime_vars,
        ]

    def get_flat_context(self) -> dict[str, Any]:
        """
        Get a flattened view of all NornFlow Default Namespace variables for this device,
        following the complete precedence hierarchy.

        Used when the complete variable context for the NornFlow Default Namespace
        is needed. This does not include 'host.' or 'global.' namespace variables,
        which are handled by other components.

        Returns:
            A dictionary representing the flattened variable context for this device,
            respecting the defined precedence order from environment variables
            (lowest) to runtime variables (highest).
        """
        precedence_layers = self._build_precedence_layers()

        flat_context = {}
        for layer in precedence_layers:
            flat_context.update(layer)

        logger.debug(f"Built flat context for host '{self.host_name}' with {len(flat_context)} variables.")
        return flat_context
