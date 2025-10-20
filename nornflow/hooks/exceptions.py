from nornflow.exceptions import NornFlowError


class HookError(NornFlowError):
    """Base exception class for hook-related errors."""


class HookRegistrationError(HookError):
    """Exception raised when hook registration fails."""


class HookConfigurationError(HookError):
    """Exception raised when hook mixin combination is invalid."""


class HookValidationError(HookError):
    """Exception raised when hook validation fails."""

    def __init__(self, hook_class: str, errors: list[tuple[str, str]]):
        """Initialize the validation error with hook details and error list.

        Args:
            hook_class: The name of the hook class that failed validation.
            errors: List of (method_name, error_message) tuples.
        """
        self.hook_class = hook_class
        self.errors = errors
        error_messages = [f"{method}: {msg}" for method, msg in errors]
        message = f"Hook '{hook_class}' validation failed: {'; '.join(error_messages)}"
        super().__init__(message)
