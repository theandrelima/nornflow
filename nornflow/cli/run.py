import click

from nornflow.nornflow import NornFlow

@click.command()
@click.argument("target", type=str)
@click.option("--dry-run", "-d", is_flag=True, default=None, help="Run in dry-run mode")
@click.option("--hosts", "-h", type=str, help="Specify the hosts to run the task on")
@click.option("--groups", "-g", type=str, help="Specify the groups to run the task on")
def run(target: str, dry_run: bool, hosts: str, groups: str) -> None:
    """
    Runs either a cataloged task or workflow - for workflows, the '.yaml' must be included.

    Args:
        target (str): The name of the task to run.
        dry_run (bool): Flag to run the task in dry-run mode.
        hosts (str): The hosts to run the task on.
        groups (str): The groups to run the task on.
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
    click.echo(
        click.style(
            f"Running task: {target} (dry-run: {dry_run}, hosts: {hosts}, groups: {groups})", fg="green"
        )
    )
    nornflow.run()
