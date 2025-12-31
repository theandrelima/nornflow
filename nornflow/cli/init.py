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
from nornflow.settings import NornFlowSettings

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

        # Step 2: Load settings to know what directories to create
        settings_path = Path(settings_file) if settings_file else NORNFLOW_SETTINGS
        settings = NornFlowSettings.load(settings_path if settings_path.exists() else None)

        # Step 3: Create nornir configs directory (derived from settings)
        setup_nornir_configs(settings)

        # Step 4: Create all directories from settings BEFORE building NornFlow
        create_directories_from_settings(settings)

        # Step 5: Build NornFlow from the settings file (now directories exist)
        builder = setup_builder(ctx)
        nornflow = builder.build()

        # Step 6: Copy sample content to directories
        setup_sample_content(nornflow)

        # Step 7: Show info using the real NornFlow object
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


def setup_nornir_configs(settings: NornFlowSettings) -> None:
    """Set up the Nornir configuration directory derived from settings.

    Args:
        settings: The loaded NornFlowSettings instance.
    """
    nornir_config_file = Path(settings.nornir_config_file)
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


def create_directories_from_settings(settings: NornFlowSettings) -> None:
    """Create all directories specified in settings.

    This is the single source of truth for directory creation during init.
    Directories are created based on what's configured in settings, which
    may be default values or custom paths from the user's nornflow.yaml.

    Args:
        settings: The loaded NornFlowSettings instance with resolved paths.
    """
    for tasks_dir in settings.local_tasks:
        create_directory(Path(tasks_dir))

    for workflows_dir in settings.local_workflows:
        create_directory(Path(workflows_dir))

    for filters_dir in settings.local_filters:
        create_directory(Path(filters_dir))

    for hooks_dir in settings.local_hooks:
        create_directory(Path(hooks_dir))

    for blueprints_dir in settings.local_blueprints:
        create_directory(Path(blueprints_dir))

    create_directory(Path(settings.vars_dir))


def setup_sample_content(nornflow: NornFlow) -> None:
    """Set up sample tasks, workflows, and vars files."""
    if nornflow.settings.local_tasks:
        tasks_dir = Path(nornflow.settings.local_tasks[0])
        copy_sample_files_to_dir(
            tasks_dir,
            [HELLO_WORLD_TASK_FILE, GREET_USER_TASK_FILE],
            created_msg="Created sample tasks in directory: {}",
            skipped_msg="Sample tasks already exist in directory: {}",
        )

    if nornflow.settings.local_workflows:
        workflows_dir = Path(nornflow.settings.local_workflows[0])
        copy_sample_files_to_dir(
            workflows_dir,
            [SAMPLE_WORKFLOW_FILE],
            created_msg="Created sample 'hello_world' workflow in directory: {}",
            skipped_msg="Sample workflow already exists in directory: {}",
        )

    vars_dir = Path(nornflow.settings.vars_dir)
    copy_sample_files_to_dir(
        vars_dir,
        [SAMPLE_VARS_FILE],
        created_msg="Created sample 'defaults.yaml' in vars directory: {}",
        skipped_msg="Sample 'defaults.yaml' already exists in vars directory: {}",
    )


def copy_sample_files_to_dir(
    dir_path: Path,
    sample_files: list[Path],
    created_msg: str,
    skipped_msg: str,
) -> None:
    """Copy sample files to an existing directory if they don't exist.

    Args:
        dir_path: Target directory for the sample files.
        sample_files: List of sample file paths to copy.
        created_msg: Message to display when files are created (use {} for dir_path).
        skipped_msg: Message to display when files already exist (use {} for dir_path).
    """
    files_created = False
    for sample_file in sample_files:
        target_file = dir_path / sample_file.name
        if not target_file.exists():
            shutil.copy(sample_file, target_file)
            files_created = True

    if files_created:
        typer.secho(created_msg.format(dir_path), fg=typer.colors.GREEN)
    else:
        typer.secho(skipped_msg.format(dir_path), fg=typer.colors.YELLOW)


def create_directory(dir_path: Path) -> bool:
    """Create a directory if it doesn't exist.

    Args:
        dir_path: Path to the directory to create.

    Returns:
        True if directory was created, False if it already existed.
    """
    if dir_path.exists():
        typer.secho(f"Directory already exists: {dir_path}", fg=typer.colors.YELLOW)
        return False
    dir_path.mkdir(parents=True, exist_ok=True)
    typer.secho(f"Created directory: {dir_path}", fg=typer.colors.GREEN)
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
