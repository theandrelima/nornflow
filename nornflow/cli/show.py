import inspect
import json
from pathlib import Path
from typing import Any

import typer
import yaml
from nornir.core.exceptions import PluginNotRegistered
from tabulate import tabulate
from termcolor import colored

from nornflow import NornFlowBuilder
from nornflow.cli.exceptions import NornFlowCLIShowError

app = typer.Typer()


@app.command()
def show(
    catalog: bool = typer.Option(False, "--catalog", "-c", help="Display the task catalog"),
    settings: bool = typer.Option(False, "--settings", "-s", help="Display current NornFlow Settings"),
    nornir_configs: bool = typer.Option(
        False, "--nornir-configs", "-n", help="Display current Nornir Configs"
    ),
    all: bool = typer.Option(False, "--all", "-a", help="Display all information"),
) -> None:
    """
    Displays summary info about NornFlow.
    """
    if not any([catalog, settings, nornir_configs, all]):
        raise typer.BadParameter("You must provide at least one option: --catalog, --settings, --nornir-configs, or --all.")

    try:
        nornflow = NornFlowBuilder().build()

        if all:
            show_catalog(nornflow)
            show_nornflow_settings(nornflow)
            show_nornir_configs(nornflow)
        else:
            if catalog:
                show_catalog(nornflow)
            if settings:
                show_nornflow_settings(nornflow)
            if nornir_configs:
                show_nornir_configs(nornflow)
    except PluginNotRegistered as e:
        NornFlowCLIShowError(
            message=f"{e!s}",
            hint="Make sure you have the required Nornir plugin(s) installed in the environment.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2)  # noqa: B904


def show_catalog(nornflow: "NornFlow") -> None:
    """
    Display the task catalog and workflows catalog.
    """
    show_formatted_table(
        "TASKS CATALOG", render_task_catalog_table_data, ["Task Name", "Description", "Location"], nornflow
    )
    show_formatted_table(
        "WORKFLOWS CATALOG",
        render_workflows_catalog_table_data,
        ["Workflow Name", "Description", "Location"],
        nornflow,
    )


def show_nornflow_settings(nornflow: "NornFlow") -> None:
    """
    Display the NornFlow settings.
    """
    show_formatted_table("NORNFLOW SETTINGS", render_settings_table_data, ["Setting", "Value"], nornflow)


def show_nornir_configs(nornflow: "NornFlow") -> None:
    """
    Display the Nornir configs.
    """
    show_formatted_table("NORNIR CONFIGS", render_nornir_cfgs_table_data, ["Config", "Value"], nornflow)


def show_formatted_table(
    banner_text: str, table_data_renderer: callable, headers: list[str], nornflow: "NornFlow"
) -> None:
    """
    Display information in a formatted table.

    Args:
        banner_text (str): The text to display in the banner.
        table_data_renderer (function): The function to prepare the data for the table.
        headers (list[str]): The headers for the table.
        nornflow (NornFlow): The NornFlow object.
    """
    # Prepare the data for the table
    table_data = table_data_renderer(nornflow)

    if not table_data:
        return

    # Colorize and bold the headers
    colored_headers = get_colored_headers(headers, "blue")

    # Determine column alignment based on the number of headers
    colalign = ["center"] + ["left"] * (len(headers) - 1)

    # Display the table to get its width
    table = tabulate(table_data, headers=colored_headers, tablefmt="rounded_grid", colalign=colalign)

    # Create and display the banner
    display_banner(banner_text, table)

    # Display the table
    typer.echo(table)


def render_task_catalog_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """
    Prepare the data for the task catalog table.

    Args:
        nornflow (NornFlow): The NornFlow object containing the task catalog.

    Returns:
        List[List[str]]: The prepared table data.
    """
    table_data = []
    for task_name, task_func in nornflow.tasks_catalog.items():
        docstring = (task_func.__doc__ or "No description available").strip()

        # Get the Python dotted path to the function
        module = inspect.getmodule(task_func)
        if module is not None:
            module_path = module.__name__
            function_path = f"{module_path}.{task_func.__name__}"
        else:
            # Fallback to the actual file location
            file_path = inspect.getfile(task_func)
            function_path = file_path

        colored_task_name = colored(task_name, "cyan", attrs=["bold"])
        colored_docstring = colored(docstring, "yellow")
        colored_location = colored(function_path, "light_green")
        table_data.append([colored_task_name, colored_docstring, colored_location])
    return table_data


def render_workflows_catalog_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """
    Prepare the data for the workflows catalog table.

    Args:
        nornflow (NornFlow): The NornFlow object containing the workflows catalog.

    Returns:
        List[List[str]]: The prepared table data.
    """
    table_data = []
    for workflow_name, workflow_path in nornflow.workflows_catalog.items():
        with Path(workflow_path).open() as file:
            workflow_data = yaml.safe_load(file)
            description = workflow_data.get("workflow_configs", {}).get(
                "description", "No description available"
            )

        colored_workflow_name = colored(workflow_name, "cyan", attrs=["bold"])
        colored_description = colored(description, "yellow")
        colored_location = colored(str(workflow_path), "light_green")
        table_data.append([colored_workflow_name, colored_description, colored_location])
    return table_data


def render_settings_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """
    Prepare the data for the settings table.

    Args:
        nornflow (NornFlow): The NornFlow object containing the settings.

    Returns:
        List[List[str]]: The prepared settings table data.
    """
    return render_table_data(nornflow.settings.as_dict)


def render_nornir_cfgs_table_data(nornflow: "NornFlow") -> list[list[str]]:
    """
    Prepare the data for the Nornir configs table.

    Args:
        nornflow (NornFlow): The NornFlow object containing the Nornir configs.

    Returns:
        List[List[str]]: The prepared Nornir configs table data.
    """
    return render_table_data(nornflow.nornir_configs)


def render_table_data(
    data: dict[str, Any], key_color: str = "cyan", value_color: str = "yellow"
) -> list[list[str]]:
    """
    Prepare the data for a table.

    Args:
        data (dict[str, Any]): The dictionary containing the data.
        key_color (str): The color to use for the keys.
        value_color (str): The color to use for the values.

    Returns:
        List[List[str]]: The prepared table data.
    """
    table_data = []
    for key, value in data.items():
        colored_key = colored(key, key_color, attrs=["bold"])
        colored_value = format_value(value, value_color)
        table_data.append([colored_key, colored_value])
    return table_data


def format_value(value: Any, color: str = "yellow") -> str:
    """
    Format the value for display in the table.

    Args:
        value (Any): The value to format.
        color (str): The color to use for the formatted value.

    Returns:
        str: The formatted value.
    """
    if isinstance(value, dict):
        # Convert the dictionary to a JSON string with indentation
        value_str = json.dumps(value, indent=2)
        # Remove the first '{' and the last '}'
        value_str = value_str[1:-1].strip()
    else:
        value_str = str(value)
    return colored(value_str, color)


def get_colored_headers(headers: list[str], color: str) -> list[str]:
    """
    Return the colorized and bold headers.

    Args:
        headers (list[str]): The list of headers to be colorized and bolded.
        color (str): The color to be used for the headers.

    Returns:
        List[str]: The colorized and bold headers.
    """
    return [colored(header, color, attrs=["bold"]) for header in headers]


def display_banner(banner_text: str, table: str) -> None:
    """
    Create a banner with the given text and display it above the table.

    Args:
        banner_text (str): The text to display in the banner.
        table (str): The table string to determine the width for centering the banner.
    """
    banner = colored(banner_text, "magenta", attrs=["bold", "underline"])

    # Center the banner with the table
    table_width = len(table.split("\n")[0])
    centered_banner = banner.center(table_width)

    # Add blank spaces before the banner
    typer.echo("\n\n" + centered_banner)