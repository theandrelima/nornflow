import ast
import re
from datetime import datetime
from pathlib import Path

import typer

from nornflow import NornFlowBuilder, WorkflowFactory
from nornflow.constants import NORNFLOW_SUPPORTED_WORKFLOW_EXTENSIONS

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
    """
    if not value:
        return []
    if isinstance(value, list):
        value = ",".join(value)
    return [x.strip() for x in value.split(",")]


def parse_task_args(value: str | None) -> dict[str, str | list | dict]:
    """
    Convert a string of key=value pairs into a dictionary, where values can be strs, lists or dictionaries.

    Args:
        value (Optional[str]): String in format "key1='value1', key2=[1,2,3], key3={'subkey': 'subvalue'}"

    Returns:
        Dict[str, Union[str, list, dict]]: Dictionary of task arguments

    """
    if not value:
        return {}

    try:
        parsed_args = {}
        # Split on commas that are not within brackets, quotes, curly brackets, or parentheses
        pairs = re.split(r",(?=(?:[^{}()[\]]*[{([][^{}()[\]]*[})\]])*[^{}()[\]]*$)", value)

        for pair in pairs:
            if "=" not in pair:
                raise typer.BadParameter(f"Invalid argument format: {pair}.")

            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()

            try:
                parsed_args[k] = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                parsed_args[k] = v  # If eval fails, keep the value as a string

    except Exception as e:
        raise typer.BadParameter(
            "Arguments must be in format: \"key1='value1', key2=[1,2,3], key3={'subkey': 'subvalue'}\". Error: " # noqa: E501
            + str(e)
        ) from e
    else:
        return parsed_args


def get_workflow_builder(target: str, args: dict, inventory_filters: dict, dry_run: bool) -> NornFlowBuilder:
    """
    Build the workflow using the provided target, arguments, inventory filters, and dry-run option.

    Args:
        target (str): The name of the task or workflow to run.
        args (dict): The task arguments.
        inventory_filters (dict): The inventory filters.
        dry_run (bool): The dry-run option.

    Returns:
        NornFlowBuilder: The builder instance with the configured workflow.
    """
    builder = NornFlowBuilder()
    nornflow_kwargs = {"dry_run": dry_run} if dry_run else {}
    builder.with_kwargs(**nornflow_kwargs)

    if any(target.endswith(ext) for ext in NORNFLOW_SUPPORTED_WORKFLOW_EXTENSIONS):
        target_path = Path(target)
        if target_path.exists():
            absolute_path = target_path.resolve()
            wf = WorkflowFactory.create_from_file(absolute_path)
            if inventory_filters:
                wf.workflow_dict["workflow_configs"]["inventory_filters"] = inventory_filters
            builder.with_workflow_object(wf)
        else:
            builder.with_workflow_name(target)
    else:
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S") # NOQA: DTZ005
        workflow_dict = {
            "workflow_configs": {
                "name": f"Task {target} - exec {timestamp}",
                "description": (
                    f"ran with 'nornflow run' CLI (args: {args}, hosts: {inventory_filters.get('hosts')}, "
                    f"groups: {inventory_filters.get('groups')}, dry-run: {dry_run})"
                ),
                "inventory_filters": inventory_filters,
            },
            "tasks": [
                {"name": target, "args": args or {}},
            ],
        }
        builder.with_workflow_dict(workflow_dict)

    return builder


# Define Options as module-level constants
HOSTS_OPTION = typer.Option(
    None,
    "--hosts",
    "-h",
    callback=csv_to_list,
    help='Filters the inventory using a comma-separated list of hosts to run the task on (e.g "device1,device2") - can be used with other filter(s)', # noqa: E501
)

GROUPS_OPTION = typer.Option(
    None,
    "--groups",
    "-g",
    callback=csv_to_list,
    help='Filters the inventory using a comma-separated list of groups to run the task on (e.g "group1,group2") - can be used with other filter(s)', # noqa: E501
)

ARGS_OPTION = typer.Option(
    None,
    "--args",
    "-a",
    callback=parse_task_args,
    help="Task arguments in key=value format (e.g., \"key1='value1', key2=[1,2,3], key3={'subkey': 'subvalue'}\")", # noqa: E501
)

DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    "-d",
    help="Run in dry-run mode [default: False]",
)


@app.command()
def run(
    target: str = typer.Argument(..., help="The name of the task or workflow to run"),
    args: str = ARGS_OPTION,
    hosts: list[str] = HOSTS_OPTION,
    groups: list[str] = GROUPS_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
) -> None:
    """
    Runs either a cataloged task or workflow - for workflows, the '.yaml' must be included.
    """
    inventory_filters = {}
    if hosts:
        inventory_filters["hosts"] = hosts
    if groups:
        inventory_filters["groups"] = groups

    builder = get_workflow_builder(target, args, inventory_filters, dry_run)

    typer.secho(
        f"Running: {target} (args: {args}, hosts: {hosts}, groups: {groups}, dry-run: {dry_run})",
        fg=typer.colors.GREEN,
    )

    nornflow = builder.build()
    nornflow.run()
