import typer

from nornflow.cli import init, run, show

app = typer.Typer(
    help="NornFlow CLI - A tiny CLI wrapper around Nornir",
    add_completion=False,
)

app.command()(init.init)
app.command()(run.run)
app.command()(show.show)

if __name__ == "__main__":
    app()
