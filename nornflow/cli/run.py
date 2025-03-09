import ast
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import typer

from nornflow import NornFlowBuilder, WorkflowFactory
from nornflow.constants import NORNFLOW_SUPPORTED_WORKFLOW_EXTENSIONS, NORNFLOW_SPECIAL_FILTER_KEYS

app = typer.Typer(help="Run NornFlow tasks and workflows")


def csv_to_list(value: str | list | None) -> list[str]:
    """
    Convert a comma-separated string or list into a list of stripped strings.

    Args:
        value: The input value to process.

    Returns:
        List of strings with whitespace stripped.
    """
    if not value:
        return []
    if isinstance(value, list):
        value = ",".join(value)
    return [x.strip() for x in value.split(",")]


def process_value(key: str, value_str: str) -> Any:
    """
    Process a string value into the appropriate Python type.
    
    Handles special cases like ensuring special filter types are always lists.
    
    Args:
        key: The key name
        value_str: The string value to process
        
    Returns:
        Processed value as the appropriate Python type
    """
    # Best effort parsing starting with python literals.
    # Try to parse as Python literal (list, dict, etc.)
    try:
        parsed_value = ast.literal_eval(value_str)
        
        # Special handling for special filter keys - ALWAYS ensure they are lists
        if key in NORNFLOW_SPECIAL_FILTER_KEYS:
            if isinstance(parsed_value, str):
                return [parsed_value]
            elif isinstance(parsed_value, (list, tuple)):
                return list(parsed_value)
            else:
                return [parsed_value]
        else:
            return parsed_value
            
    except (ValueError, SyntaxError):
        # If it's not a valid Python literal, check for CSV format
        if ',' in value_str and not (value_str.startswith('{') or value_str.startswith('[') or value_str.startswith('(')):
            # Looks like a CSV, treat as list
            return [item.strip() for item in value_str.split(',')]
        else:
            # Just a regular string
            # Special handling for special filter keys - ALWAYS ensure they are lists
            if key in NORNFLOW_SPECIAL_FILTER_KEYS:
                return [value_str]
            else:
                return value_str


def parse_key_value_pairs(value: str | None, error_context: str) -> dict[str, Any]:
    """
    Parse a string of key=value pairs into a dictionary with intelligent value parsing.
    
    Handles multiple formats for values:
    - Python literals via ast.literal_eval
    - Simple strings
    - Comma-separated values (auto-converted to lists)
    
    Args:
        value: String containing key=value pairs
        error_context: Context for error messages
        
    Returns:
        Dictionary of parsed key-value pairs
    """
    if not value:
        return {}

    try:
        parsed_dict = {}
        # Split on commas that are not within brackets, quotes, curly brackets, or parentheses
        pairs = re.split(r",(?=(?:[^{}()[\]]*[{([][^{}()[\]]*[})\]])*[^{}()[\]]*$)", value)

        for pair in pairs:
            if "=" not in pair:
                raise typer.BadParameter(f"Invalid {error_context} format: {pair}.")

            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()
            
            # Remove quotes from key if present
            if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
                k = k[1:-1]
            
            # Process the value
            parsed_dict[k] = process_value(k, v)

    except Exception as e:
        raise typer.BadParameter(
            f"{error_context.capitalize()} format examples:\n"
            f"- Simple values: \"key='value'\"\n"
            f"- Lists: \"key=['value1', 'value2']\" or \"key=value1,value2,value3\"\n"
            f"- Dicts: \"key={{'inner_key': 'value'}}\"\n"
            f"Error: {str(e)}"
        ) from e
    
    return parsed_dict


def parse_task_args(value: str | None) -> dict[str, Any]:
    """
    Convert a string of key=value pairs into a dictionary for task arguments.

    Args:
        value: String in one of these formats:
            - "key1='value1', key2=[1,2,3], key3={'subkey': 'subvalue'}"
            - "key1=value1, key2=1,2,3, key3=subvalue"

    Returns:
        Dictionary of task arguments
    """
    return parse_key_value_pairs(value, "arguments")


def parse_inventory_filters(value: str | None) -> dict[str, Any]:
    """
    Convert a string of key=value pairs into a dictionary for inventory filtering.

    Args:
        value: String in one of these formats:
            - "platform='ios', vendor='cisco', hosts=['host1', 'host2']"
            - "platform=ios, vendor=cisco, hosts=host1,host2"

    Returns:
        Dictionary of inventory filters
    """
    return parse_key_value_pairs(value, "inventory filters")


