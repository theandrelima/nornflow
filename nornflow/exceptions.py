"""
NornFlow exception hierarchy.

This module defines all exceptions used throughout the NornFlow application,
organized hierarchically with clear inheritance paths.
"""

###############################################################################
# ROOT EXCEPTION
###############################################################################


class NornFlowAppError(Exception):
    """
    Root exception class for all NornFlow errors.

    This exception serves as the base class for the entire exception hierarchy.
    It should never be raised directly but rather inherited from.
    """

    def __init__(self, message: str = ""):
        super().__init__(message)


###############################################################################
# CORE EXCEPTIONS
###############################################################################


class NornFlowCoreError(NornFlowAppError):
    """
    Base exception class for core functionality errors.

    These relate to fundamental operations of the NornFlow application itself.
    """


class CatalogModificationError(NornFlowCoreError):
    """Raised when attempting to modify a catalog directly."""

    def __init__(self, catalog_name: str):
        super().__init__(f"Cannot set {catalog_name} catalog directly.")


class EmptyTaskCatalogError(NornFlowCoreError):
    """Raised when no tasks are found in the catalog."""

    def __init__(self):
        super().__init__("No tasks were found. The Tasks Catalog can't be empty.")


class NornFlowInitializationError(NornFlowCoreError):
    """Raised when there's an error initializing NornFlow."""

    def __init__(self, message: str = "", invalid_kwargs: list[str] | None = None):
        if invalid_kwargs:
            message = f"Invalid kwarg(s) passed to NornFlow initializer: {', '.join(invalid_kwargs)}"
        super().__init__(message)
        self.invalid_kwargs = invalid_kwargs


class NornFlowRunError(NornFlowCoreError):
    """Raised when there is an error executing NornFlow."""

    def __init__(self, message: str):
        super().__init__(message)
        

class TaskValidationError(NornFlowCoreError):
    """Raised when task model validation fails."""
    
    def __init__(self, task_name: str, field_name: str, reason: str | None = None):
        self.task_name = task_name
        self.field_name = field_name
        self.reason = reason
        
        message = (
            f"Task '{task_name}' validation failed for field '{field_name}'{': ' + reason if reason else '.'}")
        
        super().__init__(message)

###############################################################################
# WORKFLOW EXCEPTIONS
###############################################################################


class NornFlowWorkflowError(NornFlowAppError):
    """
    Base exception class for workflow-related errors.

    These relate to workflow definition, parsing, and execution.
    """


class WorkflowInitializationError(NornFlowWorkflowError):
    """Raised when there is an error initializing a Workflow."""

    def __init__(self, message: str = ""):
        default_message = (
            "Either workflow_path or workflow_dict must be provided. If you want to "
            "create an empty workflow, initialize with 'empty_workflow' set to True."
        )
        super().__init__(message or default_message)


class TaskNotFoundError(NornFlowWorkflowError):
    """Raised when a specified task does not exist in the catalog."""

    def __init__(self, task_names: str | list):
        if isinstance(task_names, list):
            task_names = ", ".join(task_names)
        super().__init__(f"The following task(s) are not present in the Tasks Catalog: {task_names}")


class WorkflowInventoryFilterError(NornFlowWorkflowError):
    """Raised when there is an error with inventory filters in a Workflow."""

    def __init__(self, filter_name: str = "", message: str = ""):
        if filter_name and not message:
            message = f"Error processing filter '{filter_name}'"
        super().__init__(message)


###############################################################################
# SETTINGS EXCEPTIONS
###############################################################################


class NornFlowSettingsError(NornFlowAppError):
    """
    Base exception class for settings-related errors.

    These relate to configuration and settings management.
    """


class MandatorySettingError(NornFlowSettingsError):
    """Raised when there is an issue with a mandatory setting."""

    def __init__(self, setting: str, missing: bool = True):
        message = (
            f"Missing mandatory setting: {setting}." if missing else f"Setting '{setting}' can't be empty."
        )
        super().__init__(message)
        self.setting = setting


class SettingsFileError(NornFlowSettingsError):
    """Raised when there is an issue with the settings file."""

    def __init__(self, file_path: str, error_type: str = "access", error_details: str = ""):
        if error_type == "not_found":
            message = f"The configuration file '{file_path}' does not exist."
        elif error_type == "permission":
            message = f"Permission denied when trying to read '{file_path}'."
        elif error_type == "parsing":
            message = f"Error parsing YAML file '{file_path}': {error_details}"
        else:
            message = f"Error accessing configuration file '{file_path}': {error_details}"

        super().__init__(message)
        self.file_path = file_path
        self.error_type = error_type


class SettingsDataTypeError(NornFlowSettingsError):
    """Raised when the settings data has an incorrect type."""

    def __init__(self):
        super().__init__("The configuration file must contain a dictionary.")


class SettingsModificationError(NornFlowSettingsError):
    """Raised when attempting to modify settings directly."""

    def __init__(self):
        super().__init__(
            "Cannot set settings directly. Settings must be either passed as a NornFlowSettings object or as "
            "keyword arguments to the NornFlow initializer."
        )


###############################################################################
# NORNIR EXCEPTIONS
###############################################################################


class NornFlowNornirError(NornFlowAppError):
    """
    Base exception class for Nornir-related errors.

    These relate to interaction with the Nornir framework.
    """


class NornirConfigError(NornFlowNornirError):
    """Raised when there is an issue with Nornir configuration."""

    def __init__(self, message: str = ""):
        default_message = (
            "Cannot set Nornir configs directly. Nornir configs must be set through its own separate .yaml "
            "file and informed to NornFlow using the 'nornir_config_file' setting."
        )
        super().__init__(message or default_message)


class ProcessorError(NornFlowNornirError):
    """Raised when there is an issue with Nornir processors."""

    def __init__(self, message: str = "No filters informed."):
        super().__init__(message)


###############################################################################
# RESOURCE EXCEPTIONS
###############################################################################


class NornFlowResourceError(NornFlowAppError):
    """
    Base exception class for resource access errors.

    These relate to file, module, and other resource access issues.
    """


class DirectoryNotFoundError(NornFlowResourceError):
    """Raised when a specified directory is not found."""

    def __init__(self, directory: str, extra_message: str = ""):
        super().__init__(f"Directory not found: {directory}{' - ' + extra_message if extra_message else '.'}")
        self.directory = directory


class ModuleImportError(NornFlowResourceError):
    """Raised when there is an error importing a module."""

    def __init__(self, module_name: str, module_path: str, error: str):
        super().__init__(f"Error importing module '{module_name}' from '{module_path}': {error}")
        self.module_name = module_name
        self.module_path = module_path


class TaskLoadingError(NornFlowResourceError):
    """Raised when there is an error loading tasks."""

    def __init__(self, message: str):
        super().__init__(message)


class FilterLoadingError(NornFlowResourceError):
    """Raised when there is an error loading filters."""

    def __init__(self, message: str):
        super().__init__(message)
