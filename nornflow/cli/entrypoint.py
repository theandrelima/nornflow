import typer

from nornflow.cli import init, run, show

app = typer.Typer(
    help="NornFlow is a workflow orchestration tool for Network Automation built around Nornir.",
    add_completion=False,
)


def settings_callback(ctx: typer.Context, settings: str | None = None) -> None:
    """
    Priority order (highest to lowest):
    1. --settings CLI argument (caller's explicit intent)
    2. NORNFLOW_SETTINGS environment variable (handled by NornFlowSettings.load)
    3. Default nornflow.yaml (handled by NornFlowSettings.load)
    """
    # Just pass through whatever CLI provided (or empty string)
    ctx.obj = {"settings": settings if settings else ""}


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
