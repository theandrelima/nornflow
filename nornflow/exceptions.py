class NornFlowException(Exception):
    """Base exception class for NornFlow."""
    pass

class MissingMandatorySettingException(NornFlowException):
    """Exception raised when a mandatory setting is missing."""
    def __init__(self, setting: str):
        super().__init__(f"Missing mandatory setting: {setting}.")

class EmptyMandatorySettingException(NornFlowException):
    """Exception raised when a mandatory setting is empty."""
    def __init__(self, setting: str):
        super().__init__(f"Setting {setting} can't be empty.")