import yaml
import click
import os
from pathlib import Path

from nornflow.cli.constants import NORNIR_DEFAULT_CONFIG_DIR, NORNIR_DEFAULT_CONFIG_FILES, NONRFLOW_INIT_SETTINGS

@click.command()
def init():
    """Initialize NornFlow"""
    nornir_config_dir = Path(os.getcwd()) / NORNIR_DEFAULT_CONFIG_DIR
    nornir_config_files = NORNIR_DEFAULT_CONFIG_FILES
    click.echo(click.style(f"NornFlow will be initialized at {nornir_config_dir}", fg='green'))
    
    create_directory(nornir_config_dir)
    
    for file_name in nornir_config_files:
        create_file(nornir_config_dir / file_name)
    
    create_file(Path(os.getcwd()) / "nornflow.yaml", NONRFLOW_INIT_SETTINGS)

def create_directory(dir_path: Path) -> None:
    """Create a directory if it doesn't exist."""
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        click.echo(click.style(f"Created directory: {dir_path}", fg='green'))
    else:
        click.echo(click.style(f"Directory already exists: {dir_path}", fg='yellow'))

def create_file(file_path: Path, content: dict = None) -> None:
    """Create a file if it doesn't exist and optionally write content to it."""
    if not file_path.exists():
        file_path.touch(exist_ok=True)
        if content:
            with open(file_path, 'w') as yaml_file:
                yaml.dump(content, yaml_file, default_flow_style=False)
        click.echo(click.style(f"Created {'empty ' if not content else ''}file: {file_path}", fg='green'))
    else:
        click.echo(click.style(f"File already exists: {file_path}", fg='yellow'))