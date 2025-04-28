import logging
from typing import Any

logger = logging.getLogger(__name__)

class DeviceContext:
    """
    Maintains an isolated variable context for a specific device.
    
    Each device gets its own copy of variables from all sources,
    enabling per-device isolation during task execution.
    
    Uses shared initial state for all devices with per-variable overrides
    to minimize memory usage, only storing values that differ from the shared state.
    
    This class provides:
    1. Memory-efficient variable storage using class-level shared state
    2. Complete isolation between devices during parallel execution
    3. Variable access methods that enforce precedence order
    4. Separation of environment variables to ensure correct precedence (lowest priority)
    5. Support for device-specific runtime variables
    6. Per-variable granularity for overrides to maximize memory sharing
    
    Note: This class only manages static variable sources (1-6 and 8 in precedence order)
    and does NOT directly handle Nornir inventory variables (source #7). That's handled by
    VariableManager using NornirHostProxy.
    
    The separation of environment variables in get_flat_context_without_env() is 
    intentional to allow VariableManager to insert Nornir variables (source #7) 
    between higher precedence sources and environment variables, maintaining the
    documented precedence order.
    """
    
    # Class variables to store shared initial state for all device contexts
    _initial_cli_vars: dict[str, Any] = {}
    _initial_workflow_inline_vars: dict[str, Any] = {}
    _initial_workflow_paired_vars: dict[str, Any] = {}
    _initial_domain_vars: dict[str, Any] = {}
    _initial_default_vars: dict[str, Any] = {}
    _initial_env_vars: dict[str, Any] = {}
    _shared_state_initialized: bool = False
    
    @classmethod
    def initialize_shared_state(
        cls,
        cli_vars: dict[str, Any],
        workflow_vars: dict[str, Any],
        domain_vars: dict[str, Any],
        default_vars: dict[str, Any],
        env_vars: dict[str, Any]
    ) -> None:
        """
        Initialize the shared state for all future device contexts.
        
        This method should be called once at VariableManager initialization.
        All future DeviceContext instances will reference this shared state
        until they need to modify a variable, at which point they'll create
        their own device-specific override.
        
        Args:
            cli_vars: Variables from CLI arguments
            workflow_vars: Variables from the workflow definition
            domain_vars: Domain-specific variables
            default_vars: Default variables shared by all workflows
            env_vars: Environment variables with NORNFLOW_VAR prefix
        """
        cls._initial_cli_vars = cli_vars.copy()
        cls._initial_workflow_inline_vars = workflow_vars.get("inline", {}).copy()
        cls._initial_workflow_paired_vars = workflow_vars.get("paired", {}).copy()
        cls._initial_domain_vars = domain_vars.copy()
        cls._initial_default_vars = default_vars.copy()
        cls._initial_env_vars = env_vars.copy()
        cls._shared_state_initialized = True
    
    def __init__(self, host_name: str) -> None:
        """
        Create a new device context with reference to shared initial state.
        
        Args:
            host_name: Name of the device this context belongs to
            
        Raises:
            RuntimeError: If shared state hasn't been initialized
        """
        if not self.__class__._shared_state_initialized:
            raise RuntimeError("DeviceContext shared state must be initialized before creating instances")
            
        self.host_name = host_name
        
        # Device-specific overrides - only store variables that differ from shared state
        self._cli_overrides: dict[str, Any] = {}
        self._workflow_inline_overrides: dict[str, Any] = {}
        self._workflow_paired_overrides: dict[str, Any] = {}
        self._domain_overrides: dict[str, Any] = {}
        self._default_overrides: dict[str, Any] = {}
        self._env_overrides: dict[str, Any] = {}
        
        # Runtime vars are always device-specific (no shared state)
        self.runtime_vars: dict[str, Any] = {}
    
    # Methods for setting individual variables within categories
    
    def set_cli_var(self, name: str, value: Any) -> None:
        """Set a single CLI variable override."""
        self._cli_overrides[name] = value
        
    def set_workflow_inline_var(self, name: str, value: Any) -> None:
        """Set a single inline workflow variable override."""
        self._workflow_inline_overrides[name] = value
        
    def set_workflow_paired_var(self, name: str, value: Any) -> None:
        """Set a single paired workflow variable override."""
        self._workflow_paired_overrides[name] = value
        
    def set_domain_var(self, name: str, value: Any) -> None:
        """Set a single domain variable override."""
        self._domain_overrides[name] = value
        
    def set_default_var(self, name: str, value: Any) -> None:
        """Set a single default variable override."""
        self._default_overrides[name] = value
        
    def set_env_var(self, name: str, value: Any) -> None:
        """Set a single environment variable override."""
        self._env_overrides[name] = value
        
    # Properties that implement per-variable override behavior
    
    @property
    def cli_vars(self) -> dict[str, Any]:
        """Get CLI variables with device-specific overrides applied."""
        if not self._cli_overrides:  # No overrides, return shared state directly
            return self.__class__._initial_cli_vars
        
        # Merge shared state with overrides
        result = self.__class__._initial_cli_vars.copy()
        result.update(self._cli_overrides)
        return result
        
    @cli_vars.setter
    def cli_vars(self, value: dict[str, Any]) -> None:
        """Set all CLI variables as overrides."""
        self._cli_overrides = value.copy() if value else {}
        
    @property
    def workflow_inline_vars(self) -> dict[str, Any]:
        """Get inline workflow variables with device-specific overrides applied."""
        if not self._workflow_inline_overrides:
            return self.__class__._initial_workflow_inline_vars
        
        result = self.__class__._initial_workflow_inline_vars.copy()
        result.update(self._workflow_inline_overrides)
        return result
        
    @workflow_inline_vars.setter
    def workflow_inline_vars(self, value: dict[str, Any]) -> None:
        """Set all inline workflow variables as overrides."""
        self._workflow_inline_overrides = value.copy() if value else {}
        
    @property
    def workflow_paired_vars(self) -> dict[str, Any]:
        """Get paired workflow variables with device-specific overrides applied."""
        if not self._workflow_paired_overrides:
            return self.__class__._initial_workflow_paired_vars
        
        result = self.__class__._initial_workflow_paired_vars.copy()
        result.update(self._workflow_paired_overrides)
        return result
        
    @workflow_paired_vars.setter
    def workflow_paired_vars(self, value: dict[str, Any]) -> None:
        """Set all paired workflow variables as overrides."""
        self._workflow_paired_overrides = value.copy() if value else {}
        
    @property
    def domain_vars(self) -> dict[str, Any]:
        """Get domain variables with device-specific overrides applied."""
        if not self._domain_overrides:
            return self.__class__._initial_domain_vars
        
        result = self.__class__._initial_domain_vars.copy()
        result.update(self._domain_overrides)
        return result
        
    @domain_vars.setter
    def domain_vars(self, value: dict[str, Any]) -> None:
        """Set all domain variables as overrides."""
        self._domain_overrides = value.copy() if value else {}
        
    @property
    def default_vars(self) -> dict[str, Any]:
        """Get default variables with device-specific overrides applied."""
        if not self._default_overrides:
            return self.__class__._initial_default_vars
        
        result = self.__class__._initial_default_vars.copy()
        result.update(self._default_overrides)
        return result
        
    @default_vars.setter
    def default_vars(self, value: dict[str, Any]) -> None:
        """Set all default variables as overrides."""
        self._default_overrides = value.copy() if value else {}
        
    @property
    def env_vars(self) -> dict[str, Any]:
        """Get environment variables with device-specific overrides applied."""
        if not self._env_overrides:
            return self.__class__._initial_env_vars
        
        result = self.__class__._initial_env_vars.copy()
        result.update(self._env_overrides)
        return result
        
    @env_vars.setter
    def env_vars(self, value: dict[str, Any]) -> None:
        """Set all environment variables as overrides."""
        self._env_overrides = value.copy() if value else {}
        
    def get_flat_context_without_env(self) -> dict[str, Any]:
        """
        Get a flattened view of all variables following precedence rules,
        excluding environment variables which have lowest precedence.
        """
        flat_context = {}
        
        flat_context.update(self.default_vars)
        flat_context.update(self.domain_vars)
        flat_context.update(self.workflow_paired_vars)
        flat_context.update(self.workflow_inline_vars)
        flat_context.update(self.runtime_vars)
        flat_context.update(self.cli_vars)
        return flat_context
        
    def get_flat_context(self) -> dict[str, Any]:
        """
        Get a flattened view of all variables including env vars.
        """
        flat_context = {}
        
        flat_context.update(self.env_vars)
        flat_context.update(self.default_vars)
        flat_context.update(self.domain_vars)
        flat_context.update(self.workflow_paired_vars)
        flat_context.update(self.workflow_inline_vars)
        flat_context.update(self.runtime_vars)
        flat_context.update(self.cli_vars)
        return flat_context