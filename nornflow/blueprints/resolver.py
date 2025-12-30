import logging
import os
from pathlib import Path
from typing import Any

from pydantic_serdes.utils import load_file_to_dict

from nornflow.exceptions import BlueprintError
from nornflow.vars.constants import DEFAULTS_FILENAME, JINJA2_MARKERS, TRUTHY_STRING_VALUES
from nornflow.vars.jinja2_utils import Jinja2EnvironmentManager

logger = logging.getLogger(__name__)


class BlueprintResolver:
    """Handles variable context building and template resolution for blueprints.

    This class manages the assembly-time variable context (subset of variables
    available during workflow loading) and provides Jinja2 template resolution
    for blueprint references and conditions.
    """

    def __init__(self, jinja2_manager: Jinja2EnvironmentManager):
        """Initialize the resolver with a Jinja2 manager.

        Args:
            jinja2_manager: Manager for Jinja2 template rendering.
        """
        self.jinja2_manager = jinja2_manager

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
        context = {}

        context.update(self._load_env_vars())

        vars_dir_path = Path(vars_dir)
        defaults_path = vars_dir_path / DEFAULTS_FILENAME
        if defaults_path.exists():
            try:
                context.update(load_file_to_dict(defaults_path))
            except Exception as e:
                logger.warning(f"Failed to load defaults file {defaults_path}: {e}")

        if workflow_path:
            domain_defaults = self._load_domain_defaults(vars_dir_path, workflow_path, workflow_roots)
            context.update(domain_defaults)

        if inline_workflow_vars:
            context.update(inline_workflow_vars)

        if cli_vars:
            context.update(cli_vars)

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
            return self.jinja2_manager.render_template(template_str, context, "blueprint reference")
        except Exception as e:
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
            if isinstance(condition, bool):
                return condition

            condition_stripped = condition.strip()

            if not any(marker in condition_stripped for marker in JINJA2_MARKERS):
                return condition_stripped.lower() in TRUTHY_STRING_VALUES

            template_str = condition_stripped

            result = self.jinja2_manager.render_template(template_str, context, "blueprint condition")
            return result.lower() in TRUTHY_STRING_VALUES
        except Exception as e:
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
                return relative_path.parts[0]
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
            return {}

        try:
            return load_file_to_dict(domain_defaults_path)
        except Exception as e:
            logger.warning(f"Failed to load domain defaults from {domain_defaults_path}: {e}")
            return {}
