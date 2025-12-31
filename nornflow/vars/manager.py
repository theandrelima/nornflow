import logging
import os
from pathlib import Path
from typing import Any

import jinja2.exceptions
import yaml

from nornflow.vars.constants import (
    DEFAULTS_FILENAME,
    ENV_VAR_PREFIX,
    JINJA2_MARKERS,
)
from nornflow.vars.context import NornFlowDeviceContext
from nornflow.vars.exceptions import TemplateError, VariableError
from nornflow.vars.jinja2_utils import Jinja2EnvironmentManager
from nornflow.vars.proxy import NornirHostProxy

logger = logging.getLogger(__name__)

# Constants for magic values
MAX_LOG_VALUE_LENGTH = 80


class HostNamespace:
    """
    Provides read-only access to the Nornir host inventory data via the 'host.' prefix
    within Jinja2 templates.

    This class acts as a proxy to the NornirHostProxy, ensuring that attribute
    access (e.g., {{ host.name }}) is correctly routed to the current host's data.
    """

    def __init__(self, vars_manager: "NornFlowVariablesManager", host_name: str):
        """
        Initializes the HostNamespace.

        Args:
            vars_manager: The NornFlowVariablesManager instance.
            host_name: The name of the host for which this namespace is being created.
        """
        self._vars_manager = vars_manager
        self._host_name = host_name
        self._proxy = vars_manager.nornir_host_proxy

    def __getattr__(self, name: str) -> Any:
        """
        Retrieves an attribute (variable or data key) from the Nornir host's inventory.

        This method is called when an attribute is accessed on a HostNamespace
        object (e.g., `host.some_attribute` in a Jinja2 template).

        Args:
            name: The name of the attribute to retrieve.

        Returns:
            The value of the attribute from the host's inventory.

        Raises:
            VariableError: If the attribute is not found in the host's inventory.
        """
        try:
            # Ensure the NornirHostProxy is targeting the correct host for this access
            self._proxy.current_host_name = self._host_name
            return getattr(self._proxy, name)
        except AttributeError as err:
            # Raise a more NornFlow-specific error for clarity in logs/exceptions
            raise VariableError(
                f"Host attribute or data key '{name}' not found for host '{self._host_name}'."
            ) from err


class VariableLookupContext(dict):
    """
    Custom dictionary used as the context for Jinja2 template rendering in NornFlow.

    This class provides access to:
    - NornFlow Default Namespace variables: These are the variables loaded from various
      sources (CLI, runtime, inline, domain, default, environment) and are directly
      accessible in templates (e.g., `{{ my_variable }}`).
    - 'host.' namespace: Provides read-only access to Nornir inventory data for the
      current host, facilitated by the `HostNamespace` class (e.g., `{{ host.name }}`).
    """

    def __init__(
        self, vars_manager: "NornFlowVariablesManager", host_name: str, base_nornflow_vars: dict[str, Any]
    ):
        """
        Initializes the VariableLookupContext.

        Args:
            vars_manager: The NornFlowVariablesManager instance.
            host_name: The name of the host for which the context is being created.
            base_nornflow_vars: A dictionary containing the flattened NornFlow Default
                                Namespace variables for the current device.
        """
        super().__init__(base_nornflow_vars)  # Initialize with flattened NornFlow default vars
        self._vars_manager = vars_manager
        self._host_name = host_name

        # Make the 'host.' namespace available in the Jinja2 context
        # e.g., {{ host.name }}
        self["host"] = HostNamespace(vars_manager, host_name)


