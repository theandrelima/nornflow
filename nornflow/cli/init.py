import os
import shutil
from pathlib import Path

import typer

from nornflow import NornFlowBuilder
from nornflow.cli.constants import (
    FILTERS_DIR,
    GREET_USER_TASK_FILE,
    HELLO_WORLD_TASK_FILE,
    NORNFLOW_CONFIG_FILE,
    NORNIR_DEFAULT_CONFIG_DIR,
    SAMPLE_NORNFLOW_FILE,
    SAMPLE_NORNIR_CONFIGS_DIR,
    SAMPLE_WORKFLOW_FILE,
    TASKS_DIR,
    WORKFLOWS_DIR,
)
from nornflow.cli.show import show_catalog, show_nornflow_settings

app = typer.Typer()


@app.command()
def init(ctx: typer.Context) -> None:
    """
    Initialize NornFlow by setting up the necessary configuration files and directories.

    This command performs the following actions:
    1. If a 'nornir_configs' directory does not exist in the current working directory, it copies
    the entire 'nornflow/cli/samples/nornir_configs' directory to the current working directory.
    2. Copies a sample 'nornflow.yaml' file to the current working directory if it does not exist.
    3. If a 'tasks' directory doesn't exist, creates one and copies sample task files into it.
    4. If a 'workflows' directory doesn't exist, creates one and copies the sample workflow file into it.
    5. If a 'filters' directory doesn't exist, creates an empty one.
    """
    builder = NornFlowBuilder()

    settings = ctx.obj.get("settings")
    if settings:
        builder.with_settings_path(settings)

    # Display the banner message and prompt the user for confirmation
    display_banner()
    if not typer.confirm("Do you want to continue?", default=True):
        typer.secho("Initialization aborted.", fg=typer.colors.RED)
        return

    typer.secho(f"NornFlow will be initialized at {NORNIR_DEFAULT_CONFIG_DIR.parent}", fg=typer.colors.GREEN)

    if create_directory(NORNIR_DEFAULT_CONFIG_DIR):
        for item in SAMPLE_NORNIR_CONFIGS_DIR.iterdir():
            if item.is_dir():
                shutil.copytree(item, NORNIR_DEFAULT_CONFIG_DIR / item.name)
            else:
                shutil.copy(item, NORNIR_DEFAULT_CONFIG_DIR / item.name)
        typer.secho(
            f"Created a sample 'nornir_configs' directory: {NORNIR_DEFAULT_CONFIG_DIR}", fg=typer.colors.GREEN
        )

    if not os.getenv("NORNFLOW_CONFIG_FILE"):
        if not settings and not NORNFLOW_CONFIG_FILE.exists():
            shutil.copy(SAMPLE_NORNFLOW_FILE, NORNFLOW_CONFIG_FILE)
            typer.secho(f"Created a sample 'nornflow.yaml': {NORNFLOW_CONFIG_FILE}", fg=typer.colors.GREEN)
        elif settings:
            typer.secho(f"Trying to use informed settings file: {settings}", fg=typer.colors.YELLOW)
        else:
            typer.secho(f"Settings file already exists: {NORNFLOW_CONFIG_FILE}", fg=typer.colors.YELLOW)

    create_directory_and_copy_sample_files(
        TASKS_DIR, [HELLO_WORLD_TASK_FILE, GREET_USER_TASK_FILE], "Created sample tasks in directory: {}"
    )

    create_directory_and_copy_sample_files(
        WORKFLOWS_DIR, [SAMPLE_WORKFLOW_FILE], "Created a sample 'hello_world' workflow in directory: {}"
    )

    create_directory(FILTERS_DIR)

    show_info_post_init(builder)


def display_banner() -> None:
    """
    Display a banner message with borders.
    """
    banner_message = (
        "The 'init' command creates directories, and samples for configs, tasks and\n"
        "workflows files, all with default values that you can modify as desired.\n"
        "No customization of 'init' parameters available yet.\n\nDo you want to continue?"
    )
    lines = banner_message.split("\n")
    max_length = max(len(line) for line in lines)
    border = "+" + "-" * (max_length + 2) + "+"
    typer.secho(border, fg=typer.colors.CYAN, bold=True)
    for line in lines:
        padded_line = line + " " * (max_length - len(line))
        typer.secho(f"| {padded_line} |", fg=typer.colors.CYAN, bold=True)
    typer.secho(border, fg=typer.colors.CYAN, bold=True)


def create_directory_and_copy_sample_files(
    dir_path: Path, sample_files: list[Path], sample_message: str
) -> None:
    """
    Create a directory if it doesn't exist and copy sample files into it.

    Args:
        dir_path (Path): The path of the directory to create.
        sample_files (list[Path]): The list of sample files to copy into the directory.
        sample_message (str): The message to display after copying the sample files.
    """
    if create_directory(dir_path):
        for sample_file in sample_files:
            shutil.copy(sample_file, dir_path / sample_file.name)
        typer.secho(sample_message.format(dir_path), fg=typer.colors.GREEN)


def create_directory(dir_path: Path) -> bool:
    """Create a directory if it doesn't exist.

    Args:
        dir_path (Path): The path of the directory to create.

    Returns:
        bool: True if the directory was created, False if it already existed.
    """
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        typer.secho(f"Created directory: {dir_path}", fg=typer.colors.GREEN)
        return True
    typer.secho(f"Directory already exists: {dir_path}", fg=typer.colors.YELLOW)
    return False


def show_info_post_init(builder: NornFlowBuilder) -> None:
    """
    Display all information about NornFlow, equivalent to running 'nornflow show --all'.
    """
    nornflow = builder.build()
    show_nornflow_settings(nornflow)
    show_catalog(nornflow)
