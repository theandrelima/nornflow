from nornflow.exceptions import NornFlowAppError


class NornFlowVarsError(NornFlowAppError):
    """
    Base exception class for variable-related errors.
    These relate to variable loading, resolution, and access operations.
    """
    pass


class VariableDirectoryError(NornFlowVarsError):
    """
    Raised when there's an issue with a variable directory.
    For example, when the "vars_dir" path exists but is not a directory.
    """
    
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Variable directory path exists but is not a directory: {path}")


class VariableLoadError(NornFlowVarsError):
    """
    Raised when there's an error loading variables from a file.
    This can occur due to issues like file not found (though often handled by returning
    empty dicts), YAML syntax errors, or if the loaded content is not of the expected type
    (e.g., not a dictionary).
    """
    
    def __init__(self, path: str, reason: str | None = None, original_exception: Exception | None = None):
        self.path = path
        self.reason = reason
        self.original_exception = original_exception
        
        message = f"Error loading variables from file: {path}"
        if reason:
            message += f". Reason: {reason}"
        if original_exception:
            message += f" (Original error: {original_exception})"
        super().__init__(message)


class VariableNotFoundError(NornFlowVarsError):
    """
    Raised when a requested variable is not found in the relevant scope.
    This applies to both NornFlow Default Namespace variables and Nornir Host
    Namespace variables.
    """
    
    def __init__(self, var_name: str, context_message: str | None = None):
        self.var_name = var_name
        message = f"Variable not found: '{var_name}'"
        if context_message:
            message += f". {context_message}"
        super().__init__(message)


class VariableResolutionError(NornFlowVarsError):
    """
    Raised when there's an error resolving a Jinja2 template string.
    This typically occurs if a template references an undefined variable (and
    Jinja2 is in StrictUndefined mode), or if there's a syntax error in the
    template itself.
    """
    
    def __init__(self, template_str: str, reason: str):
        self.template_str = template_str
        self.reason = reason
        super().__init__(f"Error resolving template string. Reason: {reason}. Template: '{template_str[:100]}{'...' if len(template_str) > 100 else ''}'")
        
        
class HostContextError(NornFlowVarsError):
    """
    Raised when there's an issue with the host context during variable operations.
    For example, when trying to access host-specific variables via the NornirHostProxy
    if the Nornir instance or the current host context has not been properly set.
    """
    
    def __init__(self, message: str):
        super().__init__(message)
