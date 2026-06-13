import json
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer
import yaml
from nornir.core.exceptions import PluginNotRegistered
from tabulate import tabulate
from termcolor import colored

from nornflow import NornFlowBuilder
from nornflow.catalogs import Catalog
from nornflow.cli.constants import CWD
from nornflow.cli.exceptions import CLIShowError
from nornflow.constants import (
    REDACTION_FULL_DISABLED_WARNING,
    REDACTION_LOGS_DISABLED_WARNING,
    REDACTION_TERMINAL_DISABLED_WARNING,
)
from nornflow.exceptions import NornFlowError
from nornflow.logger import logger
from nornflow.masking import mask_structure

app = typer.Typer()


@app.command()
def show(  # noqa: PLR0912
    ctx: typer.Context,
    catalog: bool = typer.Option(
        False,
        "--catalog",
        "-c",
        help="Display the task, workflow, and filter catalogs (legacy option)",
        hidden=True,
    ),
    catalogs: bool = typer.Option(
        False, "--catalogs", help="Display all catalogs: tasks, filters, workflows, and blueprints"
    ),
    tasks: bool = typer.Option(False, "--tasks", "-t", help="Display the task catalog"),
    filters: bool = typer.Option(False, "--filters", "-f", help="Display the filter catalog"),
    workflows: bool = typer.Option(False, "--workflows", "-w", help="Display the workflow catalog"),
    blueprints: bool = typer.Option(False, "--blueprints", "-b", help="Display the blueprint catalog"),
    j2_filters: bool = typer.Option(False, "--j2-filters", "-j", help="Display the Jinja2 filters catalog"),
    hooks: bool = typer.Option(False, "--hooks", help="Display the hooks catalog"),
    settings: bool = typer.Option(False, "--settings", "-s", help="Display current NornFlow Settings"),
    nornir_configs: bool = typer.Option(
        False, "--nornir-configs", "-n", help="Display current Nornir Configs"
    ),
    all: bool = typer.Option(False, "--all", "-a", help="Display all information"),
    no_redact: bool = typer.Option(
        False,
        "--no-redact",
        help="Disable terminal output redaction. Log redaction follows settings. Use with caution.",
    ),
) -> None:
    """
    Displays summary info about NornFlow.
    """
    show_all_catalogs = catalog or catalogs

    if not any(
        [
            show_all_catalogs,
            tasks,
            filters,
            workflows,
            blueprints,
            j2_filters,
            hooks,
            settings,
            nornir_configs,
            all,
        ]
    ):
        raise typer.BadParameter(
            "You must provide at least one option: --catalogs, --tasks, --filters, --workflows, "
            "--blueprints, --j2-filters, --hooks, --settings, --nornir-configs, or --all."
        )

    try:
        builder = NornFlowBuilder()

        if ctx.obj and ctx.obj.get("settings"):
            settings_path = ctx.obj.get("settings")
            builder.with_settings_path(settings_path)

        if no_redact:
            builder.with_kwargs(no_redact=True)

        nornflow = builder.build()

        if not nornflow.redaction_enabled and not nornflow.logs_redaction_enabled:
            typer.secho(REDACTION_FULL_DISABLED_WARNING, fg=typer.colors.YELLOW)
        elif not nornflow.redaction_enabled:
            typer.secho(REDACTION_TERMINAL_DISABLED_WARNING, fg=typer.colors.YELLOW)
        elif not nornflow.logs_redaction_enabled:
            typer.secho(REDACTION_LOGS_DISABLED_WARNING, fg=typer.colors.YELLOW)

        redaction_enabled = nornflow.redaction_enabled

        if all:
            show_tasks_catalog(nornflow)
            show_filters_catalog(nornflow)
            show_workflows_catalog(nornflow)
            show_blueprints_catalog(nornflow)
            show_j2_filters_catalog(nornflow)
            show_hooks_catalog(nornflow)
            show_nornflow_settings(nornflow, redaction_enabled=redaction_enabled)
            show_nornir_configs(nornflow, redaction_enabled=redaction_enabled)
        else:
            if show_all_catalogs:
                show_tasks_catalog(nornflow)
                show_filters_catalog(nornflow)
                show_workflows_catalog(nornflow)
                show_blueprints_catalog(nornflow)
                show_j2_filters_catalog(nornflow)
                show_hooks_catalog(nornflow)
            else:
                if tasks:
                    show_tasks_catalog(nornflow)
                if filters:
                    show_filters_catalog(nornflow)
                if workflows:
                    show_workflows_catalog(nornflow)
                if blueprints:
                    show_blueprints_catalog(nornflow)
                if j2_filters:
                    show_j2_filters_catalog(nornflow)
                if hooks:
                    show_hooks_catalog(nornflow)

            if settings:
                show_nornflow_settings(nornflow, redaction_enabled=redaction_enabled)
            if nornir_configs:
                show_nornir_configs(nornflow, redaction_enabled=redaction_enabled)

    except PluginNotRegistered as e:
        CLIShowError(
            message=f"{e!s}",
            hint="Make sure you have the required Nornir plugin(s) installed in the environment.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2) from None

    except NornFlowError as e:
        CLIShowError(
            message=f"NornFlow configuration error: {e}",
            hint="Check your NornFlow configuration and verify that all required resources are available.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2) from None

    except yaml.YAMLError as e:
        CLIShowError(
            message=f"Error parsing YAML file: {e}",
            hint="Check your workflow files for YAML syntax errors.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2) from None

    except (FileNotFoundError, PermissionError) as e:
        CLIShowError(
            message=f"File system error: {e}",
            hint="Check file permissions and ensure all referenced files exist.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2) from None

    except Exception as e:
        logger.exception(f"Failed to show requested information: {e}")
        CLIShowError(
            message=f"Failed to show requested information: {e}",
            hint="Check your configuration and try again.",
            original_exception=e,
        ).show()
        raise typer.Exit(code=2) from None


def show_catalog(nornflow: "NornFlow") -> None:
    """Display all catalogs: tasks, filters, workflows, blueprints, j2_filters, and hooks."""
    show_tasks_catalog(nornflow)
    show_filters_catalog(nornflow)
    show_workflows_catalog(nornflow)
    show_blueprints_catalog(nornflow)
    show_j2_filters_catalog(nornflow)
    show_hooks_catalog(nornflow)


CATALOG_TABLE_HEADERS_BASE = [
    "Qualified Name",
    "Description",
]


def get_catalog_table_headers(include_collision: bool) -> list[str]:
    """Build catalog table headers, omitting Collision when not needed."""
    headers = list(CATALOG_TABLE_HEADERS_BASE)
    if include_collision:
        headers.append("Collision")
    return headers


def catalog_has_collisions(catalog: Catalog) -> bool:
    """Return True if any catalog entry has collision metadata."""
    return any(meta.get("collision") for meta in catalog.sources.values())


def _catalog_qualified_names(catalog: Catalog) -> list[str]:
    """Return catalog keys in display order: built-ins first, then custom."""
    builtin_names = sorted(catalog.get_builtin_items())
    custom_names = sorted(catalog.get_custom_items())
    if builtin_names or custom_names:
        return builtin_names + custom_names
    return sorted(catalog.keys())


def show_tasks_catalog(nornflow: "NornFlow") -> None:
    """Display the tasks catalog."""
    show_catalog_formatted_table(
        "TASKS CATALOG",
        render_task_catalog_table_data,
        nornflow,
    )


def show_filters_catalog(nornflow: "NornFlow") -> None:
    """Display the filters catalog."""
    show_catalog_formatted_table(
        "FILTERS CATALOG",
        render_filters_catalog_table_data,
        nornflow,
    )


def show_workflows_catalog(nornflow: "NornFlow") -> None:
    """Display the workflows catalog."""
    show_catalog_formatted_table(
        "WORKFLOWS CATALOG",
        render_workflows_catalog_table_data,
        nornflow,
    )


def show_blueprints_catalog(nornflow: "NornFlow") -> None:
    """Display the blueprints catalog."""
    show_catalog_formatted_table(
        "BLUEPRINTS CATALOG",
        render_blueprints_catalog_table_data,
        nornflow,
    )


def show_j2_filters_catalog(nornflow: "NornFlow") -> None:
    """Display the Jinja2 filters catalog."""
    show_catalog_formatted_table(
        "JINJA2 FILTERS CATALOG",
        render_j2_filters_catalog_table_data,
        nornflow,
    )


def show_hooks_catalog(nornflow: "NornFlow") -> None:
    """Display the hooks catalog."""
    show_catalog_formatted_table(
        "HOOKS CATALOG",
        render_hooks_catalog_table_data,
        nornflow,
    )


def show_nornflow_settings(nornflow: "NornFlow", *, redaction_enabled: bool = True) -> None:
    """Display the NornFlow settings.

    Args:
        nornflow: The NornFlow object.
        redaction_enabled: When False, sensitive values are shown in plain text.
    """
    show_formatted_table(
        "NORNFLOW SETTINGS",
        lambda nf: render_settings_table_data(nf, redaction_enabled=redaction_enabled),
        ["Setting", "Value"],
        nornflow,
    )


def show_nornir_configs(nornflow: "NornFlow", *, redaction_enabled: bool = True) -> None:
    """Display the Nornir configs.

    Args:
        nornflow: The NornFlow object.
        redaction_enabled: When False, sensitive values are shown in plain text.
    """
    show_formatted_table(
        "NORNIR CONFIGS",
        lambda nf: render_nornir_cfgs_table_data(nf, redaction_enabled=redaction_enabled),
        ["Config", "Value"],
        nornflow,
    )


def show_catalog_formatted_table(
    banner_text: str, table_data_renderer: Callable, nornflow: "NornFlow"
) -> None:
    """Display a catalog table with headers derived from rendered data."""
    table_data, headers = table_data_renderer(nornflow)

    if not table_data:
        return

    colored_headers = get_colored_headers(headers, "blue")
    colalign = ["center"] + ["left"] * (len(headers) - 1)
    table = tabulate(table_data, headers=colored_headers, tablefmt="rounded_grid", colalign=colalign)
    display_banner(banner_text, table)
    typer.echo(table)


def show_formatted_table(
    banner_text: str, table_data_renderer: Callable, headers: list[str], nornflow: "NornFlow"
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


def get_source_from_catalog(catalog: Catalog, item_name: str) -> str:  # noqa: PLR0911
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
                parts = [*list(parts[:-1]), parts[-1][:-3]]
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


def render_catalog_table_data(
    catalog: Catalog,
    *,
    format_description: Callable[[str, dict[str, Any]], str] | None = None,
) -> tuple[list[list[str]], list[str]]:
    """Render catalog rows and headers, omitting Collision when unused."""
    include_collision = catalog_has_collisions(catalog)
    headers = get_catalog_table_headers(include_collision)
    table_data: list[list[str]] = []

    for qualified_name in _catalog_qualified_names(catalog):
        meta = catalog.sources.get(qualified_name, {})
        collision = meta.get("collision", "")
        if format_description:
            description = format_description(qualified_name, meta)
        else:
            description = meta.get("description", "No description available")
        table_data.append(
            get_colored_catalog_row(
                qualified_name,
                description,
                collision,
                include_collision=include_collision,
            )
        )

    return table_data, headers


def render_callable_catalog_table_data(catalog) -> tuple[list[list[str]], list[str]]:
    """Render a callable catalog (tasks, filters, or J2 filters) as a list of lists."""
    return render_catalog_table_data(catalog)


def render_task_catalog_table_data(nornflow: "NornFlow") -> tuple[list[list[str]], list[str]]:
    """Render the task catalog as a list of lists."""
    return render_callable_catalog_table_data(nornflow.tasks_catalog)


def render_workflows_catalog_table_data(nornflow: "NornFlow") -> tuple[list[list[str]], list[str]]:
    """Render the workflows catalog as a list of lists."""
    return render_file_based_catalog_table_data(nornflow.workflows_catalog, nornflow)


def render_blueprints_catalog_table_data(nornflow: "NornFlow") -> tuple[list[list[str]], list[str]]:
    """Render the blueprints catalog as a list of lists."""
    return render_file_based_catalog_table_data(nornflow.blueprints_catalog, nornflow)


def render_filters_catalog_table_data(nornflow: "NornFlow") -> tuple[list[list[str]], list[str]]:
    """Render the filters catalog as a list of lists."""

    def format_filter_description(qualified_name: str, meta: dict[str, Any]) -> str:
        description = meta.get("description", "No description available")
        item = nornflow.filters_catalog[qualified_name]
        if isinstance(item, tuple) and len(item) > 1:
            param_names = item[1]
            if param_names:
                description += f"\nParameters: {', '.join(param_names)}"
            else:
                description += "\nParameters: None (host only)"
        return textwrap.fill(description, width=60)

    return render_catalog_table_data(
        nornflow.filters_catalog,
        format_description=format_filter_description,
    )


def render_j2_filters_catalog_table_data(nornflow: "NornFlow") -> tuple[list[list[str]], list[str]]:
    """Render the Jinja2 filters catalog as a list of lists."""
    return render_callable_catalog_table_data(nornflow.j2_filters_catalog)


def render_hooks_catalog_table_data(nornflow: "NornFlow") -> tuple[list[list[str]], list[str]]:
    """Render the hooks catalog as a list of lists."""

    def format_hook_description(_qualified_name: str, meta: dict[str, Any]) -> str:
        description = meta.get("description", "No description available")
        return textwrap.fill(description, width=60)

    return render_catalog_table_data(
        nornflow.hooks_catalog,
        format_description=format_hook_description,
    )


def render_settings_table_data(nornflow: "NornFlow", *, redaction_enabled: bool = True) -> list[list[str]]:
    """Render the NornFlow settings as a list of lists.

    Args:
        nornflow: The NornFlow object.
        redaction_enabled: When False, sensitive values are shown in plain text.

    Returns:
        The table data.
    """
    settings_dict = nornflow.settings.as_dict
    return render_table_data(
        settings_dict,
        redaction_enabled=redaction_enabled,
        sensitive_names=nornflow.redaction_sensitive_names,
    )


def render_nornir_cfgs_table_data(nornflow: "NornFlow", *, redaction_enabled: bool = True) -> list[list[str]]:
    """Render the Nornir configs as a list of lists.

    Args:
        nornflow: The NornFlow object.
        redaction_enabled: When False, sensitive values are shown in plain text.

    Returns:
        The table data.
    """
    nornir_configs = nornflow.nornir_configs
    return render_table_data(
        nornir_configs,
        redaction_enabled=redaction_enabled,
        sensitive_names=nornflow.redaction_sensitive_names,
    )


def render_table_data(
    data: dict[str, Any],
    key_color: str = "cyan",
    value_color: str = "yellow",
    *,
    redaction_enabled: bool = True,
    sensitive_names: frozenset[str] | None = None,
) -> list[list[str]]:
    """Render a dictionary as a list of lists, redacting sensitive values before display.

    Applies built-in 'PROTECTED_KEYWORDS' (segment-aware) and user
    'sensitive_names' (exact match) before formatting table rows.

    Args:
        data: The dictionary to render.
        key_color: The color for the keys.
        value_color: The color for the values.
        redaction_enabled: When False, skip redaction and show values as-is.
        sensitive_names: User-declared identifiers from 'redaction.sensitive_names'.

    Returns:
        The table data with sensitive values replaced by REDACTED unless redaction is disabled.
    """
    masked = mask_structure(data, reveal=not redaction_enabled, sensitive_names=sensitive_names)
    table_data = []
    for key, value in masked.items():
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

    table_width = len(table.split("\n", maxsplit=1)[0])
    centered_banner = banner.center(table_width + 5)

    typer.echo("\n\n" + centered_banner)


def render_file_based_catalog_table_data(
    catalog, nornflow: "NornFlow"
) -> tuple[list[list[str]], list[str]]:
    """Render a file-based catalog (workflows or blueprints) as a list of lists."""

    def format_file_description(_qualified_name: str, meta: dict[str, Any]) -> str:
        description = meta.get("description", "No description available")
        return textwrap.fill(description, width=60)

    return render_catalog_table_data(catalog, format_description=format_file_description)


def format_colored_qualified_name(qualified_name: str) -> str:
    """Color the namespace and asset name portions of a qualified catalog key."""
    if "." not in qualified_name:
        return colored(qualified_name, "cyan", attrs=["bold"])

    namespace, _, asset_name = qualified_name.partition(".")
    return (
        colored(namespace, "green", attrs=["bold"])
        + colored(".", "white")
        + colored(asset_name, "cyan", attrs=["bold"])
    )


def get_colored_catalog_row(
    qualified_name: str,
    desc: str,
    collision: str = "",
    *,
    include_collision: bool = True,
) -> list[str]:
    """Create a colored table row for namespaced catalog items."""
    row = [
        format_colored_qualified_name(qualified_name),
        colored(desc, "yellow"),
    ]
    if include_collision:
        collision_display = collision or "—"
        row.append(colored(collision_display, "magenta" if collision else "white"))
    return row


def get_colored_row(name: str, desc: str, source: str) -> list[str]:
    """Create a colored table row for catalog items.

    Args:
        name: The item name.
        desc: The item description.
        source: The item source path.

    Returns:
        The colored row list.
    """
    return [
        colored(name, "cyan", attrs=["bold"]),
        colored(desc, "yellow"),
        colored(source, "light_green"),
    ]