def get_nornflow_builder(
    target: str, args: dict, inventory_filters: dict, dry_run: bool, settings_file: str = ""
) -> NornFlowBuilder:
    """
    Build the workflow using the provided target, arguments, inventory filters, and dry-run option.

    Args:
        target (str): The name of the task or workflow to run.
        args (dict): The task arguments.
        inventory_filters (dict): The inventory filters.
        dry_run (bool): The dry-run option.
        settings_file (str): The path to a YAML settings file for NornFlowSettings.

    Returns:
        NornFlowBuilder: The builder instance with the configured workflow.
    """
    builder = NornFlowBuilder()

    if settings_file:
        builder.with_settings_path(settings_file)

    nornflow_kwargs = {"dry_run": dry_run} if dry_run else {}
    builder.with_kwargs(**nornflow_kwargs)

    if any(target.endswith(ext) for ext in NORNFLOW_SUPPORTED_WORKFLOW_EXTENSIONS):
        target_path = Path(target)
        if target_path.exists():
            absolute_path = target_path.resolve()
            wf = WorkflowFactory.create_from_file(absolute_path)
            if inventory_filters:
                wf.workflow_dict["workflow"]["inventory_filters"] = inventory_filters
            builder.with_workflow_object(wf)
        else:
            builder.with_workflow_name(target)
    else:
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        workflow_dict = {
            "workflow": {
                "name": f"Task {target} - exec {timestamp}",
                "description": (
                    f"ran with 'nornflow run' CLI (args: {args}, filters: {inventory_filters}, "
                    f"dry-run: {dry_run})"
                ),
                "inventory_filters": inventory_filters,
                "tasks": [
                    {"name": target, "args": args or {}},
                ],
            },
        }
        builder.with_workflow_dict(workflow_dict)

    return builder


HOSTS_OPTION = typer.Option(
    None,
    "--hosts",
    "-h",
    callback=csv_to_list,
    help='(to be deprecated) Filters the inventory using a CSV list of hosts to run the task on (e.g "device1,device2")',
)

GROUPS_OPTION = typer.Option(
    None,
    "--groups",
    "-g",
    callback=csv_to_list,
    help='(to be deprecated) Filters the inventory using a comma-separated list of groups to run the task on (e.g "group1,group2")',
)

INVENTORY_FILTERS_OPTION = typer.Option(
    None,
    "--inventory-filters",
    "-i",
    help=f"Inventory filters in flexible format. Special filters ({', '.join(NORNFLOW_SPECIAL_FILTER_KEYS)}) "
         f"receive custom handling.\nExamples:\n- \"platform='ios', vendor='cisco'\"\n- \"hosts=host1,host2\"\n- \"groups=['prod', 'core']\"",
)

ARGS_OPTION = typer.Option(
    None,
    "--args",
    "-a",
    help="Task arguments in flexible format, examples:\n- \"key1='value1', key2=[1,2,3]\"\n- \"commands=show version,show ip int brief\"\n- \"config={'interface': 'value'}\"",  # noqa: E501
)

DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    "-d",
    help="Run in dry-run mode [default: False]",
)


# TODO: Eventually, decommission the legacy options.
@app.command()
def run(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="The name of the task or workflow to run"),
    args: Optional[str] = ARGS_OPTION,
    hosts: Optional[list[str]] = HOSTS_OPTION,
    groups: Optional[list[str]] = GROUPS_OPTION,
    inventory_filters: Optional[str] = INVENTORY_FILTERS_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
) -> None:
    """
    Runs either a cataloged task or workflow - for workflows, the '.yaml'/'.yml' extension must be included.
    """
    settings = ctx.obj.get("settings")
    
    # Parse args into dictionary if provided
    parsed_args = parse_task_args(args) if args else {}
    
    # Parse inventory filters if provided
    parsed_inventory_filters = parse_inventory_filters(inventory_filters) if inventory_filters else {}

    # Combine all filter types into one dictionary
    all_inventory_filters = parsed_inventory_filters.copy()
    
    # Add hosts/groups if provided through legacy options
    legacy_filters_used = False
    
    # Handle both legacy filter options in a consistent way
    legacy_options = {"hosts": hosts, "groups": groups}
    for key, value in legacy_options.items():
        if value:
            legacy_filters_used = True
            # Don't overwrite if already in inventory_filters
            if key in all_inventory_filters:
                typer.secho(
                    f"Warning: Both --{key} and --inventory-filters with '{key}' key provided. "
                    f"Using values from --inventory-filters.",
                    fg=typer.colors.YELLOW
                )
            else:
                all_inventory_filters[key] = value
    
    # Show deprecation warning for legacy filters
    if legacy_filters_used:
        typer.secho(
            "Warning: The --hosts and --groups options will be deprecated and removed in a future version. "
            "Please use --inventory-filters instead (e.g., --inventory-filters \"hosts=host1,host2\" "
            "or \"hosts=['host1', 'host2']\")",
            fg=typer.colors.YELLOW
        )

    builder = get_nornflow_builder(target, parsed_args, all_inventory_filters, dry_run, settings)

    # Update the output message to include all filters
    filter_info = f"filters: {all_inventory_filters}" if all_inventory_filters else "no filters"
    typer.secho(
        f"Running: {target} (args: {parsed_args}, {filter_info}, dry-run: {dry_run})",
        fg=typer.colors.GREEN,
    )

    nornflow = builder.build()
    nornflow.run()