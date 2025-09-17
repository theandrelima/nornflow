import json
import textwrap
from pathlib import Path
from typing import Any

import typer
import yaml
from nornir.core.exceptions import PluginNotRegistered
from tabulate import tabulate
from termcolor import colored

from nornflow import NornFlowBuilder
from nornflow.cli.constants import CWD, DESCRIPTION_FIRST_SENTENCE_LENGTH
from nornflow.cli.exceptions import CLIShowError
from nornflow.exceptions import NornFlowError

app = typer.Typer()


@app.command()
def show(
    ctx: typer.Context,
    catalog: bool = typer.Option(
        False,
        "--catalog",
        "-c",
        help="Display the task, workflow, and filter catalogs (legacy option)",
        hidden=True,
    ),
    catalogs: bool = typer.Option(
        False, "--catalogs", help="Display all catalogs: tasks, filters, and workflows"
    ),
    tasks: bool = typer.Option(False, "--tasks", "-t", help="Display the task catalog"),
    filters: bool = typer.Option(False, "--filters", "-f", help="Display the filter catalog"),
    workflows: bool = typer.Option(False, "--workflows", "-w", help="Display the workflow catalog"),
    settings: bool = typer.Option(False, "--settings", "-s", help="Display current NornFlow Settings"),
    nornir_configs: bool = typer.Option(
        False, "--nornir-configs", "-n", help="Display current Nornir Configs"
    ),
    all: bool = typer.Option(False, "--all", "-a", help="Display all information"),
) -> None:
    """
    Displays summary info about NornFlow.
    """
    show_all_catalogs = catalog or catalogs

    if not any([show_all_catalogs, tasks, filters, workflows, settings, nornir_configs, all]):
        raise typer.BadParameter(
            "You must provide at least one option: --catalogs, --tasks, --filters, --workflows, "
            "--settings, --nornir-configs, or --all."
        )

    try:
        builder = NornFlowBuilder()

        if ctx.obj and ctx.obj.get("settings"):
            settings_path = ctx.obj.get("settings")
            builder.with_settings_path(settings_path)

        nornflow = builder.build()

        if all:
            show_tasks_catalog(nornflow)
            show_filters_catalog(nornflow)
            show_workflows_catalog(nornflow)
            show_nornflow_settings(nornflow)
            show_nornir_configs(nornflow)
        else:
            if show_all_catalogs:
                show_tasks_catalog(nornflow)
                show_filters_catalog(nornflow)
                show_workflows_catalog(nornflow)
            else:
                if tasks:
                    show_tasks_catalog(nornflow)
                if filters:
                    show_filters_catalog(nornflow)
                if workflows:
                    show_workflows_catalog(nornflow)

            if settings:
                show_nornflow_settings(nornflow)
            if nornir_configs:
                show_nornir_configs(nornflow)

    except PluginNotRegistered as e:
        CLIShowError(
            message=f"{e!s}",
            hint="Make sure you have the required Nornir plugin(s) installed in the environment.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2)

    except NornFlowError as e:
        CLIShowError(
            message=f"NornFlow configuration error: {e}",
            hint="Check your NornFlow configuration and verify that all required resources are available.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2)

    except yaml.YAMLError as e:
        CLIShowError(
            message=f"Error parsing YAML file: {e}",
            hint="Check your workflow files for YAML syntax errors.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2)

    except (FileNotFoundError, PermissionError) as e:
        CLIShowError(
            message=f"File system error: {e}",
            hint="Check file permissions and ensure all referenced files exist.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2)

    except Exception as e:
        CLIShowError(
            message=f"Failed to show requested information: {e}",
            hint="Check your configuration and try again.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2)


def show_catalog(nornflow: "NornFlow") -> None:
    """Display all catalogs: tasks, filters, and workflows."""
    show_tasks_catalog(nornflow)
    show_filters_catalog(nornflow)
    show_workflows_catalog(nornflow)


def show_tasks_catalog(nornflow: "NornFlow") -> None:
    """Display the tasks catalog."""
    show_formatted_table(
        "TASKS CATALOG",
        render_task_catalog_table_data,
        ["Task Name", "Description", "Source (python module)"],
        nornflow,
    )


def show_filters_catalog(nornflow: "NornFlow") -> None:
    """Display the filters catalog."""
    show_formatted_table(
        "FILTERS CATALOG",
        render_filters_catalog_table_data,
        ["Filter Name", "Description", "Source (python module)"],
        nornflow,
    )


def show_workflows_catalog(nornflow: "NornFlow") -> None:
    """Display the workflows catalog."""
    show_formatted_table(
        "WORKFLOWS CATALOG",
        render_workflows_catalog_table_data,
        ["Workflow Name", "Description", "Source (file path)"],
        nornflow,
    )


def show_nornflow_settings(nornflow: "NornFlow") -> None:
    """Display the NornFlow settings."""
    show_formatted_table("NORNFLOW SETTINGS", render_settings_table_data, ["Setting", "Value"], nornflow)


def show_nornir_configs(nornflow: "NornFlow") -> None:
    """Display the Nornir configs."""
    show_formatted_table("NORNIR CONFIGS", render_nornir_cfgs_table_data, ["Config", "Value"], nornflow)


def show_formatted_table(
    banner_text: str, table_data_renderer: callable, headers: list[str], nornflow: "NornFlow"
) -> None:
    """Display information in a formatted table.

    Args:
        banner_text: The text to display in the banner.
        table_data_renderer: The function to prepare the data for the table.
        headers: The headers for the table.
        nornflow: The NornFlow object.
    """
    table_data = table_data_renderer(nornflow)

    if not table_data:
        return

    colored_headers = get_colored_headers(headers, "blue")
    colalign = ["center"] + ["left"] * (len(headers) - 1)
    table = tabulate(table_data, headers=colored_headers, tablefmt="rounded_grid", colalign=colalign)
    display_banner(banner_text, table)
    typer.echo(table)


def get_source_from_catalog(catalog, item_name):
    """Get source information from catalog metadata.

    Args:
        catalog: The catalog containing the item.
        item_name: Name of the item to look up.

    Returns:
        The formatted source path.
    """
    item_info = catalog.get_item_info(item_name)

    if not item_info:
        return "Unknown"

    if "module_name" in item_info and "." in item_info["module_name"]:
        return item_info["module_name"]

    if "module_path" in item_info:
        module_path = Path(item_info["module_path"])
        try:
            relative_path = module_path.relative_to(CWD)
            parts = relative_path.parts
            if parts[-1].endswith(".py"):
                parts = list(parts[:-1]) + [parts[-1][:-3]]
            return ".".join(parts)
        except ValueError:
            return str(module_path)

    if "module_name" in item_info and item_name.startswith("napalm_"):
        return f"nornir_napalm.plugins.tasks.{item_name}"

    if "file_path" in item_info:
        file_path = Path(item_info["file_path"])
        try:
            relative_path = file_path.relative_to(CWD)
            return f"./{relative_path}"
        except ValueError:
            return str(file_path)

    return "Unknown"


def render_task_catalog_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """Render the task catalog as a list of lists.

    Args:
        nornflow: The NornFlow object.

    Returns:
        The table data.
    """
    tasks_catalog = nornflow.tasks_catalog
    table_data = []

    task_names = list(sorted(tasks_catalog.get_builtin_items()))
    task_names.extend(sorted(tasks_catalog.get_custom_items()))

    for task_name in task_names:
        task_func = tasks_catalog[task_name]
        docstring = task_func.__doc__ or "No description available"

        first_sentence = docstring.split(".")[0].strip()
        if len(first_sentence) > DESCRIPTION_FIRST_SENTENCE_LENGTH:
            first_sentence = first_sentence[:97] + "..."
        wrapped_text = textwrap.fill(first_sentence, width=60)

        source_path = get_source_from_catalog(tasks_catalog, task_name)

        colored_task_name = colored(task_name, "cyan", attrs=["bold"])
        colored_docstring = colored(wrapped_text, "yellow")
        colored_source = colored(source_path, "light_green")
        table_data.append([colored_task_name, colored_docstring, colored_source])
    return table_data


def render_workflows_catalog_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """Render the workflows catalog as a list of lists.

    Args:
        nornflow: The NornFlow object.

    Returns:
        The table data.
    """
    workflows_catalog = nornflow.workflows_catalog
    table_data = []

    for workflow_name, workflow_path in sorted(workflows_catalog.items()):
        try:
            with workflow_path.open() as f:
                workflow_dict = yaml.safe_load(f)
                description = workflow_dict["workflow"].get("description", "No description available")
        except Exception:
            description = "Could not load description from file"

        description = textwrap.fill(description, width=60)

        source_path = get_source_from_catalog(workflows_catalog, workflow_name)

        colored_workflow_name = colored(workflow_name, "cyan", attrs=["bold"])
        colored_description = colored(description, "yellow")
        colored_source = colored(source_path, "light_green")
        table_data.append([colored_workflow_name, colored_description, colored_source])
    return table_data


def render_filters_catalog_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """Render the filters catalog as a list of lists.

    Args:
        nornflow: The NornFlow object.

    Returns:
        The table data.
    """
    filters_catalog = nornflow.filters_catalog
    table_data = []

    filter_names = list(sorted(filters_catalog.get_builtin_items()))
    filter_names.extend(sorted(filters_catalog.get_custom_items()))

    for filter_name in filter_names:
        filter_func, param_names = filters_catalog[filter_name]
        docstring = filter_func.__doc__ or "No description available"

        first_sentence = docstring.split(".")[0].strip()
        if len(first_sentence) > DESCRIPTION_FIRST_SENTENCE_LENGTH:
            first_sentence = first_sentence[:97] + "..."

        if not param_names:
            param_info = "Parameters: None (host only)"
        else:
            param_info = f"Parameters: {', '.join(param_names)}"

        description = f"{first_sentence}\n{param_info}"

        source_path = get_source_from_catalog(filters_catalog, filter_name)

        colored_filter_name = colored(filter_name, "cyan", attrs=["bold"])
        colored_docstring = colored(description, "yellow")
        colored_source = colored(source_path, "light_green")
        table_data.append([colored_filter_name, colored_docstring, colored_source])
    return table_data


def render_settings_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """Render the NornFlow settings as a list of lists.

    Args:
        nornflow: The NornFlow object.

    Returns:
        The table data.
    """
    settings_dict = nornflow.settings.as_dict
    return render_table_data(settings_dict)


def render_nornir_cfgs_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """Render the Nornir configs as a list of lists.

    Args:
        nornflow: The NornFlow object.

    Returns:
        The table data.
    """
    nornir_configs = nornflow.nornir_configs
    return render_table_data(nornir_configs)


def render_table_data(
    data: dict[str, Any], key_color: str = "cyan", value_color: str = "yellow"
) -> list[list[str]]:
    """Render a dictionary as a list of lists.

    Args:
        data: The dictionary to render.
        key_color: The color for the keys.
        value_color: The color for the values.

    Returns:
        The table data.
    """
    table_data = []
    for key, value in data.items():
        colored_key = colored(key, key_color, attrs=["bold"])
        formatted_value = format_value(value, value_color)
        table_data.append([colored_key, formatted_value])
    return table_data


def format_value(value: Any, color: str = "yellow") -> str:
    """Format the value for display in the table.

    Args:
        value: The value to format.
        color: The color to use for the formatted value.

    Returns:
        The formatted value.
    """
    if isinstance(value, dict):
        value_str = json.dumps(value, indent=2)
        value_str = value_str[1:-1].strip()
    else:
        value_str = str(value)
    return colored(value_str, color)


def get_colored_headers(headers: list[str], color: str) -> list[str]:
    """Color the headers.

    Args:
        headers: The headers to color.
        color: The color to use.

    Returns:
        The colored headers.
    """
    return [colored(header, color, attrs=["bold"]) for header in headers]


def display_banner(banner_text: str, table: str) -> None:
    """Create a banner with the given text and display it above the table.

    Args:
        banner_text: The text to display in the banner.
        table: The table string to determine the width for centering the banner.
    """
    banner = colored(banner_text, "magenta", attrs=["bold", "underline"])

    table_width = len(table.split("\n")[0])
    centered_banner = banner.center(table_width + 5)

    typer.echo("\n\n" + centered_banner)
