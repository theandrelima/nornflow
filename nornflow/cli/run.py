import ast
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from nornflow import NornFlowBuilder
from nornflow.cli.exceptions import CLIRunError
from nornflow.constants import (
    FailureStrategy,
    NORNFLOW_SPECIAL_FILTER_KEYS,
    NORNFLOW_SUPPORTED_YAML_EXTENSIONS,
)
from nornflow.exceptions import NornFlowError
from nornflow.utils import normalize_failure_strategy

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


def process_value(key: str, value_str: str) -> Any:  # noqa: PLR0911
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
            if isinstance(parsed_value, list | tuple):
                return list(parsed_value)
            return [parsed_value]
        return parsed_value

    except (ValueError, SyntaxError):
        # If it's not a valid Python literal, check for CSV format
        if "," in value_str and not value_str.startswith(("{", "[", "(")):
            # Looks like a CSV, treat as list
            return [item.strip() for item in value_str.split(",")]

        # Just a regular string
        # Special handling for special filter keys - ALWAYS ensure they are lists
        if key in NORNFLOW_SPECIAL_FILTER_KEYS:
            return [value_str]
        return value_str


def parse_key_value_pairs(value: str | None, error_context: str) -> dict[str, Any]:
    """
    Parse a string of key=value pairs into a dictionary with intelligent value parsing.

    This function splits the input string on commas, but only those not inside quotes
    or brackets, using a regex lookahead to avoid breaking nested structures. Each
    key=value pair is then processed: keys have quotes stripped if present, and values
    are handled based on quoting—quoted values become strings (with quotes removed),
    while unquoted values are evaluated as Python literals (e.g., lists, dicts) via
    ast.literal_eval, falling back to strings if evaluation fails. Special keys like
    'hosts' and 'groups' auto-convert unquoted comma-separated strings to lists.

    Parsing steps:
    1. If input is empty, return empty dict.
    2. Use regex to split on commas outside quotes/brackets.
    3. For each pair, split on '=' and strip whitespace.
    4. Strip quotes from keys if present.
    5. For values: If quoted (single/double), treat as string (unquote). If unquoted,
       attempt literal evaluation; fallback to string.
    6. Handle special keys for list conversion.
    7. Raise error with examples on failure.

    Args:
        value: String containing key=value pairs, e.g., "a=1,b='hello',c=[1,2]".
        error_context: Context for error messages, e.g., "vars" or "inventory filters".

    Returns:
        Dictionary of parsed key-value pairs.

    Raises:
        CLIRunError: If parsing fails, with examples.

    Examples:
        - Simple unquoted: "a=1,b=hello" -> {"a": 1, "b": "hello"}
        - Quoted strings: "a='hello',b=\"world\"" -> {"a": "hello", "b": "world"}
        - Lists: "a=[1,2,3],b=['x','y']" -> {"a": [1, 2, 3], "b": ["x", "y"]}
        - Dicts: "a={'key': 'val'},b={\"k\": 1}" -> {"a": {"key": "val"}, "b": {"k": 1}}
        - Special keys: "hosts=host1,host2" -> {"hosts": ["host1", "host2"]}
        - Nested/complex: "a=[1,{'b': 2}],c='not,eval'" -> {"a": [1, {"b": 2}], "c": "not,eval"}
        - Invalid: "a=1,b" -> Raises CLIRunError with examples.
    """
    if not value:
        return {}

    try:
        parsed_dict = {}
        # This pattern splits on commas that are NOT inside any type of quotes or brackets
        pairs = re.split(
            r"""
            ,                           # Match a comma
            (?=                         # Followed by (positive lookahead)
                (?:                     # Non-capturing group
                    [^"'{}()[\]]*       # Any chars except quotes/brackets
                    (?:                 # Non-capturing group
                        "[^"]*"         # Double quoted content
                        |'[^']*'        # OR single quoted content
                        |{[^}]*}        # OR curly bracket content
                        |\([^)]*\)      # OR parentheses content
                        |\[[^\]]*\]     # OR square bracket content
                    )
                )*                      # Zero or more times
                [^"'{}()[\]]*           # Any chars except quotes/brackets
                $                       # Until end of string
            )
            """,
            value,
            flags=re.VERBOSE,
        )

        for pair in pairs:
            if "=" not in pair:
                raise CLIRunError(f"Invalid {error_context} format: {pair}.")

            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()

            # Remove quotes from key if present
            if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
                k = k[1:-1]

            # Check if value is quoted
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                # Treat as string, remove quotes
                v = v[1:-1]
                parsed_dict[k] = v
            else:
                # Attempt literal evaluation for unquoted values
                parsed_dict[k] = process_value(k, v)

    except Exception as e:
        raise CLIRunError(
            f"{error_context.capitalize()} format examples:\n"
            f"- Simple values: \"key='value'\"\n"
            f"- Lists: \"key=['value1', 'value2']\" or \"key=value1,value2,value3\"\n"
            f"- Dicts: \"key={{'inner_key': 'value'}}\"\n"
            f"Error: {e!s}"
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


def parse_vars(value: str | None) -> dict[str, Any]:
    """
    Convert a string of key=value pairs into a dictionary for vars.

    Args:
        value: String in one of these formats:
            - "server='10.0.0.1', debug=True, ports=[22,80]"
            - "server=10.0.0.1, debug=true, ports=22,80"

    Returns:
        Dictionary of vars
    """
    return parse_key_value_pairs(value, "vars")


def parse_processors(value: str | None) -> list[dict[str, Any]]:
    """
    Parse a string of processor configurations into a list of processor configs.

    Format examples:
      - Single processor: "class='nornflow.builtins.DefaultNornFlowProcessor',args={}"
      - Multiple processors:
        "class='package.module.Processor1',args={};class='package.Processor2',args={'key':'value'}"

    Args:
        value: String describing processor configurations

    Returns:
        List of processor configurations
    """
    if not value:
        return []

    result = []
    # Split by semicolons to separate multiple processors
    processor_strings = value.split(";")

    for proc_str in processor_strings:
        if not proc_str.strip():
            continue

        # Parse as key-value pairs
        proc_dict = parse_key_value_pairs(proc_str, "processor")

        # Validate required 'class' key
        if "class" not in proc_dict:
            raise CLIRunError("Each processor must have a 'class' key specified")

        # If args not specified, add empty dict
        if "args" not in proc_dict:
            proc_dict["args"] = {}

        result.append(proc_dict)

    return result


def parse_failure_strategy(value: str | None) -> FailureStrategy | None:
    """
    Parse a string into a FailureStrategy enum value.

    Delegates to shared utility for consistent validation and error handling.

    Args:
        value: String representing the failure strategy (case-insensitive).
               Supports both hyphen and underscore variations.

    Returns:
        FailureStrategy enum value or None if not provided.

    Raises:
        CLIRunError: If the value is invalid.
    """
    if not value:
        return None

    return normalize_failure_strategy(value, CLIRunError)


def get_nornflow_builder(
    target: str,
    args: dict[str, Any],
    inventory_filters: dict[str, Any],
    settings_file: str = "",
    processors: list[dict[str, Any]] | None = None,
    vars: dict[str, Any] | None = None,
    failure_strategy: FailureStrategy | None = None,
    dry_run: bool = False,
) -> NornFlowBuilder:
    """
    Build the workflow using the provided target, arguments, inventory filters, and dry-run option.

    Args:
        target (str): The name of the task or workflow to run.
        args (dict): The task arguments.
        inventory_filters (dict): The inventory filters.
        settings_file (str): The path to a YAML settings file for NornFlowSettings.
        processors (list): The processor configurations.
        vars (dict): Vars with highest precedence.
        failure_strategy (FailureStrategy): Failure strategy with highest precedence.
        dry_run (bool): Whether to perform a dry run.

    Returns:
        NornFlowBuilder: The builder instance with the configured workflow.
    """
    processors = processors or []

    builder = NornFlowBuilder()

    if settings_file:
        builder.with_settings_path(settings_file)

    # Add processors using dedicated method if specified
    if processors:
        builder.with_processors(processors)

    # Add vars if specified
    if vars:
        builder.with_vars(vars)

    # Add filters if specified
    if inventory_filters:
        builder.with_filters(inventory_filters)

    # Add failure strategy if specified
    if failure_strategy:
        builder.with_failure_strategy(failure_strategy)

    # Add dry_run if specified
    if dry_run:
        builder.with_kwargs(dry_run=dry_run)

    if any(target.endswith(ext) for ext in NORNFLOW_SUPPORTED_YAML_EXTENSIONS):
        target_path = Path(target)
        if target_path.exists():
            absolute_path = target_path.resolve()
            builder.with_workflow_path(str(absolute_path))
        else:
            builder.with_workflow_name(target)
    else:
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        workflow_dict = {
            "workflow": {
                "name": f"Task {target} - exec {timestamp}",
                "description": (f"ran with 'nornflow run' CLI (args: {args}, filters: {inventory_filters})"),
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
    help='(to be deprecated) Filters the inventory using a CSV list of hosts to run the task on (e.g "device1,device2")',  # noqa: E501
)

GROUPS_OPTION = typer.Option(
    None,
    "--groups",
    "-g",
    callback=csv_to_list,
    help='(to be deprecated) Filters the inventory using a comma-separated list of groups to run the task on (e.g "group1,group2")',  # noqa: E501
)

INVENTORY_FILTERS_OPTION = typer.Option(
    None,
    "--inventory-filters",
    "-i",
    help="Inventory filters in flexible format. "
    "\nExamples:\n- \"platform='ios', vendor='cisco'\"\n- \"hosts=host1,host2\""
    "\n- \"groups=['prod', 'core']\"\n- \"custom_filter=\" (parameterless filter)",  # Added example
)

ARGS_OPTION = typer.Option(
    None,
    "--args",
    "-a",
    help="Task arguments in flexible format, examples:\n- \"key1='value1', key2=[1,2,3]\"\n- \"commands=show version,show ip int brief\"\n- \"config={'interface': 'value'}\"",  # noqa: E501
)

VARS_OPTION = typer.Option(
    None,
    "--vars",
    "-v",
    help="Vars in flexible format, with highest precedence in the variables system."
    "\nExamples:\n- \"server='10.0.0.1', debug=True\"\n- \"domain='example.com', ports=[80,443]\"",
)

DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    "-d",
    help="Run in dry-run mode [default: False]",
)

PROCESSORS_OPTION = typer.Option(
    None,
    "--processors",
    "-p",
    help="Processor configurations in format: \"class='package.ProcessorClass',args={'key':'value'}\". "
    "Multiple processors can be separated with semicolons.",
)

FAILURE_STRATEGY_OPTION = typer.Option(
    None,
    "--failure-strategy",
    "-f",
    help="Failure handling strategy. "
    "Options: 'skip-failed' (default, skip failed hosts), 'fail-fast' (stop on first error), "
    "'run-all' (run all tasks, report failures at end). "
    "Both hyphen and underscore variations are accepted (e.g., 'fail-fast' or 'fail_fast').",
)


# TODO: Eventually, decommission the legacy options.
@app.command()
def run(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="The name of the task or workflow to run"),
    args: str | None = ARGS_OPTION,
    hosts: list[str] | None = HOSTS_OPTION,
    groups: list[str] | None = GROUPS_OPTION,
    inventory_filters: str | None = INVENTORY_FILTERS_OPTION,
    processors: str | None = PROCESSORS_OPTION,
    vars: str | None = VARS_OPTION,
    failure_strategy: str | None = FAILURE_STRATEGY_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
) -> None:
    """
    Runs either a cataloged task or workflow - for workflows, the '.yaml'/'.yml' extension must be included.
    """
    try:
        settings = ctx.obj.get("settings")

        # Parse args into dictionary if provided
        parsed_args = parse_task_args(args) if args else {}

        # Parse inventory filters if provided
        parsed_inventory_filters = parse_inventory_filters(inventory_filters) if inventory_filters else {}

        # Parse vars if provided
        parsed_vars = parse_vars(vars) if vars else {}

        # Parse processors if provided
        parsed_processors = parse_processors(processors) if processors else []

        # Parse failure strategy if provided
        parsed_failure_strategy = parse_failure_strategy(failure_strategy) if failure_strategy else None

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
                        fg=typer.colors.YELLOW,
                    )
                else:
                    all_inventory_filters[key] = value

        # Show deprecation warning for legacy filters
        if legacy_filters_used:
            typer.secho(
                "Warning: The --hosts and --groups options will be deprecated and removed in a future version. "  # noqa: E501
                'Please use --inventory-filters instead (e.g., --inventory-filters "hosts=host1,host2" '
                "or \"hosts=['host1', 'host2']\")",
                fg=typer.colors.YELLOW,
            )

        builder = get_nornflow_builder(
            target,
            parsed_args,
            all_inventory_filters,
            settings,
            parsed_processors,
            parsed_vars,
            parsed_failure_strategy,
            dry_run,
        )

        nornflow = builder.build()

        # Capture the exit code from nornflow.run()
        exit_code = nornflow.run()

        # Exit with the workflow's exit code if non-zero, otherwise return normally
        if exit_code != 0:
            sys.exit(exit_code)

    except NornFlowError as e:
        CLIRunError(
            message=f"NornFlow error while running {target}: {e}",
            original_exception=e,
        ).show()
        raise typer.Exit(code=102)  # noqa: B904

    except FileNotFoundError as e:
        CLIRunError(
            message=f"File not found: {e}",
            hint=f"Check that the file '{target}' exists and is accessible.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=103)  # noqa: B904

    except PermissionError as e:
        CLIRunError(
            message=f"Permission denied: {e}",
            hint="Check that you have sufficient permissions to access the required files.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=104)  # noqa: B904

    except Exception as e:
        CLIRunError(
            message=f"Unexpected error while running {target}: {e}",
            hint="This may be a bug. Please report it if the issue persists.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=105)  # noqa: B904
