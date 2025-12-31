"""
NornFlow exception hierarchy.

This module defines the core exceptions used throughout the NornFlow application,
organized hierarchically with clear inheritance paths.
"""

###############################################################################
# ROOT EXCEPTION
###############################################################################
from typing import Any


class NornFlowError(Exception):
    """
    Root exception class for all NornFlow errors.

    This exception serves as the base class for the entire exception hierarchy.
    It should never be raised directly but rather inherited from.
    """


###############################################################################
# CORE EXCEPTIONS
###############################################################################


class CoreError(NornFlowError):
    """
    Base exception class for core functionality errors.

    These relate to fundamental operations of the NornFlow application itself.
    """

    def __init__(self, message: str = "", component: str = ""):
        prefix = f"{component}: " if component else ""
        super().__init__(f"{prefix}{message}")
        self.component = component


class CatalogError(CoreError):
    """Base for all catalog-related errors."""

    def __init__(self, message: str = "", catalog_name: str = ""):
        prefix = f"{catalog_name.capitalize()} catalog error: " if catalog_name else ""
        super().__init__(f"{prefix}{message}")
        self.catalog_name = catalog_name


class InitializationError(CoreError):
    """Base for all initialization-related errors."""


class ImmutableAttributeError(CoreError):
    """
    Exception raised when attempting to set a read-only or immutable attribute.

    This is used for properties that should never be modified directly,
    ensuring API integrity and guiding users to proper configuration methods.
    """


###############################################################################
# WORKFLOW EXCEPTIONS
###############################################################################


class WorkflowError(NornFlowError):
    """
    Base exception class for workflow-related errors.

    These relate to workflow definition, parsing, and execution.
    """

    def __init__(self, message: str = "", task_name: str = "", filter_name: str = "", **kwargs):
        self.task_name = task_name
        self.filter_name = filter_name

        prefix = ""
        if task_name:
            prefix = f"Task '{task_name}': "
        elif filter_name:
            prefix = f"Filter '{filter_name}': "

        super().__init__(f"{prefix}{message}")


class TaskError(WorkflowError):
    """Base for all task-related errors."""

    def __init__(self, message: str = "", task_name: str = "", **kwargs):
        super().__init__(message, task_name=task_name, **kwargs)


class FilterError(WorkflowError):
    """Base for all filter-related errors."""

    def __init__(self, message: str = "", filter_name: str = "", **kwargs):
        super().__init__(message, filter_name=filter_name, **kwargs)


class BlueprintError(WorkflowError):
    """Base exception for all blueprint-related errors."""

    def __init__(self, message: str = "", blueprint_name: str = "", details: dict[str, Any] | None = None):
        self.blueprint_name = blueprint_name
        self.details = details or {}
        prefix = f"Blueprint '{blueprint_name}': " if blueprint_name else "Blueprint: "
        super().__init__(f"{prefix}{message}")


class BlueprintCircularDependencyError(BlueprintError):
    """Raised when circular dependencies are detected in blueprint expansion."""

    def __init__(self, blueprint_name: str, dependency_chain: list[str]):
        self.dependency_chain = dependency_chain
        chain_str = " → ".join(dependency_chain)
        super().__init__(
            message=f"Circular dependency detected: {chain_str} → {blueprint_name}",
            blueprint_name=blueprint_name,
            details={"dependency_chain": dependency_chain},
        )


###############################################################################
# SETTINGS EXCEPTIONS
###############################################################################


class SettingsError(NornFlowError):
    """
    Base exception class for settings-related errors.

    These relate to configuration and settings management.
    """

    def __init__(self, message: str = "", setting: str = ""):
        prefix = f"Setting '{setting}': " if setting else ""
        super().__init__(f"{prefix}{message}")
        self.setting = setting


###############################################################################
# NORNIR EXCEPTIONS
###############################################################################


class NornirError(NornFlowError):
    """
    Base exception class for Nornir-related errors.

    These relate to interaction with the Nornir framework.
    """


class ProcessorError(NornirError):
    """Base for all processor-related errors."""


###############################################################################
# RESOURCE EXCEPTIONS
###############################################################################


class ResourceError(NornFlowError):
    """
    Base exception class for resource access errors.

    These relate to file, module, and other resource access issues.
    """

    def __init__(self, message: str = "", resource_type: str = "", resource_name: str = ""):
        prefix = f"{resource_type} '{resource_name}': " if resource_type and resource_name else ""
        super().__init__(f"{prefix}{message}")
        self.resource_type = resource_type
        self.resource_name = resource_name
