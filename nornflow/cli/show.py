import click

@click.command()
def show():
    """Another command"""
    click.echo("This is the show command")