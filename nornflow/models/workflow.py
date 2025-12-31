"""Workflow model classes for NornFlow."""

from typing import Any

from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict, OneToMany
from pydantic_serdes.utils import convert_to_hashable

from nornflow.blueprints import BlueprintExpander, BlueprintResolver
from nornflow.constants import FailureStrategy
from nornflow.exceptions import WorkflowError
from nornflow.models import NornFlowBaseModel, TaskModel
from nornflow.utils import normalize_failure_strategy
from nornflow.vars.jinja2_utils import Jinja2EnvironmentManager


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

        Extracts the 'workflow' key from the input dict, expands any blueprint references
        in the tasks list, and processes tasks into TaskModel instances.

        Args:
            dict_args: Dictionary containing the full workflow data, must include 'workflow' key.
            *args: Additional positional arguments passed to parent create method.
            **kwargs: Additional keyword arguments passed to parent create method.
                blueprints_catalog: Optional catalog mapping blueprint names to file paths.
                vars_dir: Optional directory containing variable files.
                workflow_path: Optional path to the workflow file.
                workflow_roots: Optional list of workflow root directories.
                cli_vars: Optional CLI variables with highest precedence.

        Returns:
            The created WorkflowModel instance.

        Raises:
            WorkflowError: If 'workflow' key is not present in dict_args.
            BlueprintError: If blueprint expansion fails.
        """
        if "workflow" not in dict_args:
            raise WorkflowError("Workflow file must have 'workflow' as a root-level key.")

        workflow_dict = dict_args["workflow"]

        if "tasks" not in workflow_dict:
            workflow_dict["tasks"] = []

        jinja2_manager = Jinja2EnvironmentManager()
        resolver = BlueprintResolver(jinja2_manager)
        expander = BlueprintExpander(resolver)

        # Pop blueprint-specific kwargs to consume them and remove them from the dict.
        blueprints_catalog = kwargs.pop("blueprints_catalog", None)
        vars_dir = kwargs.pop("vars_dir", None)
        workflow_path = kwargs.pop("workflow_path", None)
        workflow_roots = kwargs.pop("workflow_roots", None)
        cli_vars = kwargs.pop("cli_vars", None)

        expanded_tasks = expander.expand_blueprints(
            tasks=workflow_dict["tasks"],
            blueprints_catalog=blueprints_catalog,
            vars_dir=vars_dir,
            workflow_path=workflow_path,
            workflow_roots=workflow_roots,
            inline_vars=workflow_dict.get("vars"),
            cli_vars=cli_vars,
        )

        tasks = []
        for task_dict in expanded_tasks:
            task = TaskModel.create(task_dict)
            tasks.append(task)

        workflow_dict["tasks"] = tasks

        # kwargs contains arguments meant for the model itself.
        result = super().create(workflow_dict, *args, **kwargs)
        return result

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
