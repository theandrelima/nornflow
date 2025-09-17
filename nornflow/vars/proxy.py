import logging
from typing import Any

from nornir.core import Nornir
from nornir.core.inventory import Host

from nornflow.vars.exceptions import VariableError

logger = logging.getLogger(__name__)


class NornirHostProxy:
    """
    Read-only proxy object for accessing Nornir inventory variables for the current host
    via the `host.` namespace in NornFlow templates.

    This class implements a proxy pattern to provide direct access to host attributes
    (like `name`, `platform`) and keys within the `host.data` dictionary. Nornir's
    `host.data` dictionary is the result of merging variables from host-specific
    definitions, group inheritance, and inventory defaults.

    The `NornFlowVariableProcessor` is responsible for setting the `current_host_name`
    and `nornir` instance on this proxy before it's used for variable resolution
    within a task context. This proxy itself does not modify Nornir inventory.
    """

    def __init__(self) -> None:
        """Initialize the proxy with no current host or Nornir instance."""
        self._current_host: Host | None = None
        self._nornir: Nornir | None = None

    @property
    def current_host(self) -> Host | None:
        """Get the current Nornir Host object being proxied."""
        return self._current_host

    @current_host.setter
    def current_host(self, host: Host | None) -> None:
        """Set the current Nornir Host object."""
        self._current_host = host

    @property
    def nornir(self) -> Nornir | None:
        """Get the Nornir instance associated with this proxy."""
        return self._nornir

    @nornir.setter
    def nornir(self, nornir_instance: Nornir | None) -> None:
        """Set the Nornir instance."""
        self._nornir = nornir_instance

    @property
    def current_host_name(self) -> str | None:
        """Get the name of the current host, if one is set."""
        return self._current_host.name if self._current_host else None

    @current_host_name.setter
    def current_host_name(self, host_name: str | None) -> None:
        """
        Set the current host by its name, looking it up in the Nornir inventory.
        If `host_name` is None or empty, or if the Nornir instance is not set,
        or if the host is not found, the current host context will be cleared.
        """
        if not host_name:
            self.current_host = None
            logger.debug("NornirHostProxy: Cleared current_host due to None/empty host_name.")
            return

        if not self._nornir:
            logger.warning(
                "NornirHostProxy: Nornir instance not set. Cannot look up host '%s'. Clearing current_host.",
                host_name,
            )
            self.current_host = None
            return

        if host_name in self._nornir.inventory.hosts:
            self.current_host = self._nornir.inventory.hosts[host_name]
            logger.debug("NornirHostProxy: Set current_host to '%s'.", host_name)
        else:
            logger.warning(
                "NornirHostProxy: Host '%s' not found in Nornir inventory. Clearing current_host.", host_name
            )
            self.current_host = None

    def __getattr__(self, name: str) -> Any:
        """
        Dynamically retrieves an attribute or data key from the current Nornir host.

        This method is called for attribute access like `proxy.some_attribute` or
        `{{ host.some_attribute }}` in Jinja2 templates. It follows NornFlow's
        documented precedence for the `host.` namespace:
        1. Direct attributes of the Nornir `Host` object.
        2. Keys within the `Host.data` dictionary.

        Args:
            name: The name of the attribute or data key to retrieve.

        Returns:
            The value of the attribute/key from the host's inventory.

        Raises:
            VariableError: If no Nornir instance or current host is set.
            VariableError: If the attribute/key is not found.
        """
        if not self._nornir:
            raise VariableError("NornirHostProxy: Nornir instance not set. Cannot resolve host variables.")
        if not self._current_host:
            raise VariableError(
                "NornirHostProxy: No active host context. "
                "Ensure NornFlowVariableProcessor correctly sets current_host_name."
            )

        return self._get_host_value(name)

    def _get_host_value(self, name: str) -> Any:
        """
        Retrieves a value from the current host, following NornFlow's documented
        precedence for the `host.` namespace:
        1. Direct host attributes (e.g., name, platform, data).
        2. Keys within the `host.data` dictionary (which is already fully resolved
           by Nornir, including group and default data).

        Args:
            name: The name of the attribute or data key.

        Returns:
            The value if found.

        Raises:
            VariableError: If `self._current_host` is not set
                (safeguard, shouldbe caught by `__getattr__`).
            VariableError: If the name is not found.
        """
        if not self._current_host:
            # This check is a safeguard; __getattr__ should prevent calls if _current_host is None.
            raise VariableError("NornirHostProxy: _get_host_value called with no current host.")

        # Try to retrieve 'name' using Host.get(), which covers direct attributes, data, and inheritance.
        value = self._current_host.get(name)
        if value is None:
            raise VariableError(f"Attribute or key '{name}' not found in host '{self._current_host.name}'.")
        return value
