import click
from nornflow.nornflow import NornFlow

@click.command(context_settings=dict(max_content_width=120))
@click.argument('target', type=str)
@click.option('--dry-run', '-d', is_flag=True, default=None, help="Run in dry-run mode")
@click.option('--hosts', '-h', type=str, help="Specify the hosts to run the task on")
def run(target: str, dry_run: bool, hosts: str) -> None:
    """
    Runs either a cataloged task or workflow - for workflows, the '.yaml' must be included.
    """
    nornflow_kwargs = {'tasks_to_run': [target]}
    
    if dry_run is not None:
        nornflow_kwargs['dry_run'] = dry_run

    if hosts:
        nornflow_kwargs['hosts'] = hosts

    nornflow = NornFlow(**nornflow_kwargs)
    click.echo(click.style(f"Running task: {target} (dry-run: {dry_run}, hosts: {hosts})", fg="green"))
    nornflow.run()

