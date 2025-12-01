"""Workflow model classes for NornFlow."""

from typing import Any

from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict, OneToMany
from pydantic_serdes.utils import convert_to_hashable

from nornflow.constants import FailureStrategy
from nornflow.exceptions import WorkflowError
from nornflow.models import NornFlowBaseModel, TaskModel
from nornflow.utils import normalize_failure_strategy


class WorkflowModel(NornFlowBaseModel):
    _key = ("name",)
    _directive = "workflow"

    name: str
    description: str | None = None
    inventory_filters: HashableDict[str, Any] | None = None
    processors: tuple[HashableDict[str, Any]] | None = None
    tasks: OneToMany[TaskModel, ...]
    dry_run: bool | None = None
    vars: HashableDict[str, Any] | None = None
    failure_strategy: FailureStrategy | None = None

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args: Any, **kwargs: Any) -> "WorkflowModel":
        """
        Create a new WorkflowModel from a workflow dictionary.

        Extracts the 'workflow' key from the input dict and processes tasks into TaskModel instances.

        Args:
            dict_args: Dictionary containing the full workflow data, must include 'workflow' key.
            *args: Additional positional arguments passed to parent create method.
            **kwargs: Additional keyword arguments passed to parent create method.

        Returns:
            The created WorkflowModel instance.

        Raises:
            WorkflowError: If 'workflow' key is not present in dict_args.
        """
        try:
            dict_args = dict_args.pop("workflow")
        except KeyError as e:
            raise WorkflowError("Workflow file must have 'workflow' as a root-level key.") from e

        # Tasks should already be in dict_args from the workflow definition
        if "tasks" not in dict_args:
            dict_args["tasks"] = []  # Default to empty list if no tasks defined

        # Create TaskModels from the tasks in dict_args
        tasks = []
        for task_dict in dict_args["tasks"]:
            task = TaskModel.create(task_dict)
            tasks.append(task)

        # Update tasks in dict_args with the created TaskModels
        # in the end, it's ok for tasks to be a python list, because PydanticSerdesBaseModel
        # automatically takes care of converting it to its own OneToMany type
        dict_args["tasks"] = tasks

        return super().create(dict_args, *args, **kwargs)

    @field_validator("failure_strategy", mode="before")
    @classmethod
    def validate_failure_strategy(cls, v: Any) -> FailureStrategy:
        """
        Validate and convert failure_strategy string to enum, case-insensitively.

        Delegates to shared utility for consistent validation and error handling.

        Args:
            v (Any): The failure_strategy value to validate.

        Returns:
            FailureStrategy: The validated FailureStrategy enum.

        Raises:
            WorkflowError: If the value is invalid.
        """
        return normalize_failure_strategy(v, WorkflowError)

    @field_validator("inventory_filters", mode="before")
    def validate_inventory_filters(
        cls, v: HashableDict[str, Any] | None  # noqa: N805
    ) -> HashableDict[str, Any] | None:
        """
        Convert nested structures in inventory_filters to fully hashable equivalents.

        Args:
            v (HashableDict[str, Any] | None): The inventory_filters value to validate.

        Returns:
            HashableDict[str, Any] | None: The inventory_filters with all nested
                 structures converted to hashable equivalents.
        """
        return convert_to_hashable(v)

    @field_validator("processors", mode="before")
    def validate_processors(
        cls, v: list[dict[str, Any]] | None  # noqa: N805
    ) -> tuple[HashableDict[str, Any], ...] | None:
        """
        Convert processors list to tuple with fully hashable nested structures.

        Args:
            v (list[HashableDict[str, Any]] | None): The processors list to validate.

        Returns:
            tuple[HashableDict[str, Any], ...] | None: The processors as a tuple with
                hashable nested structures.
        """
        if v is None:
            return None
        return tuple(convert_to_hashable(processor) for processor in v)

    @field_validator("vars", mode="before")
    def validate_vars(cls, v: dict[str, Any] | None) -> HashableDict[str, Any] | None:  # noqa: N805
        """
        Convert workflow variables to fully hashable structure.

        Args:
            v (dict[str, Any] | None): The vars dictionary to validate.

        Returns:
            HashableDict[str, Any] | None: The vars with all nested structures
                converted to hashable equivalents.
        """
        return convert_to_hashable(v)
