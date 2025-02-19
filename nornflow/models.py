from typing import Any

from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict, OneToMany
from pydantic_serdes.models import PydanticSerdesBaseModel

from nornflow.exceptions import WorkflowInventoryFilterError


class TaskModel(PydanticSerdesBaseModel):
    _key = (
        "name",
        "args",
    )
    _directive = "tasks"
    _err_on_duplicate = False

    name: str
    args: HashableDict[str, list | None] | None = None


class WorkflowModel(PydanticSerdesBaseModel):
    _key = ("name",)
    _directive = "workflow_configs"

    name: str
    description: str | None = None
    inventory_filters: HashableDict[str, list[str] | None] | None = None
    tasks: OneToMany[TaskModel, ...]

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args, **kwargs) -> "WorkflowModel": # noqa: ANN002
        dict_args["tasks"] = list(TaskModel.get_all())
        super().create(dict_args, *args, **kwargs)

    @field_validator("inventory_filters", mode="before")
    def validate_inventory_filters(cls, v: HashableDict[str, Any] | None) -> HashableDict[str, Any] | None: #noqa: N805
        """
        Validate that the inventory_filters field only contains the keys 'hosts' and 'groups'.
        These are the only supported filtering options at the moment.

        Args:
            v (Optional[HashableDict[str, Any]]): The inventory_filters value to validate.

        Returns:
            Optional[HashableDict[str, Any]]: The validated inventory_filters value.

        Raises:
            ValueError: If the inventory_filters contains invalid keys.
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

        return v
