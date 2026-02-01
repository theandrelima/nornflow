import os
from pathlib import Path
from typing import Any

from pydantic_serdes.utils import load_file_to_dict

from nornflow.exceptions import BlueprintError
from nornflow.j2 import Jinja2Service
from nornflow.logger import logger
from nornflow.vars.constants import DEFAULTS_FILENAME


class BlueprintResolver:
    """Handles variable context building and template resolution for blueprints.

    This class manages the assembly-time variable context (subset of variables
    available during workflow loading) and provides Jinja2 template resolution
    for blueprint references and conditions.
    """

    def __init__(self):
        """Initialize resolver with Jinja2Service."""
        self.jinja2 = Jinja2Service()

    def build_context(
        self,
        vars_dir: Path,
        workflow_path: Path | None,
        workflow_roots: list[str],
        inline_workflow_vars: dict[str, Any] | None = None,
        cli_vars: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build variable context for blueprint resolution.

        Assembly-time variable precedence (lowest to highest):
        1. Environment Variables (NORNFLOW_VAR_*)
        2. Default Variables (vars_dir/defaults.yaml)
        3. Domain-specific Default Variables (vars_dir/{domain}/defaults.yaml)
        4. Workflow Variables (workflow.vars section)
        5. CLI Variables (--vars option)

        Args:
            vars_dir: Base directory containing variable files.
            workflow_path: Path to the workflow file (None for in-memory).
            workflow_roots: List of workflow root directories.
            inline_workflow_vars: Variables from workflow.vars section.
            cli_vars: CLI variables with highest precedence.

        Returns:
            Dictionary containing merged variables with proper precedence.
        """
        logger.debug("Building blueprint variable context")
        context = {}

        env_vars = self._load_env_vars()
        if env_vars:
            logger.debug(f"Loaded {len(env_vars)} environment variables")
        context.update(env_vars)

        vars_dir_path = Path(vars_dir)
        defaults_path = vars_dir_path / DEFAULTS_FILENAME
        if defaults_path.exists():
            try:
                defaults = load_file_to_dict(defaults_path)
                logger.debug(f"Loaded default variables from '{defaults_path}'")
                context.update(defaults)
            except Exception as e:
                logger.exception(f"Failed to load defaults from '{defaults_path}': {e}")

        if workflow_path:
            domain_defaults = self._load_domain_defaults(vars_dir_path, workflow_path, workflow_roots) or {}
            if domain_defaults:
                logger.debug(f"Loaded {len(domain_defaults)} domain-specific variables")
            context.update(domain_defaults)

        if inline_workflow_vars:
            logger.debug(f"Merging {len(inline_workflow_vars)} inline workflow variables")
            context.update(inline_workflow_vars)

        if cli_vars:
            logger.debug(f"Merging {len(cli_vars)} CLI variables")
            context.update(cli_vars)

        logger.debug(f"Blueprint context built with {len(context)} total variables")
        return context

    def resolve_template(self, template_str: str, context: dict[str, Any]) -> str:
        """Resolve a Jinja2 template in blueprint reference.

        Args:
            template_str: Template string to resolve.
            context: Variable context for rendering.

        Returns:
            Resolved template string.

        Raises:
            BlueprintError: If template has undefined variables or syntax errors.
        """
        try:
            resolved = self.jinja2.resolve_string(template_str, context, error_context="blueprint reference")
            if template_str != resolved:
                logger.debug(f"Resolved template '{template_str}' -> '{resolved}'")
            return resolved
        except Exception as e:
            logger.exception(f"Failed to resolve blueprint template: {e}")
            raise BlueprintError(
                f"Failed to resolve blueprint template: {e}", details={"template": template_str}
            ) from e

    def evaluate_condition(self, condition: str | bool, context: dict[str, Any]) -> bool:
        """Evaluate blueprint 'if' condition.

        Handles YAML-parsed booleans, string literals, and Jinja2 expressions.

        Args:
            condition: Conditional expression to evaluate.
            context: Variable context for evaluation.

        Returns:
            Boolean result of condition evaluation.

        Raises:
            BlueprintError: If condition has undefined variables or syntax errors.
        """
        try:
            result = self.jinja2.resolve_to_bool(condition, context)
            logger.debug(f"Evaluated condition '{condition}' -> {result}")
            return result
        except Exception as e:
            logger.exception(f"Failed to evaluate blueprint condition: {e}")
            raise BlueprintError(
                f"Failed to evaluate blueprint condition: {e}", details={"condition": condition}
            ) from e

    @staticmethod
    def _load_env_vars() -> dict[str, Any]:
        """Load environment variables prefixed with NORNFLOW_VAR_.

        Returns:
            Dictionary of environment variables with prefix stripped.
        """
        env_vars = {}
        prefix = "NORNFLOW_VAR_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                var_name = key[len(prefix) :]
                env_vars[var_name] = value
        return env_vars

    @staticmethod
    def _find_domain_for_workflow(workflow_path: Path, workflow_roots: list[str]) -> str | None:
        """Find the domain directory containing the workflow.

        Args:
            workflow_path: Path to the workflow file.
            workflow_roots: List of workflow root directories.

        Returns:
            Domain name if found, None otherwise.
        """
        for root in workflow_roots:
            root_path = Path(root)
            if not workflow_path.is_relative_to(root_path):
                continue

            relative_path = workflow_path.relative_to(root_path)
            if len(relative_path.parts) > 1:
                domain = relative_path.parts[0]
                logger.debug(f"Found domain '{domain}' for workflow '{workflow_path.name}'")
                return domain
            break

        return None

    @staticmethod
    def _load_domain_defaults(
        vars_dir: Path, workflow_path: Path, workflow_roots: list[str]
    ) -> dict[str, Any]:
        """Load domain-specific default variables.

        Args:
            vars_dir: Base directory containing variable files.
            workflow_path: Path to the workflow file.
            workflow_roots: List of workflow root directories.

        Returns:
            Dictionary of domain-specific default variables.
        """
        domain = BlueprintResolver._find_domain_for_workflow(workflow_path, workflow_roots)
        if not domain:
            return {}

        domain_defaults_path = vars_dir / domain / DEFAULTS_FILENAME
        if not domain_defaults_path.exists():
            logger.debug(f"No domain defaults found at '{domain_defaults_path}'")
            return {}

        try:
            loaded = load_file_to_dict(domain_defaults_path)
            logger.debug(f"Loaded domain defaults from '{domain_defaults_path}'")
            return loaded
        except Exception as e:
            logger.exception(f"Failed to load domain defaults from '{domain_defaults_path}': {e}")
            return {}
