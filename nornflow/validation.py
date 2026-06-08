"""Static workflow validation without contacting devices or running Nornir tasks."""

import inspect
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from nornflow.exceptions import (
    AssetAmbiguityError,
    AssetNotFoundError,
    NornFlowError,
    TaskError,
    WorkflowError,
    WorkflowValidationError,
)
from nornflow.models import WorkflowModel

if TYPE_CHECKING:
    from nornflow.nornflow import NornFlow

# Task parameters Nornir or task decorators inject; not supplied from workflow YAML.
_EXCLUDED_TASK_PARAMS = frozenset({"task", "node"})


@dataclass
class ValidationIssue:
    """One task-level problem found during static workflow validation."""

    task_index: int
    task_ref: str
    task_name: str
    category: str
    message: str


def validate_task_args(task_name: str, task_func: Any, args: dict[str, Any] | None) -> None:
    """Ensure required task parameters are present in workflow args.

    Args:
        task_name: Catalog task reference from the workflow.
        task_func: Resolved Nornir task callable.
        args: Task args from the workflow YAML.

    Raises:
        TaskError: When a required workflow-supplied parameter is missing.
    """
    signature = inspect.signature(task_func)
    provided = set(args or {})
    missing = []

    for param_name, param in signature.parameters.items():
        if param_name in _EXCLUDED_TASK_PARAMS:
            continue
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
        if param.default is inspect.Parameter.empty and param_name not in provided:
            missing.append(param_name)

    if missing:
        joined = ", ".join(f"'{name}'" for name in missing)
        raise TaskError(
            f"Missing required argument(s): {joined}",
            task_name=task_name,
        )


def validate_workflow_tasks(nornflow: "NornFlow", workflow: WorkflowModel) -> None:
    """Resolve tasks, validate args, and run hook configuration checks.

    Precondition: workflow must be a finished WorkflowModel. YAML must already be
    parsed, blueprints expanded, and each task built via TaskModel.create(). Do not
    call this on raw dicts or unexpanded blueprint entries.

    Assembly errors (missing blueprints, circular chains, invalid workflow shape)
    belong to WorkflowModel.create() or build(), not this function. This is a second
    pass: catalog resolution, required args, and hook checks.

    Every task is checked before raising. When any problem is found, raises
    WorkflowValidationError with all collected issues.

    Args:
        nornflow: Initialized NornFlow instance with catalogs loaded.
        workflow: Fully expanded workflow model.

    Raises:
        WorkflowValidationError: When one or more task-level problems were found.
        WorkflowError: When the workflow has no tasks after expansion.
    """
    if not workflow.tasks:
        raise WorkflowError("Workflow has no tasks after blueprint expansion", component="NornFlow")

    catalog = nornflow.tasks_catalog
    issues: list[ValidationIssue] = []

    for index, task in enumerate(workflow.tasks, start=1):
        try:
            task_func = catalog.resolve(task.name)
        except AssetAmbiguityError as exc:
            issues.append(
                ValidationIssue(
                    task_index=index,
                    task_ref=task.canonical_id,
                    task_name=task.name,
                    category="catalog",
                    message=(
                        f"Ambiguous task reference. Use a qualified name. "
                        f"Candidates: {', '.join(sorted(exc.candidates))}"
                    ),
                )
            )
            continue
        except AssetNotFoundError:
            issues.append(
                ValidationIssue(
                    task_index=index,
                    task_ref=task.canonical_id,
                    task_name=task.name,
                    category="catalog",
                    message="Task not found in tasks catalog",
                )
            )
            continue

        task_args = dict(task.args) if task.args else None
        try:
            validate_task_args(task.name, task_func, task_args)
        except TaskError as exc:
            issues.append(
                ValidationIssue(
                    task_index=index,
                    task_ref=task.canonical_id,
                    task_name=task.name,
                    category="args",
                    message=str(exc),
                )
            )
            continue

        try:
            task.run_hook_validations()
        except NornFlowError as exc:
            issues.append(
                ValidationIssue(
                    task_index=index,
                    task_ref=task.canonical_id,
                    task_name=task.name,
                    category="hooks",
                    message=str(exc),
                )
            )

    if issues:
        raise WorkflowValidationError(issues)
