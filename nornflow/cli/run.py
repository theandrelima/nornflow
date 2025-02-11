import typer

from nornflow.nornflow import NornFlow

app = typer.Typer(help="Run NornFlow tasks and workflows")


@app.command()
def run(
    target: str = typer.Argument(..., help="The name of the task or workflow to run"),
    dry_run: bool = typer.Option(None, "--dry-run", "-d", help="Run in dry-run mode"),
    hosts: str = typer.Option(None, "--hosts", "-h", help="Specify the hosts to run the task on"),
    groups: str = typer.Option(None, "--groups", "-g", help="Specify the groups to run the task on"),
) -> None:
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

    nornflow = NornFlow(**nornflow_kwargs)
    typer.secho(
        f"Running task: {target} (dry-run: {dry_run}, hosts: {hosts}, groups: {groups})",
        fg=typer.colors.GREEN,
    )
    nornflow.run()


if __name__ == "__main__":
    app()
