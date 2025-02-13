
import typer

from nornflow.nornflow import NornFlow

app = typer.Typer(help="Run NornFlow tasks and workflows")


def csv_to_list(value: str | list | None) -> list[str]:
    """
    Convert a comma-separated string or list into a list of stripped strings.

    This callback function is used by Typer to process command-line arguments
    that accept comma-separated values or lists.

    Args:
        value (Union[str, list, None]): The input value to process.
            - If string: splits on commas ("item1,item2")
            - If list: joins and splits to handle nested commas (["item1,item2"])
            - If None: returns empty list

    Returns:
        List[str]: A list of strings with whitespace stripped from each item.
            Returns empty list if input is None or empty.

    Examples:
        >>> csv_to_list("host1,host2")
        ['host1', 'host2']
        >>> csv_to_list(["host1,host2"])
        ['host1', 'host2']
        >>> csv_to_list(None)
        []
    """
    if not value:
        return []
    if isinstance(value, list):
        value = ",".join(value)
    return [x.strip() for x in value.split(",")]


# Define Options as module-level constants
HOSTS_OPTION = typer.Option(
    [],
    "--hosts",
    "-h",
    callback=csv_to_list,
    help="Comma-separated list of hosts to run the task on",
)

GROUPS_OPTION = typer.Option(
    [],
    "--groups",
    "-g",
    callback=csv_to_list,
    help="Comma-separated list of groups to run the task on",
)

@app.command()
def run(
    target: str = typer.Argument(..., help="The name of the task or workflow to run"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Run in dry-run mode [default: False]"),
    hosts: list[str] = HOSTS_OPTION,
    groups: list[str] = GROUPS_OPTION,
) -> None:
    # ...rest of the function...
    """
    Runs either a cataloged task or workflow - for workflows, the '.yaml' must be included.
    """
    nornflow_kwargs = {"tasks_to_run": [target]}

    if dry_run is not None:
        nornflow_kwargs["dry_run"] = dry_run

    inventory_filters = {}
    if hosts:
        inventory_filters["hosts"] = hosts
    if groups:
        inventory_filters["groups"] = groups

    if inventory_filters:
        nornflow_kwargs["inventory_filters"] = inventory_filters

    typer.secho(
        f"Running task: {target} (dry-run: {dry_run}, hosts: {hosts}, groups: {groups})",
        fg=typer.colors.GREEN,
    )
    nornflow = NornFlow(**nornflow_kwargs)
    nornflow.run()
