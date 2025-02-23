from typing import Any

from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict, OneToMany
from pydantic_serdes.models import PydanticSerdesBaseModel

from nornflow.exceptions import WorkflowInventoryFilterError


class TaskModel(PydanticSerdesBaseModel):
    _key = (
        "id",
        "name",
    )
    _directive = "tasks"
    _err_on_duplicate = False

    id: int | None = None
    name: str
    args: HashableDict[str, str | tuple | dict | None] | None = None

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args, **kwargs) -> "TaskModel": # noqa: ANN002
        """Create a new TaskModel with auto-incrementing id."""
        # Get current tasks and calculate next id
        current_tasks = cls.get_all()
        next_id = len(current_tasks) + 1 if current_tasks else 1

        # Set the id in dict_args
        dict_args["id"] = next_id

        # Call parent's create method
        return super().create(dict_args, *args, **kwargs)

    @field_validator("args", mode="before")
    @classmethod
    def convert_args_lists_to_tuples(cls, v: HashableDict[str, Any] | None) -> HashableDict[str, Any] | None:
        """
        Convert any lists in the args values to tuples.

        Args:
            v (Optional[HashableDict[str, Any]]): The args dictionary to validate.

        Returns:
            Optional[HashableDict[str, Any]]: The validated args with lists converted to tuples.
        """
        if v is None:
            return v

        return HashableDict(
            {key: tuple(value) if isinstance(value, list) else value for key, value in v.items()}
        )


class WorkflowModel(PydanticSerdesBaseModel):
    _key = ("name",)
    _directive = "workflow"

    name: str
    description: str | None = None
    inventory_filters: HashableDict[str, tuple[str] | None] | None = None
    tasks: OneToMany[TaskModel, ...]

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args, **kwargs) -> "WorkflowModel": # noqa: ANN002
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

    @field_validator("inventory_filters", mode="before")
    def validate_inventory_filters(
        cls, v: HashableDict[str, Any] | None # noqa: N805
    ) -> HashableDict[str, Any] | None:
        """
        Validate inventory_filters and convert lists to tuples.

        Args:
            v (Optional[HashableDict[str, Any]]): The inventory_filters value to validate.

        Returns:
            Optional[HashableDict[str, Any]]: The validated inventory_filters with lists converted to tuples.

        Raises:
            WorkflowInventoryFilterError: If the inventory_filters contains invalid keys.
        """
        if v is None:
            return v

        valid_keys = {"hosts", "groups"}
        invalid_keys = set(v.keys()) - valid_keys
        if invalid_keys:
            raise WorkflowInventoryFilterError(
                f"Invalid keys in inventory_filters: {', '.join(invalid_keys)}. "
                "Only 'hosts' and 'groups' are allowed."
            )

        # Convert any lists in values to tuples
        return HashableDict(
            {key: tuple(value) if isinstance(value, list) else value for key, value in v.items()}
        )
