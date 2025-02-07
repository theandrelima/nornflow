import pkgutil
from importlib import import_module
from types import ModuleType

import click

import nornflow.cli


@click.group()
def nornflow_cli() -> None:
    """
    NornFlow CLI group.

    This is the main entry point for the NornFlow command-line interface.
    """


def load_subcommands() -> None:
    """
    Dynamically load subcommands from the cli package.

    This function scans the cli package for modules and dynamically imports them as subcommands,
    ignoring specified modules.
    """
    package: ModuleType = nornflow.cli
    ignore_modules: list[str] = ["main", "constants"]
    for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if module_name.split(".")[-1] not in ignore_modules:
            module = import_module(module_name)
            command = getattr(module, module_name.split(".")[-1])
            nornflow_cli.add_command(command)


load_subcommands()

if __name__ == "__main__":
    nornflow_cli()
