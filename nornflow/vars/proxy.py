from typing import Any

class NornirHostProxy:
    """
    Proxy object for accessing host-specific variables in Nornir inventory.
    
    This class implements a proxy pattern to provide direct access to host data
    without copying it, maintaining high performance even with large inventories
    and many tasks. It works by:
    
    1. Maintaining a reference to the current host being processed (set by NornFlowVariableProcessor)
    2. Dynamically accessing host attributes and data dictionary when requested
    3. Providing a clean template interface for host variables
    
    Design rationale:
    - Avoids overhead of loading host data for each task execution
    - Works with Nornir's parallel execution model via thread-local context
    - Maintains a consistent API with other variable sources
    - Allows transparent access to host attributes and data dictionary
    
    The proxy allows variable resolution to be context-aware during parallel task
    execution, with each host getting its own variable context.
    """
    
    def __init__(self) -> None:
        """Initialize the proxy with no current host."""
        self._current_host = None
        
    @property
    def current_host(self) -> Any:
        """Get the current host."""
        return self._current_host
        
    @current_host.setter
    def current_host(self, host: Any) -> None:
        """Set the current host."""
        self._current_host = host
    
    def __getattr__(self, name: str) -> Any:
        """
        Access host attributes and data directly.
        
        Args:
            name: The attribute or data key to retrieve
            
        Returns:
            The value from the host's attributes or data
            
        Raises:
            AttributeError: When no host context is set or attribute not found
        """
        if not self.current_host:
            raise AttributeError("No current host context")
        
        # Try to get the value from the host
        return self._get_host_value(name)
    
    def _get_host_value(self, name: str) -> Any:
        """
        Get a value from the host, checking both data dict and attributes.
        
        Args:
            name: The attribute or data key to retrieve
            
        Returns:
            The requested value
            
        Raises:
            AttributeError: If the value isn't found in either location
        """
        # Check host.data dictionary first (likely more common case)
        if name in self.current_host.data:
            return self.current_host.data[name]
            
        # Then check direct host attributes
        if hasattr(self.current_host, name):
            return getattr(self.current_host, name)

        raise AttributeError(f"'{name}' not found on host {self.current_host.name}")