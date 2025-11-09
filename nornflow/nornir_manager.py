from typing import Any

from nornir import InitNornir
from nornir.core import Nornir
from nornir.core.processor import Processor

from nornflow.constants import NORNFLOW_SETTINGS_OPTIONAL
from nornflow.exceptions import CoreError, ProcessorError


class NornirManager:
    """
    NornirManager provides a centralized way to manage Nornir instances.

    This class is responsible for initializing and managing Nornir instances
    used throughout a NornFlow workflow execution. It handles configuration,
    filtering, and processor application in a consistent manner.

    Key responsibilities:
    - Creating and initializing Nornir objects from configuration files
    - Applying inventory filters (both direct attribute and function-based)
    - Managing processor application to Nornir instances
    - Properly managing connection lifecycle through context manager support

    The filtering system supports:
    - Direct attribute filtering on any host property
    - Custom filter functions with flexible parameter passing
    - Sequential application of multiple filters with AND logic
    """

    def __init__(self, nornir_settings: str, **kwargs):
        """
        Initialize the NornirManager with a Nornir configuration.

        Args:
            nornir_settings: Path to Nornir config file (YAML)
            **kwargs: Additional arguments to pass to InitNornir
        """
        # Clean up kwargs before passing to InitNornir
        self._remove_optional_nornflow_settings_from_kwargs(kwargs)

        # Store settings
        self.nornir_settings = nornir_settings
        self.kwargs = kwargs

        # Create regular Nornir instance
        self.nornir = InitNornir(
            config_file=self.nornir_settings,
            **kwargs,
        )

    def __enter__(self) -> "NornirManager":
        """
        Enter the context manager protocol.

        Returns:
            self: The NornirManager instance for use in the context block
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager protocol, ensuring connections are cleaned up.

        This method is called when exiting a 'with' block and ensures all network
        connections are properly closed, even if an exception occurred or the
        execution was interrupted (e.g., with Ctrl+C).

        Args:
            exc_type: Exception type if an exception was raised in the context block, else None
            exc_val: Exception value if an exception was raised, else None
            exc_tb: Traceback if an exception was raised, else None
        """
        self.close_connections()

    def close_connections(self) -> None:
        """
        Close all Nornir connections to prevent resources from hanging.

        This implementation silently closes connections without producing
        task output to keep the user interface clean.
        """
        if hasattr(self, "nornir"):
            # Store original processors
            original_processors = self.nornir.processors.copy()

            try:
                # Clear processors to prevent output during connection closure
                self.nornir.processors.clear()

                # Close connections
                self.nornir.close_connections(on_good=True, on_failed=True)
            finally:
                # Restore processors
                self.nornir.processors = original_processors

    def _remove_optional_nornflow_settings_from_kwargs(self, kwargs: dict[str, Any]) -> None:
        """
        Remove NornFlow-specific settings from kwargs that shouldn't be passed to InitNornir.

        Args:
            kwargs: The kwargs dictionary to modify in-place
        """
        for key in NORNFLOW_SETTINGS_OPTIONAL:
            kwargs.pop(key, None)

    def apply_filters(self, **kwargs) -> Nornir:
        """
        Apply filters to the Nornir inventory.

        This method can apply both direct attribute filters and custom filter functions.
        For custom filter functions, the 'filter_func' kwarg will contain the actual function
        while other kwargs provide the parameters.

        Args:
            **kwargs: Filter criteria to pass to Nornir's filter method
                - For attribute filters: key=value pairs for host attributes
                - For function filters: filter_func=function, param1=value1, etc.

        Returns:
            Nornir: The filtered Nornir instance

        Raises:
            ProcessorError: If no filters are provided
        """
        if not kwargs:
            raise ProcessorError("No filters informed.")

        self.nornir = self.nornir.filter(**kwargs)
        return self.nornir

    def apply_processors(self, processors: list[Processor]) -> Nornir:
        """
        Apply processors to the Nornir instance.

        This method applies the provided processors to the Nornir instance,
        updates the internal instance, and returns it.

        Args:
            processors: List of processor objects to apply

        Returns:
            Nornir: Nornir instance with processors applied

        Raises:
            ProcessorError: If no processors are provided
        """
        if not processors:
            raise ProcessorError("No processors informed.")

        self.nornir = self.nornir.with_processors(processors)
        return self.nornir

    def apply_runner(self, runner: "RunnerPlugin") -> Nornir:
        """
        Apply a runner to the Nornir instance.

        This method sets the specified runner on the Nornir instance,
        updates the internal instance, and returns it.

        Args:
            runner: The runner object to apply

        Returns:
            Nornir: Nornir instance with the runner applied
        """
        self.nornir = self.nornir.with_runner(runner)
        return self.nornir

    def set_dry_run(self, value: bool = False) -> None:
        """
        Sets the dry_run flag in the Nornir instance's global data state.
        This flag is used by Nornir's task execution system to determine whether
        tasks should be executed in dry-run mode (simulation) or normal mode.

        Args:
            value (bool): True to enable dry-run mode, False to disable it.
                Defaults to False.

        Example:
            manager.set_dry_run(True)   # Enable dry-run mode
            manager.set_dry_run(False)  # Disable dry-run mode (default)
        """
        if not isinstance(value, bool):
            raise CoreError(
                f"dry_run value must be a boolean, got {type(value).__name__}: {value}",
                component="NornirManager",
            )

        self.nornir.data.dry_run = value

    def get_processor_by_type(self, processor_type: type) -> Any:
        """
        Get a processor instance by its type.

        Args:
            processor_type: The type of processor to retrieve

        Returns:
            The processor instance of the requested type

        Raises:
            ProcessorError: If no processor of the requested type is found
        """
        for processor in self.nornir.processors:
            if isinstance(processor, processor_type):
                return processor

        raise ProcessorError(f"No processor of type {processor_type.__name__} found in Nornir instance")
