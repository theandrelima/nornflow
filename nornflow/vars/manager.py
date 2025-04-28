import logging
import os
from pathlib import Path
from typing import Any

import jinja2
import yaml

from nornflow.vars.constants import (
    ENV_VAR_PREFIX,
    VARS_DIR_DEFAULT,
    DEFAULTS_FILENAME,
    JINJA2_MARKERS,
)
       
from nornflow.vars.exceptions import (
    VariableDirectoryError,
    VariableLoadError,
    VariableNotFoundError,
    VariableResolutionError,
)

from nornflow.vars.context import DeviceContext
from nornflow.vars.proxy import NornirHostProxy

logger = logging.getLogger(__name__)


class VariableManager:
    """
    Manages variable loading and resolution across different sources.
    
    Variable precedence order:
    1. CLI variables (highest priority)
    2. Runtime variables
    3. Inline workflow variables
    4. Paired workflow variables
    5. Domain-specific default variables 
    6. Default variables
    7. Nornir inventory variables
    8. Environment variables (lowest priority)
    """

    def __init__(
        self,
        vars_dir: str = VARS_DIR_DEFAULT,
        cli_vars: dict[str, Any] | None = None,
        workflow_vars: dict[str, Any] | None = None,
        paired_workflow_vars: dict[str, Any] | None = None,
        workflow_path: Path | None = None,
        workflow_roots: list[str] | None = None,
    ) -> None:
        self.vars_dir = Path(vars_dir)
        self.cli_vars = cli_vars or {}
        
        self.workflow_source_vars = {
            "inline": workflow_vars or {},
            "paired": paired_workflow_vars or {}
        }
        
        self.workflow_path = workflow_path
        self.workflow_roots = [Path(root) for root in (workflow_roots or ["workflows"])]
        
        self.default_vars: dict[str, Any] = {}
        self.domain_vars: dict[str, Any] = {}
        self.env_vars = self._load_environment_variables()
        
        self.nornir_proxy = NornirHostProxy()
        
        if self.vars_dir.exists():
            if not self.vars_dir.is_dir():
                raise VariableDirectoryError(str(self.vars_dir))
            
            defaults_path = self.vars_dir / DEFAULTS_FILENAME
            self.default_vars = self._load_vars_from_file(defaults_path, "default")
            
            if workflow_path:
                self.domain_vars = self._load_domain_variables(workflow_path)
        
        DeviceContext.initialize_shared_state(
            self.cli_vars,
            self.workflow_source_vars,
            self.domain_vars,
            self.default_vars,
            self.env_vars
        )
        
        self.jinja_env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            extensions=["jinja2.ext.loopcontrols"],
        )
        
        self.device_contexts: dict[str, DeviceContext] = {}
        self.global_namespace: dict[str, Any] = {}
    
    def _load_environment_variables(self) -> dict[str, Any]:
        env_vars: dict[str, Any] = {}
        
        for key, value in os.environ.items():
            if key.startswith(ENV_VAR_PREFIX):
                var_name = key[len(ENV_VAR_PREFIX):]
                env_vars[var_name] = value
                
        return env_vars
    
    def _load_domain_variables(self, workflow_path: Path) -> dict[str, Any]:
        domain = self._extract_domain_from_path(workflow_path)
        if not domain:
            return {}
            
        domain_path = self._get_domain_vars_path(domain)
        return self._load_vars_from_file(domain_path, "domain")
        
    def _extract_domain_from_path(self, workflow_path: Path) -> str:
        try:
            workflow_path_str = str(workflow_path.resolve())
            
            for root_path in self.workflow_roots:
                root_path_str = str(root_path.resolve())
                
                if workflow_path_str.startswith(root_path_str):
                    relative_path = workflow_path.relative_to(root_path)
                    parts = relative_path.parts
                    
                    if len(parts) >= 2:
                        return parts[0]
                    else:
                        logger.info(f"Workflow {workflow_path} is directly in workflow root, no domain variables will be loaded.")
                        return ""
            
            logger.warning(f"Workflow path {workflow_path} not under any known workflow root. No domain variables will be loaded.")
            return ""
            
        except Exception as e:
            logger.warning(f"Error extracting domain from path: {e}")
            
        return ""
        
    def _get_domain_vars_path(self, domain: str) -> Path:
        return self.vars_dir / domain / DEFAULTS_FILENAME
        
    def _load_vars_from_file(self, file_path: Path, context: str) -> dict[str, Any]:
        if not file_path.exists():
            return {}
            
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Error loading {context} variables: {e}")
            raise VariableLoadError(str(file_path), e)

    def get_device_context(self, host_name: str, create_if_missing: bool = True) -> DeviceContext:
        if host_name not in self.device_contexts and create_if_missing:
            self.device_contexts[host_name] = DeviceContext(host_name=host_name)
        return self.device_contexts[host_name]

    def set_variable(self, name: str, value: Any, host_name: str, category: str = "runtime") -> None:
        """
        The category parameter exists primarily for internal use and future extensibility.
        End users should generally not need to specify a category.
        """
        category_setters = {
            "runtime": self.set_runtime_variable,
            "cli": self.set_cli_variable,
            "workflow_inline": self.set_workflow_inline_variable,
            "workflow_paired": self.set_workflow_paired_variable,
            "domain": self.set_domain_variable,
            "default": self.set_default_variable,
            "env": self.set_env_variable
        }
        
        setter = category_setters.get(category)
        if setter:
            setter(name, value, host_name)
        else:
            raise ValueError(f"Unknown variable category: {category}")

    def set_runtime_variable(self, name: str, value: Any, host_name: str) -> None:
        ctx = self.get_device_context(host_name)
        ctx.runtime_vars[name] = value
    
    def set_cli_variable(self, name: str, value: Any, host_name: str) -> None:
        ctx = self.get_device_context(host_name)
        ctx.set_cli_var(name, value)
        
    def set_workflow_inline_variable(self, name: str, value: Any, host_name: str) -> None:
        ctx = self.get_device_context(host_name)
        ctx.set_workflow_inline_var(name, value)
        
    def set_workflow_paired_variable(self, name: str, value: Any, host_name: str) -> None:
        ctx = self.get_device_context(host_name)
        ctx.set_workflow_paired_var(name, value)
        
    def set_domain_variable(self, name: str, value: Any, host_name: str) -> None:
        ctx = self.get_device_context(host_name)
        ctx.set_domain_var(name, value)
        
    def set_default_variable(self, name: str, value: Any, host_name: str) -> None:
        ctx = self.get_device_context(host_name)
        ctx.set_default_var(name, value)
        
    def set_env_variable(self, name: str, value: Any, host_name: str) -> None:
        ctx = self.get_device_context(host_name)
        ctx.set_env_var(name, value)
    
    def set_global_variable(self, name: str, value: Any) -> None:
        self.global_namespace[name] = value

    def get_variable(self, var_name: str, host_name: str) -> Any:
        device_ctx = self.get_device_context(host_name)
        flat_context = device_ctx.get_flat_context_without_env()
        
        if var_name in flat_context:
            return flat_context[var_name]
            
        if self.nornir_proxy.current_host and self.nornir_proxy.current_host.name == host_name:
            try:
                return getattr(self.nornir_proxy, var_name)
            except AttributeError:
                pass
        
        if var_name in device_ctx.env_vars:
            return device_ctx.env_vars[var_name]
            
        raise VariableNotFoundError(var_name)

    def _get_nornir_variable(self, name: str, host_name: str) -> Any:
        if self.nornir_proxy.current_host and self.nornir_proxy.current_host.name == host_name:
            try:
                return getattr(self.nornir_proxy, name)
            except AttributeError:
                return None
        return None
        
    def resolve_string(self, template_str: str, host_name: str, additional_vars: dict[str, Any] | None = None) -> str:
        try:
            template = self.jinja_env.from_string(template_str)
            device_ctx = self.get_device_context(host_name)
            
            class VariableLookupContext(dict):
                def __init__(self, var_manager, host_name, base_dict=None):
                    super().__init__()
                    self.var_manager = var_manager
                    self.host_name = host_name
                    self.device_ctx = var_manager.get_device_context(host_name)
                    if base_dict:
                        self.update(base_dict)
                
                def __getitem__(self, key):
                    try:
                        return super().__getitem__(key)
                    except KeyError:
                        value = self.var_manager._get_nornir_variable(key, self.host_name)
                        if value is not None:
                            return value
                            
                        if key in self.device_ctx.env_vars:
                            return self.device_ctx.env_vars[key]
                            
                        raise
            
            flat_context = device_ctx.get_flat_context_without_env()
            flat_context["global"] = self.global_namespace
            
            if additional_vars:
                flat_context.update(additional_vars)
                
            context = VariableLookupContext(self, host_name, flat_context)
            return template.render(**context)
            
        except jinja2.exceptions.UndefinedError as e:
            logger.error(f"Undefined variable in template: {e}")
            raise VariableResolutionError(template_str, f"Undefined variable: {e}")
        except jinja2.exceptions.TemplateError as e:
            logger.error(f"Template error: {e}")
            raise VariableResolutionError(template_str, str(e))
    
    def resolve_data(self, data: Any, host_name: str, additional_vars: dict[str, Any] | None = None) -> Any:
        if isinstance(data, str):
            if any(marker in data for marker in JINJA2_MARKERS):
                return self.resolve_string(data, host_name, additional_vars)
            return data
        elif isinstance(data, list):
            return [self.resolve_data(item, host_name, additional_vars) for item in data]
        elif isinstance(data, dict):
            return {k: self.resolve_data(v, host_name, additional_vars) for k, v in data.items()}
        else:
            return data