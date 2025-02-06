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
        super().__init__(f"Setting '{setting}' can't be empty.")

class SettingsFileNotFoundException(NornFlowException):
    """Exception raised when the configuration file is not found."""
    def __init__(self, file_path: str):
        super().__init__(f"The configuration file '{file_path}' does not exist.")

class SettingsFilePermissionException(NornFlowException):
    """Exception raised when there is a permission error accessing the configuration file."""
    def __init__(self, file_path: str):
        super().__init__(f"Permission denied when trying to read '{file_path}'.")

class SettingsFileParsingException(NornFlowException):
    """Exception raised when there is an error parsing the configuration file."""
    def __init__(self, file_path: str, error: str):
        super().__init__(f"Error parsing YAML file '{file_path}': {error}")

class SettingsDataTypeException(NornFlowException):
    """Exception raised when the configuration data is not a dictionary."""
    def __init__(self):
        super().__init__("The configuration file must contain a dictionary.")