class NornFlowVariablesManager:
    """
    Manages the loading, accessing, and resolution of variables from multiple sources,
    strictly adhering to NornFlow's documented precedence order. It supports
    device-specific contexts (`NornFlowDeviceContext`) to ensure variable isolation
    during workflow execution.

    NornFlow Default Namespace Variable Precedence (Highest to Lowest):
    1. Runtime Variables (dynamically set by the 'set' task or 'set_to' keyword)
    2. CLI Variables
    3. Inline Workflow Variables (defined in the `workflow.vars` section)
    4. Domain-specific Default Variables (from `{vars_dir}/{domain}/defaults.yaml`)
    5. Default Variables (from `{vars_dir}/defaults.yaml`)
    6. Environment Variables (prefixed with `NORNFLOW_VAR_`)

    The 'host.' namespace provides read-only access to Nornir inventory data
    (e.g., `{{ host.hostname }}`).
    """

    def __init__(
        self,
        vars_dir: str,
        cli_vars: dict[str, Any] | None = None,
        inline_workflow_vars: dict[str, Any] | None = None,
        workflow_path: Path | None = None,
        workflow_roots: list[str] | None = None,
    ) -> None:
        """
        Initializes the NornFlowVariablesManager.

        This involves setting up paths, loading initial variable layers (environment,
        default, domain-specific), and preparing the shared state for device contexts.

        Args:
            vars_dir: The root directory where NornFlow variable files (`defaults.yaml`,
                      domain-specific `defaults.yaml`) are stored.
            cli_vars: A dictionary of variables provided via command-line arguments.
            inline_workflow_vars: A dictionary of variables defined directly within the
                                  workflow's `vars` section.
            workflow_path: The `pathlib.Path` object representing the currently executing
                           workflow file. Used to determine the domain for domain-specific
                           variables.
            workflow_roots: A list of root directory paths where workflows are stored.
                            Used in conjunction with `workflow_path` to determine the domain.

        Raises:
            VariableError: If `vars_dir` exists but is not a directory.
        """
        self.vars_dir = Path(vars_dir)
        self._cli_vars = cli_vars or {}
        self._inline_workflow_vars = inline_workflow_vars or {}

        self.workflow_path = workflow_path
        self.workflow_roots = [Path(root) for root in (workflow_roots or [])]

        self._default_vars: dict[str, Any] = {}
        self._domain_vars: dict[str, Any] = {}  # Loaded based on workflow_path
        self._env_vars = self._load_environment_variables()

        self.nornir_host_proxy = NornirHostProxy()

        if self.vars_dir.exists():
            if not self.vars_dir.is_dir():
                raise VariableError(f"Specified vars_dir '{self.vars_dir}' exists but is not a directory.")

            defaults_path = self.vars_dir / DEFAULTS_FILENAME
            self._default_vars = self._load_vars_from_file(defaults_path, "Default Variables")

            if workflow_path:  # Only attempt to load domain vars if a workflow path is provided
                self._domain_vars = self._load_domain_variables(workflow_path)

        NornFlowDeviceContext.initialize_shared_state(
            cli_vars=self._cli_vars,
            inline_workflow_vars=self._inline_workflow_vars,
            domain_vars=self._domain_vars,
            default_vars=self._default_vars,
            env_vars=self._env_vars,
        )

        self._jinja2_manager = Jinja2EnvironmentManager()
        self._device_contexts: dict[str, NornFlowDeviceContext] = {}

    def _load_environment_variables(self) -> dict[str, Any]:
        """
        Loads environment variables that are prefixed with `NORNFLOW_VAR_`.
        The prefix is stripped from the variable names.

        Returns:
            A dictionary of NornFlow-specific environment variables.
        """
        env_vars: dict[str, Any] = {}
        for key, value in os.environ.items():
            if key.startswith(ENV_VAR_PREFIX):
                var_name = key[len(ENV_VAR_PREFIX) :]
                if var_name:
                    env_vars[var_name] = value
        logger.debug(f"Loaded environment variables with prefix '{ENV_VAR_PREFIX}': {list(env_vars.keys())}")
        return env_vars

    def _load_domain_variables(self, workflow_path: Path) -> dict[str, Any]:
        """
        Loads domain-specific default variables from `{vars_dir}/{domain}/defaults.yaml`.
        The domain is determined based on the `workflow_path` relative to `workflow_roots`.

        Args:
            workflow_path: The path to the currently executing workflow file.

        Returns:
            A dictionary of domain-specific variables, or an empty dictionary if
            no domain is found or the domain's variable file doesn't exist.
        """
        domain = self._extract_domain_from_path(workflow_path)
        if not domain:
            logger.debug(
                f"No domain determined for workflow '{workflow_path}'. Skipping domain variable loading."
            )
            return {}

        domain_vars_path = self.vars_dir / domain / DEFAULTS_FILENAME
        logger.debug(f"Attempting to load domain variables for domain '{domain}' from '{domain_vars_path}'.")
        return self._load_vars_from_file(domain_vars_path, f"Domain Variables for '{domain}'")

    def _extract_domain_from_path(self, workflow_path: Path) -> str:
        """
        Extracts the domain name from a workflow's path.
        The domain is considered the first-level subdirectory under one of the
        configured `workflow_roots` that contains the `workflow_path`.

        Args:
            workflow_path: The `pathlib.Path` to the workflow file.

        Returns:
            The extracted domain name as a string, or an empty string if a domain
            cannot be determined.
        """
        try:
            abs_workflow_path = workflow_path.resolve()
            for root_dir_path_str in self.workflow_roots:
                abs_root_path = Path(root_dir_path_str).resolve()

                if abs_workflow_path.is_relative_to(abs_root_path):
                    relative_path = abs_workflow_path.relative_to(abs_root_path)
                    if relative_path.parts and len(relative_path.parts) > 1:
                        domain_name = relative_path.parts[0]
                        logger.debug(
                            f"Extracted domain '{domain_name}' for workflow '{workflow_path}' "
                            f"based on root '{abs_root_path}'."
                        )
                        return domain_name
                    logger.debug(
                        f"Workflow '{workflow_path}' is directly in a workflow root '{abs_root_path}'. "
                        "No domain identified from path structure."
                    )
                    return ""

            logger.debug(
                f"Workflow path '{workflow_path}' not found under any configured workflow roots: "
                f"{self.workflow_roots}. Cannot determine domain from path."
            )
            return ""
        except (OSError, ValueError) as e:
            logger.warning(f"Error extracting domain from path '{workflow_path}': {e}", exc_info=True)
            return ""

    def _load_vars_from_file(self, file_path: Path, context_description: str) -> dict[str, Any]:
        """
        Loads variables from a specified YAML file.

        Args:
            file_path: The `pathlib.Path` to the YAML file.
            context_description: A string describing the context of the variables being loaded
                                 (e.g., "Default Variables", "Domain Variables for 'xyz'").

        Returns:
            A dictionary of variables loaded from the file. Returns an empty dictionary
            if the file does not exist, is not a file, or if the loaded content is not
            a dictionary.

        Raises:
            VariableError: If there's a YAML parsing error or an unexpected
                           error during file loading.
        """
        if not file_path.exists():
            logger.debug(f"{context_description} file not found at '{file_path}'. Skipping.")
            return {}
        if not file_path.is_file():
            logger.warning(
                f"Expected {context_description} file at '{file_path}' is not a regular file. Skipping."
            )
            return {}

        try:
            with file_path.open(encoding="utf-8") as f:
                loaded_vars = yaml.safe_load(f)
                if loaded_vars is None:
                    logger.debug(
                        f"{context_description} file '{file_path}' is empty or contains only null values."
                    )
                    return {}
                if not isinstance(loaded_vars, dict):
                    raise VariableError(
                        f"Expected a dictionary from {context_description} file at '{file_path}', "
                        f"but got {type(loaded_vars).__name__}."
                    )
                logger.debug(f"Successfully loaded {context_description} from '{file_path}'.")
                return loaded_vars
        except yaml.YAMLError as e:
            logger.exception(f"YAML parsing error in {context_description} file '{file_path}'")
            raise VariableError(f"YAML parsing error in {context_description} file '{file_path}': {e}") from e
        except Exception as e:
            logger.exception(f"Unexpected error loading {context_description} file '{file_path}'")
            raise VariableError(
                f"Unexpected error loading {context_description} file '{file_path}': {e}"
            ) from e

    def get_device_context(self, host_name: str) -> NornFlowDeviceContext:
        """
        Retrieves or creates a `NornFlowDeviceContext` for the specified host.

        Args:
            host_name: The name of the host for which to get the device context.

        Returns:
            The `NornFlowDeviceContext` instance for the given host.
        """
        if host_name not in self._device_contexts:
            logger.debug(f"Creating new NornFlowDeviceContext for host '{host_name}'.")
            self._device_contexts[host_name] = NornFlowDeviceContext(host_name=host_name)
        return self._device_contexts[host_name]

    def set_runtime_variable(self, name: str, value: Any, host_name: str) -> None:
        """
        Sets a runtime variable for a specific host.

        Runtime variables are created or modified during workflow execution.

        Args:
            name: The name of the runtime variable to set.
            value: The value to assign to the variable.
            host_name: The name of the host for which this variable is being set.
        """
        if not host_name:
            logger.error("Cannot set runtime variable: host_name is missing.")
            return

        ctx = self.get_device_context(host_name)
        ctx.runtime_vars[name] = value
        value_str = str(value)
        logger.debug(
            f"Runtime variable '{name}' set for host '{host_name}'. Value: "
            f"{value_str[:MAX_LOG_VALUE_LENGTH]}"
            f"{'...' if len(value_str) > MAX_LOG_VALUE_LENGTH else ''}"
        )

    def get_nornflow_variable(self, var_name: str, host_name: str) -> Any:
        """
        Retrieves a NornFlow Default Namespace variable for a specific host,
        respecting the full 6-level precedence order.

        This method queries the NornFlow Default Namespace.

        Args:
            var_name: The name of the NornFlow variable to retrieve.
            host_name: The name of the host for which to retrieve the variable.

        Returns:
            The value of the variable.

        Raises:
            VariableError: If the variable is not found or host_name is missing.
        """
        if not host_name:
            raise VariableError(f"Host name not provided for NornFlow variable lookup: {var_name}")

        device_ctx = self.get_device_context(host_name)
        flat_context = device_ctx.get_flat_context()

        if var_name in flat_context:
            return flat_context[var_name]

        raise VariableError(
            f"NornFlow variable '{var_name}' not found in Default Namespace for host '{host_name}'."
        )

    def resolve_string(
        self, template_str: str, host_name: str, additional_vars: dict[str, Any] | None = None
    ) -> str:
        """
        Resolves a Jinja2 template string using variables for a specific host.

        Context provides access to Default Namespace and 'host.' namespace.

        Args:
            template_str: The Jinja2 template string to resolve.
            host_name: The name of the host for which to resolve the template.
            additional_vars: Optional dictionary of variables to add to the Jinja2
                             context with the highest precedence for this resolution.

        Returns:
            The resolved string. Returns input if not a string or no Jinja2 markers.

        Raises:
            TemplateError: If template resolution fails or host_name is missing.
        """
        if not isinstance(template_str, str):
            return template_str

        if not any(marker in template_str for marker in JINJA2_MARKERS):
            return template_str

        if not host_name:
            raise TemplateError(f"Host name not provided for template resolution: {template_str}")

        try:
            device_ctx = self.get_device_context(host_name)
            nornflow_default_vars = device_ctx.get_flat_context()

            resolution_context_dict = nornflow_default_vars.copy()
            if additional_vars:
                resolution_context_dict.update(additional_vars)

            context_for_jinja = VariableLookupContext(self, host_name, resolution_context_dict)

            template = self._jinja2_manager.env.from_string(template_str)
            return template.render(context_for_jinja)

        except jinja2.exceptions.UndefinedError as e:
            logger.exception(f"Jinja2 UndefinedError for host '{host_name}' in template '{template_str}'")
            raise TemplateError(f"Undefined variable in template '{template_str}': {e}") from e
        except VariableError as e:
            logger.exception(f"NornFlow VariableError for host '{host_name}' in template '{template_str}'")
            raise TemplateError(f"Variable error in template '{template_str}': {e}") from e
        except Exception as e:
            logger.exception(
                f"Jinja2 TemplateError or unexpected issue for host '{host_name}' "
                f"in template '{template_str}'"
            )
            raise TemplateError(f"Template rendering error in '{template_str}': {e}") from e

    def resolve_data(self, data: Any, host_name: str, additional_vars: dict[str, Any] | None = None) -> Any:
        """
        Recursively resolve Jinja2 templates in nested data structures.

        Args:
            data: The data structure to resolve (dict, list, string, etc.).
            host_name: The name of the host for which to resolve variables.
            additional_vars: Additional variables to include in the context.

        Returns:
            The data structure with all templates resolved.
        """
        if isinstance(data, str):
            # Check if the string contains Jinja2 markers
            if any(marker in data for marker in JINJA2_MARKERS):
                return self.resolve_string(data, host_name, additional_vars)
            return data
        if isinstance(data, dict):
            return {k: self.resolve_data(v, host_name, additional_vars) for k, v in data.items()}
        if isinstance(data, (list, tuple)):
            # Convert both lists and tuples to lists after resolving items
            # This ensures YAML-defined lists remain lists, even if converted to tuples for hashability
            return [self.resolve_data(item, host_name, additional_vars) for item in data]
        # Return other types as-is
        return data
