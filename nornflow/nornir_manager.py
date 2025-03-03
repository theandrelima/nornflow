from typing import Any

from nornir import InitNornir
from nornir.core import Nornir
from nornir.core.processor import Processor

from nornflow.constants import NONRFLOW_SETTINGS_OPTIONAL
from nornflow.exceptions import NornirManagerProcessorsError


class NornirManager:
    """
    NornirManager provides a centralized way to manage Nornir instances.

    This class is responsible for initializing and managing Nornir instances
    used throughout a NornFlow workflow execution. It handles configuration,
    filtering, and processor application in a consistent manner.

    The NornirManager maintains a primary Nornir instance and optionally
    a specialized instance for local tasks, providing appropriate access
    to either based on task requirements.
    """

    def __init__(self, nornir_settings: str, dry_run: bool, **kwargs):
        """
        Initialize the NornirManager with a Nornir configuration.

        Args:
            nornir_settings: Path to Nornir config file (YAML)
            dry_run: Whether to run Nornir tasks in dry-run mode
            **kwargs: Additional arguments to pass to InitNornir
        """
        # Clean up kwargs before passing to InitNornir
        self._remove_optional_nornflow_settings_from_kwargs(kwargs)

        # Store settings
        self.nornir_settings = nornir_settings
        self.dry_run = dry_run
        self.kwargs = kwargs

        # Create regular Nornir instance
        self.nornir = InitNornir(
            config_file=self.nornir_settings,
            dry_run=self.dry_run,
            **kwargs,
        )

        # Initialize _local_tasks_nornir to None (lazy initialization)
        self._local_tasks_nornir = None

    def _remove_optional_nornflow_settings_from_kwargs(self, kwargs: dict[str, Any]) -> None:
        """
        Remove NornFlow-specific settings from kwargs that shouldn't be passed to InitNornir.

        Args:
            kwargs: The kwargs dictionary to modify in-place
        """
        for key in NONRFLOW_SETTINGS_OPTIONAL:
            if key in kwargs:
                del kwargs[key]

    def apply_filters(self, **kwargs) -> Nornir:
        """
        Apply filters to the Nornir inventory.

        This method filters the inventory based on the provided criteria,
        updates the internal Nornir instance, and returns it.

        Args:
            **kwargs: Filter criteria to pass to Nornir's filter method

        Returns:
            Nornir: The filtered Nornir instance

        Raises:
            NornirManagerProcessorsError: If no filters are provided
        """
        if not kwargs:
            raise NornirManagerProcessorsError("No filters informed.")

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
            NornirManagerProcessorsError: If no processors are provided
        """
        if not processors:
            raise NornirManagerProcessorsError("No processors informed.")

        self.nornir = self.nornir.with_processors(processors)
        return self.nornir
