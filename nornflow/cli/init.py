import os
import shutil
from pathlib import Path

import typer

from nornflow import NornFlow, NornFlowBuilder
from nornflow.cli.constants import (
    FILTERS_DIR,
    GREET_USER_TASK_FILE,
    HELLO_WORLD_TASK_FILE,
    HOOKS_DIR,
    INIT_BANNER,
    NORNFLOW_SETTINGS,
    NORNIR_DEFAULT_CONFIG_DIR,
    SAMPLE_NORNFLOW_FILE,
    SAMPLE_NORNIR_CONFIGS_DIR,
    SAMPLE_VARS_FILE,
    SAMPLE_WORKFLOW_FILE,
    TASKS_DIR,
    VARS_DIR,
    WORKFLOWS_DIR,
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

        # Step 1: Copy sample nornir configs directory first
        setup_nornir_configs()

        # Step 2: Copy sample nornflow.yaml settings file
        settings_file = ctx.obj.get("settings", "")
        setup_nornflow_settings_file(settings_file)

        # Step 3: Create default directories
        create_default_directories()

        # Step 4: Build NornFlow from the real settings file that now exists
        builder = setup_builder(ctx)
        nornflow = builder.build()

        # Step 5: Create any additional directories specified in settings
        create_settings_based_directories(nornflow)

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


def setup_nornir_configs() -> None:
    """Set up the Nornir configuration directory."""
    typer.secho(f"NornFlow will be initialized at {NORNIR_DEFAULT_CONFIG_DIR.parent}", fg=typer.colors.GREEN)

    if create_directory(NORNIR_DEFAULT_CONFIG_DIR):
        shutil.copytree(SAMPLE_NORNIR_CONFIGS_DIR, NORNIR_DEFAULT_CONFIG_DIR, dirs_exist_ok=True)
        typer.secho(
            f"Copied sample Nornir configuration to directory: {NORNIR_DEFAULT_CONFIG_DIR}",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"Nornir configuration directory already exists: {NORNIR_DEFAULT_CONFIG_DIR}",
            fg=typer.colors.YELLOW,
        )


def setup_nornflow_settings_file(settings: str) -> None:
    """Set up the NornFlow settings file."""
    if not os.getenv("NORNFLOW_SETTINGS"):
        target_file = Path(settings) if settings else NORNFLOW_SETTINGS
        if not target_file.exists():
            shutil.copy(SAMPLE_NORNFLOW_FILE, target_file)
            typer.secho(
                f"Created NornFlow settings file: {target_file}",
                fg=typer.colors.GREEN,
            )
        else:
            typer.secho(
                f"NornFlow settings file already exists: {target_file}",
                fg=typer.colors.YELLOW,
            )


def create_default_directories() -> None:
    """Create default directories based on constants."""
    create_directory(TASKS_DIR)
    create_directory(WORKFLOWS_DIR)
    create_directory(FILTERS_DIR)
    create_directory(HOOKS_DIR)
    create_directory(VARS_DIR)


def setup_builder(ctx: typer.Context) -> NornFlowBuilder:
    """Set up and configure the NornFlowBuilder."""
    builder = NornFlowBuilder()
    settings = ctx.obj.get("settings")
    if settings and Path(settings).exists():
        builder.with_settings_path(settings)
    elif NORNFLOW_SETTINGS.exists():
        builder.with_settings_path(NORNFLOW_SETTINGS)
    return builder


def create_settings_based_directories(nornflow: NornFlow) -> None:
    """Create any additional directories specified in settings that differ from defaults."""
    for tasks_dir in nornflow.settings.local_tasks_dirs:
        create_directory(Path(tasks_dir))

    for workflows_dir in nornflow.settings.local_workflows_dirs:
        create_directory(Path(workflows_dir))

    for filters_dir in nornflow.settings.local_filters_dirs:
        create_directory(Path(filters_dir))

    for hooks_dir in nornflow.settings.local_hooks_dirs:
        create_directory(Path(hooks_dir))

    vars_dir = Path(nornflow.settings.vars_dir)
    create_directory(vars_dir)


def setup_sample_content(nornflow: NornFlow) -> None:
    """Set up sample tasks, workflows, and vars files."""
    if nornflow.settings.local_tasks_dirs:
        tasks_dir = Path(nornflow.settings.local_tasks_dirs[0])
        copy_sample_files_to_dir(
            tasks_dir, [HELLO_WORLD_TASK_FILE, GREET_USER_TASK_FILE], "Created sample tasks in directory: {}"
        )

    if nornflow.settings.local_workflows_dirs:
        workflows_dir = Path(nornflow.settings.local_workflows_dirs[0])
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
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        return True
    return False


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