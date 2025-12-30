import logging
from pathlib import Path
from typing import Any

from pydantic_serdes.utils import load_file_to_dict

from nornflow.blueprints.resolver import BlueprintResolver
from nornflow.exceptions import BlueprintCircularDependencyError, BlueprintError
from nornflow.utils import get_file_content_hash

logger = logging.getLogger(__name__)


class BlueprintExpander:
    """Handles recursive blueprint expansion with circular dependency detection.

    This class orchestrates the expansion of blueprint references into actual
    task definitions, including nested blueprint support and validation.
    """

    def __init__(self, resolver: BlueprintResolver):
        """Initialize the expander with a resolver.

        Args:
            resolver: BlueprintResolver for template resolution and context building.
        """
        self.resolver = resolver

    def expand_blueprints(
        self,
        tasks: list[dict[str, Any]],
        blueprints_catalog: dict[str, Path] | None,
        vars_dir: Path | None,
        workflow_path: Path | None,
        workflow_roots: list[str] | None,
        inline_vars: dict[str, Any] | None,
        cli_vars: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Expand blueprint references in tasks list.

        Args:
            tasks: List of task dictionaries (may contain blueprint references).
            blueprints_catalog: Catalog mapping blueprint names to file paths.
            vars_dir: Directory containing variable files.
            workflow_path: Path to the workflow file.
            workflow_roots: List of workflow root directories.
            inline_vars: Variables defined in the workflow YAML.
            cli_vars: CLI variables with highest precedence.

        Returns:
            Expanded list of task dictionaries with blueprints resolved.

        Raises:
            BlueprintError: If blueprint expansion fails.
        """
        if not vars_dir or not workflow_roots:
            return tasks

        if not blueprints_catalog:
            blueprints_catalog = {}

        context = self.resolver.build_context(
            vars_dir=vars_dir,
            workflow_path=workflow_path,
            workflow_roots=workflow_roots,
            inline_workflow_vars=inline_vars,
            cli_vars=cli_vars,
        )

        expansion_stack: list[str] = []
        name_stack: list[str] = []
        content_cache: dict[str, list[dict[str, Any]]] = {}

        expanded = []
        for task_dict in tasks:
            processed_tasks = self._process_task_item(
                task_dict, blueprints_catalog, context, expansion_stack, name_stack, content_cache
            )
            expanded.extend(processed_tasks)

        return expanded

    def _process_task_item(
        self,
        task_dict: dict[str, Any],
        blueprints_catalog: dict[str, Path],
        context: dict[str, Any],
        expansion_stack: list[str],
        name_stack: list[str],
        content_cache: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Process a single task item, expanding blueprints or returning regular tasks.

        Args:
            task_dict: Task or blueprint reference dictionary.
            blueprints_catalog: Catalog mapping blueprint names to file paths.
            context: Variable context for template resolution.
            expansion_stack: Stack of content hashes for circular detection.
            name_stack: Stack of blueprint names for error reporting.
            content_cache: Cache mapping content hash to parsed tasks.

        Returns:
            List of task dictionaries.
        """
        if "blueprint" not in task_dict:
            return [task_dict]

        if not self._should_include_blueprint(task_dict, context):
            return []

        return self._expand_single_blueprint(
            task_dict, blueprints_catalog, context, expansion_stack, name_stack, content_cache
        )

    def _should_include_blueprint(self, blueprint_ref: dict[str, Any], context: dict[str, Any]) -> bool:
        """Check if blueprint should be included based on 'if' condition.

        Args:
            blueprint_ref: Blueprint reference dictionary.
            context: Variable context for condition evaluation.

        Returns:
            True if blueprint should be included, False otherwise.
        """
        if "if" not in blueprint_ref:
            return True

        return self.resolver.evaluate_condition(blueprint_ref["if"], context)

    def _expand_single_blueprint(
        self,
        blueprint_ref: dict[str, Any],
        blueprints_catalog: dict[str, Path],
        context: dict[str, Any],
        expansion_stack: list[str],
        name_stack: list[str],
        content_cache: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Expand a single blueprint reference.

        Args:
            blueprint_ref: Blueprint reference dictionary.
            blueprints_catalog: Catalog mapping blueprint names to file paths.
            context: Variable context for template resolution.
            expansion_stack: Stack of content hashes for circular detection.
            name_stack: Stack of blueprint names for error reporting.
            content_cache: Cache mapping content hash to parsed tasks.

        Returns:
            List of expanded task dictionaries.

        Raises:
            BlueprintError: If blueprint expansion fails.
            BlueprintCircularDependencyError: If circular dependency detected.
        """
        blueprint_name = blueprint_ref.get("blueprint")
        if not blueprint_name:
            raise BlueprintError("Blueprint reference missing 'blueprint' field")

        resolved_name = self.resolver.resolve_template(blueprint_name, context)
        blueprint_path = self._resolve_blueprint_to_path(resolved_name, blueprints_catalog)
        content_hash = get_file_content_hash(blueprint_path)

        if content_hash in expansion_stack:
            raise BlueprintCircularDependencyError(blueprint_path.name, name_stack)

        expansion_stack.append(content_hash)
        name_stack.append(blueprint_path.name)
        try:
            if content_hash not in content_cache:
                content_cache[content_hash] = self._load_blueprint_tasks(blueprint_path)

            blueprint_tasks = content_cache[content_hash]

            expanded = []
            for task_dict in blueprint_tasks:
                processed = self._process_task_item(
                    task_dict, blueprints_catalog, context, expansion_stack, name_stack, content_cache
                )
                expanded.extend(processed)

            return expanded
        finally:
            expansion_stack.pop()
            name_stack.pop()

    @staticmethod
    def _resolve_blueprint_to_path(blueprint_ref: str, blueprints_catalog: dict[str, Path]) -> Path:
        """Resolve blueprint reference to file path.

        Resolution order:
        1. Catalog lookup (by name)
        2. Direct file path (relative or absolute, must include suffix)

        Args:
            blueprint_ref: Blueprint name or file path.
            blueprints_catalog: Catalog mapping blueprint names to file paths.

        Returns:
            Resolved file path.

        Raises:
            BlueprintError: If blueprint cannot be found.
        """
        if blueprint_ref in blueprints_catalog:
            return blueprints_catalog[blueprint_ref]

        path = Path(blueprint_ref)

        if path.is_absolute() and path.exists():
            return path

        # Relative to current working directory
        resolved = Path.cwd() / path
        if resolved.exists():
            return resolved

        raise BlueprintError(
            (
                "Blueprint not found in catalog or filesystem. "
                f"Note: relative blueprint paths are resolved against the current "
                f"working directory ({Path.cwd()})."
            ),
            blueprint_name=blueprint_ref,
            details={
                "searched_locations": [
                    f"Catalog: {list(blueprints_catalog.keys())[:5]}...",
                    str(Path.cwd() / path),
                ],
                "current_working_directory": str(Path.cwd()),
                "note": (
                    "The provided blueprint reference was interpreted as a path "
                    "relative to the current working directory. Ensure you run "
                    "nornflow from the expected directory or provide an absolute path."
                ),
            },
        )

    @staticmethod
    def _load_blueprint_tasks(blueprint_path: Path) -> list[dict[str, Any]]:
        """Load and validate blueprint structure from file.

        Args:
            blueprint_path: Path to the blueprint file.

        Returns:
            List of task dictionaries from the blueprint.

        Raises:
            BlueprintError: If blueprint structure is invalid.
        """
        try:
            blueprint_data = load_file_to_dict(blueprint_path)
        except Exception as e:
            raise BlueprintError(
                f"Failed to load blueprint file: {e}",
                blueprint_name=str(blueprint_path.name),
                details={"path": str(blueprint_path)},
            ) from e

        actual_keys = set(blueprint_data.keys())

        if actual_keys != {"tasks"}:
            raise BlueprintError(
                f"Blueprint must contain ONLY 'tasks' key, found: {', '.join(sorted(actual_keys))}",
                blueprint_name=str(blueprint_path.name),
                details={
                    "path": str(blueprint_path),
                    "expected": ["tasks"],
                    "found": sorted(actual_keys),
                },
            )

        if not isinstance(blueprint_data["tasks"], list):
            raise BlueprintError(
                f"'tasks' must be a list, got {type(blueprint_data['tasks']).__name__}",
                blueprint_name=str(blueprint_path.name),
                details={"path": str(blueprint_path)},
            )

        return blueprint_data["tasks"]
