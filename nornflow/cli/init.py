import os
import shutil
from pathlib import Path

import typer

from nornflow import NornFlow, NornFlowBuilder
from nornflow.cli.constants import (
    GREET_USER_TASK_FILE,
    HELLO_WORLD_TASK_FILE,
    INIT_BANNER,
    NORNFLOW_SETTINGS,
    SAMPLE_NORNFLOW_FILE,
    SAMPLE_NORNIR_CONFIGS_DIR,
    SAMPLE_VARS_FILE,
    SAMPLE_WORKFLOW_FILE,
)
from nornflow.cli.exceptions import CLIInitError
from nornflow.cli.show import show_catalog, show_nornflow_settings
from nornflow.exceptions import NornFlowError

app = typer.Typer()


@app.command()
def init(ctx: typer.Context) -> None:
    """
    Initialize a NornFlow project structure.

    Creates necessary directories and sample files based on settings.
    """
    try:
        if not get_user_confirmation():
            return

        # Step 1: Copy sample nornflow.yaml settings file (must happen first)
        settings_file = ctx.obj.get("settings", "")
        setup_nornflow_settings_file(settings_file)

        # Step 2: Build NornFlow from the settings file that now exists
        builder = setup_builder(ctx)
        nornflow = builder.build()

        # Step 3: Create nornir configs directory (derived from settings)
        setup_nornir_configs(nornflow)

        # Step 4: Create all directories from settings
        create_directories_from_settings(nornflow)

        # Step 5: Copy sample content to directories
        setup_sample_content(nornflow)

        # Step 6: Show info using the real NornFlow object
        show_info_post_init(nornflow)

    except NornFlowError as e:
        raise CLIInitError(
            f"Failed to initialize NornFlow project: {e!s}",
            hint="Ensure you have write permissions and the directory is not already initialized",
            original_exception=e,
        ) from e
    except Exception as e:
        raise CLIInitError(
            "An unexpected error occurred during initialization",
            hint=f"Error details: {e!s}",
            original_exception=e,
        ) from e


def get_user_confirmation() -> bool:
    """Display banner and get user confirmation to proceed."""
    display_banner()
    if not typer.confirm("Do you want to continue?", default=True):
        typer.secho("Initialization cancelled.", fg=typer.colors.YELLOW)
        return False
    return True


def setup_nornflow_settings_file(settings: str) -> None:
    """Set up the NornFlow settings file."""
    if os.getenv("NORNFLOW_SETTINGS"):
        return

    target_file = Path(settings) if settings else NORNFLOW_SETTINGS
    if target_file.exists():
        typer.secho(
            f"NornFlow settings file already exists: {target_file}",
            fg=typer.colors.YELLOW,
        )
        return

    shutil.copy(SAMPLE_NORNFLOW_FILE, target_file)
    typer.secho(
        f"Created NornFlow settings file: {target_file}",
        fg=typer.colors.GREEN,
    )


def setup_builder(ctx: typer.Context) -> NornFlowBuilder:
    """Set up and configure the NornFlowBuilder."""
    builder = NornFlowBuilder()
    settings = ctx.obj.get("settings")
    if settings and Path(settings).exists():
        builder.with_settings_path(settings)
    elif NORNFLOW_SETTINGS.exists():
        builder.with_settings_path(NORNFLOW_SETTINGS)
    return builder


def setup_nornir_configs(nornflow: NornFlow) -> None:
    """Set up the Nornir configuration directory derived from settings."""
    nornir_config_file = Path(nornflow.settings.nornir_config_file)
    nornir_config_dir = nornir_config_file.parent

    typer.secho(f"NornFlow will be initialized at {Path.cwd()}", fg=typer.colors.GREEN)

    if nornir_config_dir.exists():
        typer.secho(
            f"Nornir configuration directory already exists: {nornir_config_dir}",
            fg=typer.colors.YELLOW,
        )
        return

    shutil.copytree(SAMPLE_NORNIR_CONFIGS_DIR, nornir_config_dir)
    typer.secho(
        f"Created Nornir configuration directory: {nornir_config_dir}",
        fg=typer.colors.GREEN,
    )


def create_directories_from_settings(nornflow: NornFlow) -> None:
    """Create all directories specified in settings.

    This is the single source of truth for directory creation during init.
    Directories are created based on what's configured in settings, which
    may be default values or custom paths from the user's nornflow.yaml.

    Args:
        nornflow: The initialized NornFlow instance with loaded settings.
    """
    for tasks_dir in nornflow.settings.local_tasks:
        create_directory(Path(tasks_dir))

    for workflows_dir in nornflow.settings.local_workflows:
        create_directory(Path(workflows_dir))

    for filters_dir in nornflow.settings.local_filters:
        create_directory(Path(filters_dir))

    for hooks_dir in nornflow.settings.local_hooks:
        create_directory(Path(hooks_dir))

    create_directory(Path(nornflow.settings.vars_dir))


def setup_sample_content(nornflow: NornFlow) -> None:
    """Set up sample tasks, workflows, and vars files."""
    if nornflow.settings.local_tasks:
        tasks_dir = Path(nornflow.settings.local_tasks[0])
        copy_sample_files_to_dir(
            tasks_dir, [HELLO_WORLD_TASK_FILE, GREET_USER_TASK_FILE], "Created sample tasks in directory: {}"
        )

    if nornflow.settings.local_workflows:
        workflows_dir = Path(nornflow.settings.local_workflows[0])
        copy_sample_files_to_dir(
            workflows_dir, [SAMPLE_WORKFLOW_FILE], "Created a sample 'hello_world' workflow in directory: {}"
        )

    vars_dir = Path(nornflow.settings.vars_dir)
    copy_sample_files_to_dir(
        vars_dir, [SAMPLE_VARS_FILE], "Created a sample 'defaults.yaml' in vars directory: {}"
    )


def copy_sample_files_to_dir(dir_path: Path, sample_files: list[Path], sample_message: str) -> None:
    """Copy sample files to an existing directory."""
    for sample_file in sample_files:
        target_file = dir_path / sample_file.name
        if not target_file.exists():
            shutil.copy(sample_file, target_file)
    typer.secho(sample_message.format(dir_path), fg=typer.colors.GREEN)


def create_directory(dir_path: Path) -> bool:
    """
    Create a directory if it doesn't exist.

    Returns:
        True if directory was created, False if it already existed.
    """
    if dir_path.exists():
        return False
    dir_path.mkdir(parents=True, exist_ok=True)
    return True


def display_banner() -> None:
    """Display the NornFlow initialization banner."""
    typer.secho(INIT_BANNER, fg=typer.colors.MAGENTA, bold=True)
    typer.secho(
        "\n🚀 Welcome to NornFlow initialization! This will set up your project structure.\n",
        fg=typer.colors.GREEN,
        bold=True,
    )


def show_info_post_init(nornflow: NornFlow) -> None:
    """Show information after successful initialization."""
    typer.secho("\n✨ NornFlow project initialized successfully!\n", fg=typer.colors.GREEN, bold=True)
    show_nornflow_settings(nornflow)
    show_catalog(nornflow)
    typer.secho("\n📚 Next steps:", fg=typer.colors.CYAN, bold=True)
    typer.secho("  1. Edit 'nornir_configs/' files to set up your inventory", fg=typer.colors.WHITE)
    typer.secho("  2. Create tasks in the configured tasks directories", fg=typer.colors.WHITE)
    typer.secho("  3. Create workflows in the configured workflows directories", fg=typer.colors.WHITE)
    typer.secho("  4. Run 'nornflow run <task_or_workflow>' to execute", fg=typer.colors.WHITE)
