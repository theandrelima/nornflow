"""
NornFlow CLI exception hierarchy.

This module defines CLI-specific exceptions for the NornFlow application.
"""

import traceback
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from nornflow.exceptions import NornFlowAppError

console = Console(stderr=True)


class NornFlowCLIError(NornFlowAppError):
    """
    Base exception class for CLI-related errors.
    
    These relate to command-line interface operations.
    """

    def __init__(
        self,
        message: str,
        hint: Optional[str] = None,
        code: int = 1,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.code = code
        self.original_exception = original_exception

    def format_rich(self) -> str:
        """Format the error message for rich display."""
        error_message = f"[red bold]Error:[/] {self.message}"

        if self.hint:
            error_message += f"\n[yellow]Hint:[/] {self.hint}"

        if self.original_exception:
            error_message += "\n\n[dim]Original error:[/]"
            error_message += (
                f"\n[dim]{self.original_exception.__class__.__name__}: {self.original_exception!s}[/]"
            )

            # Get traceback if available
            tb = "".join(traceback.format_tb(self.original_exception.__traceback__))
            if tb:
                error_message += f"\n[dim]Traceback:[/]\n[dim]{tb}[/]"

        return error_message

    def show(self) -> None:
        """Display the error message using Rich formatting."""
        error_message = self.format_rich()
        console.print(Panel(error_message, title="[red]NornFlow CLI Error[/]", border_style="red"))


class CLIShowError(NornFlowCLIError):
    """Raised when there are errors displaying information via CLI."""


class CLIRunError(NornFlowCLIError):
    """Raised when there are errors running commands via CLI."""