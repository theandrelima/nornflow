"""Improving exceptions here will be a continuous effort."""

import traceback

from rich.console import Console
from rich.panel import Panel

console = Console(stderr=True)


class NornFlowCLIError(Exception):
    """Base exception for NornFlow CLI errors."""

    def __init__(
        self,
        message: str,
        hint: str | None = None,
        code: int | None = 1,
        original_exception: Exception | None = None,
    ) -> None:
        self.message = message
        self.hint = hint
        self.code = code
        self.original_exception = original_exception
        super().__init__(message)

    def show(self) -> None:
        """Display the error message using Rich formatting."""
        error_message = f"[red bold]Error:[/] {self.message}"

        if self.hint:
            error_message += f"\n[yellow]Hint:[/] {self.hint}"

        if self.original_exception:
            error_message += "\n\n[dim]Original error:[/]"
            error_message += (
                f"\n[dim]{self.original_exception.__class__.__name__}: {self.original_exception!s}[/]"
            )

            # Get the traceback, excluding the current exception handling
            tb = "".join(traceback.format_tb(self.original_exception.__traceback__))
            if tb:
                error_message += f"\n[dim]Traceback:[/]\n[dim]{tb}[/]"

        console.print(Panel(error_message, title="[red]NornFlow CLI Error[/]", border_style="red"))


class NornFlowCLIShowError(NornFlowCLIError):
    """Raised when there are errors displaying information."""
