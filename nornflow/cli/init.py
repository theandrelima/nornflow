import shutil
from pathlib import Path

import typer
import yaml

from nornflow.cli.constants import (
    NORNFLOW_CONFIG_FILE,
    NORNIR_DEFAULT_CONFIG_DIR,
    SAMPLE_NORNFLOW_FILE,
    SAMPLE_NORNIR_CONFIGS_DIR,
    SAMPLE_TASK_FILE,
    TASKS_DIR,
)
from nornflow.cli.show import show_catalog, show_nornflow_settings
from nornflow.nornflow import NornFlow

app = typer.Typer()


@app.command()
def init() -> None:
    """
    Initialize NornFlow by setting up the necessary configuration files and directories.

    This command performs the following actions:
    1. If a 'nornir_configs' directory does not exist in the current working directory, it copies
    the entire 'nornflow/cli/samples/nornir_configs' directory to the current working directory.
    2. Copies a sample 'nornflow.yaml' file to the current working directory if it does not exist.
    3. Creates a 'tasks' directory and copies a sample 'hello_world.py' task file into it if the
    directory does not exist.
    """
    # TODO: 'nornflow init' should open a dialog to ask the user where to create
    # stuff and with what name (showing defaults)
    # an option to skip the dialog and use defaults should be available as well
    # (e.g. 'nornflow init --with-defaults')

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

    if not NORNFLOW_CONFIG_FILE.exists():
        shutil.copy(SAMPLE_NORNFLOW_FILE, NORNFLOW_CONFIG_FILE)
        typer.secho(f"Created a sample 'nornflow.yaml': {NORNFLOW_CONFIG_FILE}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"File already exists: {NORNFLOW_CONFIG_FILE}", fg=typer.colors.YELLOW)

    if create_directory(TASKS_DIR):
        shutil.copy(SAMPLE_TASK_FILE, TASKS_DIR / SAMPLE_TASK_FILE.name)
        typer.secho(
            f"Created a sample 'hello_world' task: {TASKS_DIR / SAMPLE_TASK_FILE.name}", fg=typer.colors.GREEN
        )

    show_info_post_init()


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


def create_file(file_path: Path, content: dict = None) -> None:
    """Create a file if it doesn't exist and optionally write content to it.

    Args:
        file_path (Path): The path of the file to create.
        content (dict, optional): The content to write to the file if provided.
    """
    if not file_path.exists():
        file_path.touch(exist_ok=True)
        if content:
            with Path.open(file_path, "w") as yaml_file:
                yaml.dump(content, yaml_file, default_flow_style=False)
        typer.secho(f"Created {'empty ' if not content else ''}file: {file_path}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"File already exists: {file_path}", fg=typer.colors.YELLOW)


def show_info_post_init() -> None:
    """
    Display all information about NornFlow, equivalent to running 'nornflow show --all'.
    """
    nornflow = NornFlow()
    show_nornflow_settings(nornflow)
    show_catalog(nornflow)
