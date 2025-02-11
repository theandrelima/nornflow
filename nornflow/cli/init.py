import shutil
from pathlib import Path

import typer
import yaml

from nornflow.cli.constants import (
    NORNIR_DEFAULT_CONFIG_DIR,
)
from nornflow.cli.show import show_catalog, show_nornflow_settings, show_nornir_configs
from nornflow.nornflow import NornFlow

app = typer.Typer()

@app.command()  # Remove app. and use typer.command directly
def init() -> None:
    """
    Initialize NornFlow by setting up the necessary configuration files and directories.

    This command performs the following actions:
    1. If a 'nornir_configs' directory does not exist in the current working directory, it copies
    the entire 'nornflow/cli/samples/nornir_configs' directory to the current working directory.
    2. Copies a sample 'nornflow.yaml' file to the current working directory if it does not exist.
    3. Creates a 'tasks' directory and copies a sample 'hello_world.py' task file into it if the
    directory does not exist.

    The paths for the configuration files and sample files are determined relative to the location
    of this script.
    """
    nornir_config_dir = Path.cwd() / NORNIR_DEFAULT_CONFIG_DIR
    tasks_dir = Path.cwd() / "tasks"
    sample_task_file = Path(__file__).parent / "samples" / "hello_world.py"
    sample_nornflow_file = Path(__file__).parent / "samples" / "nornflow.yaml"
    sample_nornir_configs_dir = Path(__file__).parent / "samples" / "nornir_configs"
    nornflow_file = Path.cwd() / "nornflow.yaml"

    typer.secho(f"NornFlow will be initialized at {Path.cwd()}", fg=typer.colors.GREEN)

    if create_directory(nornir_config_dir):
        for item in sample_nornir_configs_dir.iterdir():
            if item.is_dir():
                shutil.copytree(item, nornir_config_dir / item.name)
            else:
                shutil.copy(item, nornir_config_dir / item.name)
        typer.secho(
            f"Created a sample 'nornir_configs' directory: {nornir_config_dir}", 
            fg=typer.colors.GREEN
        )

    if not nornflow_file.exists():
        shutil.copy(sample_nornflow_file, nornflow_file)
        typer.secho(f"Created a sample 'nornflow.yaml': {nornflow_file}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"File already exists: {nornflow_file}", fg=typer.colors.YELLOW)

    if create_directory(tasks_dir):
        shutil.copy(sample_task_file, tasks_dir / sample_task_file.name)
        typer.secho(
            f"Created a sample 'hello_world' task: {tasks_dir / sample_task_file.name}", 
            fg=typer.colors.GREEN
        )

    show_all()


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
        typer.secho(
            f"Created {'empty ' if not content else ''}file: {file_path}", 
            fg=typer.colors.GREEN
        )
    else:
        typer.secho(f"File already exists: {file_path}", fg=typer.colors.YELLOW)


def show_all() -> None:
    """
    Display all information about NornFlow, equivalent to running 'nornflow show --all'.
    """
    nornflow = NornFlow()
    show_catalog(nornflow)
    show_nornflow_settings(nornflow)
    show_nornir_configs(nornflow)


if __name__ == "__main__":
    typer.run(init)  # Use typer.run to run the command directly