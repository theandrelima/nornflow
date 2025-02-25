import os

import typer

from nornflow.cli import init, run, show

app = typer.Typer(
    help="NornFlow CLI - A workflow orchestration tool for Network Automation built around Nornir.",
    add_completion=False,
)


def settings_callback(ctx: typer.Context, settings: str | None = None) -> None:
    """
    Callback function to handle the global --settings option.

    This function sets the settings file path in the Typer context object. If the environment variable
    'NORNFLOW_CONFIG_FILE' is set, it takes precedence over the --settings option. The function also
    provides feedback to the user about which settings file will be used.

    Args:
        ctx (typer.Context): The Typer context object.
        settings (Optional[str]): The path to the custom settings file provided via the --settings option.
    """
    ctx.obj = {"settings": ""}

    # settings will only be set if 'NORNFLOW_CONFIG_FILE' is not set
    nornflow_config_file = os.getenv("NORNFLOW_CONFIG_FILE")

    if nornflow_config_file:
        typer.secho(
            "\nBecause env var 'NORNFLOW_CONFIG_FILE' is set, NornFlow will try to use it as a path "
            "for its settings file.",
            fg=typer.colors.MAGENTA,
            bold=True,
        )
        typer.secho(
            "Unset it to make use of '--settings' option, or to fallback to a default 'nornflow.yaml' file.",
            fg=typer.colors.MAGENTA,
            bold=True,
        )
        typer.secho(
            f"NORNFLOW_CONFIG_FILE='{nornflow_config_file}'\n", fg=typer.colors.BRIGHT_YELLOW, bold=True
        )

        return

    if settings:
        ctx.obj = {"settings": settings}


# Add the global option to the main Typer app
@app.callback()
def main(
    ctx: typer.Context,
    settings: str | None = typer.Option(
        None, "--settings", "-s", help="Specify a path to a custom settings file."
    ),
) -> None:
    settings_callback(ctx, settings)


# Register subcommands
app.command()(init.init)
app.command()(run.run)
app.command()(show.show)

if __name__ == "__main__":
    app()
