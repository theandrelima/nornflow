class NornFlowError(Exception):
    """Base exception class for NornFlow."""


class CatalogModificationError(NornFlowError):
    """Exception raised when attempting to modify the tasks catalog directly."""

    def __init__(self, catalog_name: str):
        super().__init__(f"Cannot set {catalog_name} catalog directly.")


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


class SettingsModificationError(NornFlowError):
    """Exception raised when attempting to modify the settings directly."""

    def __init__(self):
        super().__init__(
            "Cannot set settings directly. Settings must be either passed as a NornFlowSettings object or as "
            "keyword arguments to the NornFlow initializer."
        )


class NornirConfigsModificationError(NornFlowError):
    """Exception raised when attempting to modify the Nornir configs directly."""

    def __init__(self):
        super().__init__(
            "Cannot set Nornir configs directly. Nornir configs must be set through its own separate .yaml "
            "file and informed to NornFlow using the 'nornir_config_file' setting."
        )


class TaskLoadingError(NornFlowError):
    """Exception raised when there is an error loading tasks."""


class NoTasksToRunError(NornFlowError):
    """Exception raised when there are no tasks to run."""

    def __init__(self):
        super().__init__("No tasks to run informed.")


class EmptyTaskCatalogError(NornFlowError):
    """Exception raised when no tasks are found."""

    def __init__(self):
        super().__init__("No tasks were found. The Tasks Catalog can't be empty.")


class ModuleImportError(NornFlowError):
    """Exception raised when there is an error importing a module."""

    def __init__(self, module_name: str, module_path: str, error: str):
        super().__init__(f"Error importing module '{module_name}' from '{module_path}': {error}")


class LocalDirectoryNotFoundError(NornFlowError):
    """Exception raised when a specified directory is not found."""

    def __init__(self, directory: str, extra_message: str = ""):
        super().__init__(f"Directory not found: {directory}{ - extra_message if extra_message else '.'}")


class NornFlowInitializationError(NornFlowError):
    """Exception raised when invalid kwargs are passed to the NornFlow initializer."""

    def __init__(self, invalid_kwargs: list[str], extra_message: str = ""):
        super().__init__(
            f"Invalid kwarg(s) passed to NornFlow initializer: {', '.join(invalid_kwargs)} {extra_message}"
        )
        self.invalid_kwargs = invalid_kwargs


class NornFlowRunError(NornFlowError):
    """Exception raised when there is an error executing a task."""

    def __init__(self, message: str):
        super().__init__(message)


class WorkflowError(Exception):
    """Base exception class for Workflow-related errors."""

    def __init__(self, message: str):
        super().__init__(message)


class WorkflowInitializationError(WorkflowError):
    """Exception raised when there is an error initializing a Workflow."""

    def __init__(self, message: str):
        super().__init__(
            message
            or "Either workflow_path or workflow_dict must be provided. If you want to "
            "create an empty workflow, initialize with 'empty_workflow' set to True."
        )


class TaskDoesNotExistError(WorkflowError):
    """Exception raised when a task does not exist."""

    def __init__(self, task_names: str | list):
        if isinstance(task_names, list):
            task_names = ", ".join(task_names)

        super().__init__(f"Some informed tasks are not present in the Tasks Catalog: {task_names}")


class WorkflowInventoryFilterError(WorkflowError):
    """Exception raised when there is an error with the inventory filters in a Workflow."""
