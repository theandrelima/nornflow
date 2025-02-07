import click
from importlib import import_module
import pkgutil
import nornflow.cli

@click.group()
def nornflow_cli():
    """NornFlow CLI"""
    pass

# Dynamically load subcommands from the cli package
def load_subcommands():
    package = nornflow.cli
    ignore_modules = ['main', 'constants']
    for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if module_name.split('.')[-1] not in ignore_modules:
            module = import_module(module_name)
            command = getattr(module, module_name.split('.')[-1])
            nornflow_cli.add_command(command)

load_subcommands()

if __name__ == "__main__":
    nornflow_cli()