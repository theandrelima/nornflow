import inspect

import click
from tabulate import tabulate
from termcolor import colored

from nornflow.nornflow import NornFlow


@click.command()
@click.option("--catalog", "-c", is_flag=True, help="Display the task catalog")
@click.option("--settings", "-s", is_flag=True, help="Display current NornFlow Settings and Nornir Configs")
def show(catalog: bool, settings: bool) -> None:
    """
    Displays summary info about NornFlow.
    """
    if catalog:
        show_task_catalog()
    if settings:
        show_settings()


def show_task_catalog() -> None:
    """
    Display the task catalog in a formatted table.
    """
    # Instantiate a NornFlow object
    nornflow = NornFlow()

    # Prepare the data for the table
    table_data = prepare_table_data(nornflow)

    # Colorize and bold the headers
    headers = get_colored_headers()

    # Display the table to get its width
    table = tabulate(table_data, headers=headers, tablefmt="fancy_grid", colalign=("center", "left", "left"))

    # Create and display the banner
    display_banner(table)

    # Display the table
    click.echo(table)


def show_settings() -> None:
    """
    Display the NornFlow settings and Nornir configs.
    """
    # Instantiate a NornFlow object
    nornflow = NornFlow()

    # Display the settings and Nornir configs
    click.echo(colored("NornFlow Settings:", "green", attrs=["bold"]))
    click.echo(nornflow.settings)
    click.echo(colored("\nNornir Configs:", "green", attrs=["bold"]))
    click.echo(nornflow.nornir_configs)


def prepare_table_data(nornflow: NornFlow) -> list[list[str]]:
    """
    Prepare the data for the table.

    Args:
        nornflow (NornFlow): The NornFlow object containing the task catalog.

    Returns:
        List[List[str]]: The prepared table data.
    """
    table_data = []
    for task_name, task_func in nornflow.tasks_catalog.items():
        docstring = (task_func.__doc__ or "No description available").strip()
        docstring = " ".join(docstring.split())  # Remove extra spaces, new lines, and tabs

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


def get_colored_headers() -> list[str]:
    """
    Return the colorized and bold headers.

    Returns:
        List[str]: The colorized and bold headers.
    """
    return [
        colored("Task Name", "blue", attrs=["bold"]),
        colored("Description", "blue", attrs=["bold"]),
        colored("Location", "blue", attrs=["bold"]),
    ]


def display_banner(table: str) -> None:
    """
    Create and display the banner.

    Args:
        table (str): The table string to determine the width for centering the banner.
    """
    banner_text = "TASKS CATALOG"
    banner = colored(banner_text, "magenta", attrs=["bold", "underline"])

    # Center the banner with the table
    table_width = len(table.split("\n")[0])
    centered_banner = banner.center(table_width)

    # Add blank spaces before the banner
    click.echo("\n\n" + centered_banner)