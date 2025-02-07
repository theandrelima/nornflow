class NornFlowError(Exception):
    """Base exception class for NornFlow."""


class TasksCatalogModificationError(NornFlowError):
    """Exception raised when attempting to modify the tasks catalog directly."""

    def __init__(self):
        super().__init__("Cannot set tasks catalog directly.")


class MissingMandatorySettingError(NornFlowError):
    """Exception raised when a mandatory setting is missing."""

    def __init__(self, setting: str):
        super().__init__(f"Missing mandatory setting: {setting}.")


class EmptyMandatorySettingError(NornFlowError):
    """Exception raised when a mandatory setting is empty."""

    def __init__(self, setting: str):
        super().__init__(f"Setting '{setting}' can't be empty.")


class SettingsFileNotFoundError(NornFlowError):
    """Exception raised when the configuration file is not found."""

    def __init__(self, file_path: str):
        super().__init__(f"The configuration file '{file_path}' does not exist.")


class SettingsFilePermissionError(NornFlowError):
    """Exception raised when there is a permission error accessing the configuration file."""

    def __init__(self, file_path: str):
        super().__init__(f"Permission denied when trying to read '{file_path}'.")


class SettingsFileParsingError(NornFlowError):
    """Exception raised when there is an error parsing the configuration file."""

    def __init__(self, file_path: str, error: str):
        super().__init__(f"Error parsing YAML file '{file_path}': {error}")


class SettingsDataTypeError(NornFlowError):
    """Exception raised when the configuration data is not a dictionary."""

    def __init__(self):
        super().__init__("The configuration file must contain a dictionary.")


class SettingsModificationError(Exception):
    """Exception raised when attempting to modify the settings directly."""

    def __init__(self):
        super().__init__(
            "Cannot set settings directly. Settings must be either passed as a NornFlowSettings object or as keyword arguments to the NornFlow initializer."
        )


class NornirConfigsModificationError(Exception):
    """Exception raised when attempting to modify the Nornir configs directly."""

    def __init__(self):
        super().__init__(
            "Cannot set Nornir configs directly. Nornir configs must be set through it's own separate .yaml file and informed to NornFlow using the 'nornir_config_file' setting."
        )


class TaskLoadingError(NornFlowError):
    """Exception raised when there is an error loading tasks."""

    def __init__(self, message: str):
        super().__init__(message)


class TaskDoesNotExistError(NornFlowError):
    """Exception raised when a task does not exist."""

    def __init__(self, task_names: str | list):

        if isinstance(task_names, list):
            task_names = ", ".join(task_names)

        super().__init__(f"Some informed tasks are not present in the Tasks Catalog: {task_names}")


class NoTasksToRunError(NornFlowError):
    """Exception raised when there are no tasks to run."""

    def __init__(self):
        super().__init("No tasks to run informed.")


class EmptyTaskCatalogError(NornFlowError):
    """Exception raised when no tasks are found."""

    def __init__(self):
        super().__init__("No tasks were found. The Tasks Catalog can't be empty.")


class ModuleImportError(NornFlowError):
    """Exception raised when there is an error importing a module."""

    def __init__(self, module_name: str, module_path: str, error: str):
        super().__init__(f"Error importing module '{module_name}' from '{module_path}': {error}")
