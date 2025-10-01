from collections.abc import Callable
from typing import Any, ClassVar

from nornir.core.task import AggregatedResult
from pydantic import ConfigDict, field_validator
from pydantic_serdes.custom_collections import HashableDict, OneToMany
from pydantic_serdes.models import PydanticSerdesBaseModel
from pydantic_serdes.utils import convert_to_hashable

from nornflow.constants import FailureStrategy
from nornflow.exceptions import TaskError, WorkflowError
from nornflow.nornir_manager import NornirManager
from nornflow.utils import normalize_failure_strategy
from nornflow.validators import (
    run_post_creation_task_validation,
    run_universal_field_validation,
)


class NornFlowBaseModel(PydanticSerdesBaseModel):
    """
    Base model for all NornFlow models with strict field validation and universal field validation.
    """

    model_config = ConfigDict(extra="forbid")
    _exclude_from_global_validators: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def create(cls, model_dict: dict[str, Any], *args: Any, **kwargs: Any) -> "NornFlowBaseModel":
        """
        Create model instance with universal field validation.
        """
        new_instance = super().create(model_dict, *args, **kwargs)
        run_universal_field_validation(new_instance)
        return new_instance


class TaskModel(NornFlowBaseModel):
    _key = (
        "id",
        "name",
    )
    _directive = "tasks"
    _err_on_duplicate = False

    # Exclude 'args' from universal Jinja2 validation since it's allowed there
    _exclude_from_global_validators: ClassVar[tuple[str, ...]] = ("args", "set_to")

    id: int | None = None
    name: str
    args: HashableDict[str, str | tuple | dict | None] | None = None
    set_to: str | None = None

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args: Any, **kwargs: Any) -> "TaskModel":
        """Create a new TaskModel with auto-incrementing id."""
        # Get current tasks and calculate next id
        current_tasks = cls.get_all()
        next_id = len(current_tasks) + 1 if current_tasks else 1

        # Set the id in dict_args
        dict_args["id"] = next_id

        # Call parent's create method (runs universal validation)
        new_task = super().create(dict_args, *args, **kwargs)
        run_post_creation_task_validation(new_task)
        return new_task

    @field_validator("args", mode="before")
    @classmethod
    def validate_args(cls, v: HashableDict[str, Any] | None) -> HashableDict[str, Any] | None:
        """
        Validate the args dictionary and convert to fully hashable structure.

        Args:
            v (HashableDict[str, Any] | None): The args dictionary to validate.

        Returns:
            HashableDict[str, Any] | None: The validated args with all nested structures
                converted to hashable equivalents.
        """
        return convert_to_hashable(v)

    def run(self, nornir_manager: NornirManager, tasks_catalog: dict[str, Callable]) -> AggregatedResult:
        """
        Execute the task using the provided NornirManager and tasks catalog.

        Args:
            nornir_manager: The NornirManager instance to use for execution.
            tasks_catalog: Dictionary mapping task names to their function implementations.

        Returns:
            The results of the task execution.

        Raises:
            TaskError: If the task name is not found in the tasks catalog.
        """
        # Get the task function from the catalog
        task_func = tasks_catalog.get(self.name)
        if not task_func:
            raise TaskError(f"Task function for '{self.name}' not found in tasks catalog")

        task_args = {} if self.args is None else dict(self.args)
        result = nornir_manager.nornir.run(task=task_func, **task_args)
        return result


class WorkflowModel(NornFlowBaseModel):
    _key = ("name",)
    _directive = "workflow"

    name: str
    description: str | None = None
    inventory_filters: HashableDict[str, Any] | None = None
    processors: tuple[HashableDict[str, Any]] | None = None
    tasks: OneToMany[TaskModel, ...]
    dry_run: bool = False
    vars: HashableDict[str, Any] | None = None
    failure_strategy: FailureStrategy = FailureStrategy.SKIP_FAILED

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args: Any, **kwargs: Any) -> "WorkflowModel":
        """Create a new WorkflowModel."""
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
