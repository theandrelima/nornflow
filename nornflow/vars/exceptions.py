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
    
    For example, when the "vars" directory exists but is not a directory.
    """
    
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Variable directory path exists but is not a directory: {path}")


class VariableLoadError(NornFlowVarsError):
    """
    Raised when there's an error loading variables from a file.
    
    For example, when a YAML file has syntax errors.
    """
    
    def __init__(self, path: str, original_exception: Exception | None = None):
        self.path = path
        self.original_exception = original_exception
        message = f"Error loading variables from: {path}"
        if original_exception:
            message += f" ({original_exception})"
        super().__init__(message)


class VariableNotFoundError(NornFlowVarsError):
    """
    Raised when a requested variable is not found in any scope.
    """
    
    def __init__(self, var_name: str):
        self.var_name = var_name
        super().__init__(f"Variable not found: {var_name}")


class VariableResolutionError(NornFlowVarsError):
    """
    Raised when there's an error resolving a template.
    
    For example, when a template references an undefined variable.
    """
    
    def __init__(self, template: str, reason: str):
        self.template = template
        self.reason = reason
        super().__init__(f"Error resolving template: {reason}")