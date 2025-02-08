from pathlib import Path
import shutil

import click
import yaml

from nornflow.cli.constants import (
    NORNIR_DEFAULT_CONFIG_DIR,
    NORNIR_DEFAULT_CONFIG_FILES,
)


@click.command()
def init() -> None:
    """Initialize NornFlow"""
    nornir_config_dir = Path.cwd() / NORNIR_DEFAULT_CONFIG_DIR
    nornir_config_files = NORNIR_DEFAULT_CONFIG_FILES
    tasks_dir = Path.cwd() / "tasks"
    sample_task_file = Path(__file__).parent / "samples" / "hello_world.py"
    sample_nornflow_file = Path(__file__).parent / "samples" / "nornflow.yaml"
    nornflow_file = Path.cwd() / "nornflow.yaml"

    click.echo(click.style(f"NornFlow will be initialized at {nornir_config_dir}", fg="green"))

    create_directory(nornir_config_dir)

    for file_name in nornir_config_files:
        create_file(nornir_config_dir / file_name)

    if not nornflow_file.exists():
        shutil.copy(sample_nornflow_file, nornflow_file)
        click.echo(click.style(f"Created sample 'nornflow.yaml': {nornflow_file}", fg="green"))
    else:
        click.echo(click.style(f"File already exists: {nornflow_file}", fg="yellow"))

    if create_directory(tasks_dir):
        shutil.copy(sample_task_file, tasks_dir / sample_task_file.name)
        click.echo(click.style(f"Created sample 'hello_world' task: {tasks_dir / sample_task_file.name}", fg="green"))


def create_directory(dir_path: Path) -> bool:
    """Create a directory if it doesn't exist.

    Args:
        dir_path (Path): The path of the directory to create.

    Returns:
        bool: True if the directory was created, False if it already existed.
    """
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        click.echo(click.style(f"Created directory: {dir_path}", fg="green"))
        return True
    else:
        click.echo(click.style(f"Directory already exists: {dir_path}", fg="yellow"))
        return False


def create_file(file_path: Path, content: dict = None) -> None:
    """Create a file if it doesn't exist and optionally write content to it."""
    if not file_path.exists():
        file_path.touch(exist_ok=True)
        if content:
            with Path.open(file_path, "w") as yaml_file:
                yaml.dump(content, yaml_file, default_flow_style=False)
        click.echo(click.style(f"Created {'empty ' if not content else ''}file: {file_path}", fg="green"))
    else:
        click.echo(click.style(f"File already exists: {file_path}", fg="yellow"))