"""CLI command for static workflow validation."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nornflow import NornFlowBuilder
from nornflow.cli.exceptions import CLIValidateError
from nornflow.exceptions import NornFlowError, WorkflowError, WorkflowValidationError
from nornflow.nornflow import NornFlow

app = typer.Typer(help="Validate NornFlow workflows without executing tasks")
_console = Console(stderr=True)


def show_validation_issues(workflow_path: str, exc: WorkflowValidationError) -> None:
    """Render collected task validation issues as a single Rich table.

    Args:
        workflow_path: Path to the workflow file that was validated.
        exc: Exception carrying all collected validation issues.
    """
    table = Table(
        show_header=True,
        header_style="bold red",
        title=f"{len(exc.issues)} validation error(s) in {workflow_path}",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Task ref", style="cyan", no_wrap=True)
    table.add_column("Task", style="cyan")
    table.add_column("Check", style="yellow", no_wrap=True)
    table.add_column("Problem")

    for issue in exc.issues:
        table.add_row(
            str(issue.task_index),
            issue.task_ref,
            issue.task_name,
            issue.category,
            issue.message,
        )

    _console.print(Panel(table, title="[red]NornFlow Validation Failed[/]", border_style="red"))


def build_nornflow_for_validate(settings_file: str, workflow: str) -> NornFlow:
    """Build NornFlow with a fully assembled workflow, ready for validate_workflow().

    Uses the same path as run: settings load, blueprint expansion, TaskModel build.
    Call validate_workflow() only after build() returns.

    Args:
        settings_file: Optional path to nornflow settings YAML.
        workflow: Workflow file path or catalog workflow name.

    Returns:
        NornFlow with catalogs loaded and workflow assembled.

    Raises:
        CLIValidateError: When the workflow reference is invalid or assembly fails.
    """
    builder = NornFlowBuilder()
    if settings_file:
        builder.with_settings_path(settings_file)

    try:
        builder.with_workflow_reference(workflow)
    except WorkflowError as exc:
        raise CLIValidateError(message=str(exc), original_exception=exc) from exc

    workflow_label = Path(workflow).name if Path(workflow).exists() else workflow

    try:
        return builder.build()
    except NornFlowError as exc:
        raise CLIValidateError(
            message=f"Failed to assemble workflow '{workflow_label}': {exc}",
            original_exception=exc,
        ) from exc


@app.command()
def validate(
    ctx: typer.Context,
    workflow: str = typer.Argument(..., help="Workflow file path or catalog workflow name"),
) -> None:
    """Validate a workflow file without running tasks or contacting devices."""
    settings = ctx.obj.get("settings", "")

    try:
        nornflow = build_nornflow_for_validate(settings, workflow)
        nornflow.validate_workflow()
        workflow_name = nornflow.workflow.name if nornflow.workflow else workflow
        typer.secho(f"Validation passed: {workflow_name}", fg=typer.colors.GREEN)
    except WorkflowValidationError as exc:
        show_validation_issues(workflow, exc)
        sys.exit(1)
    except NornFlowError as exc:
        CLIValidateError(
            message=f"Validation failed for '{workflow}': {exc}",
            original_exception=exc,
        ).show()
        sys.exit(1)
    except CLIValidateError as exc:
        exc.show()
        sys.exit(exc.code)
