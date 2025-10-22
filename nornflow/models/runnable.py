import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from nornir.core.task import AggregatedResult
from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict
from pydantic_serdes.utils import convert_to_hashable

from nornflow.hooks import Hook
from nornflow.hooks.registry import HOOK_REGISTRY
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager
from .base import NornFlowBaseModel

logger = logging.getLogger(__name__)

# Global hook instance cache shared across all RunnableModel instances
# Key: (hook_class, value) tuple
# Value: Hook instance
# This cache ensures we create only one instance per unique hook configuration
_HOOK_INSTANCE_CACHE: dict[tuple[type, Any], Hook] = {}
_HOOK_CACHE_LOCK = threading.Lock()


class RunnableModel(NornFlowBaseModel, ABC):
    """Abstract base class for runnable entities with processor-based hook support.

    Hook Processing Architecture:
    =============================
    Hooks are now full Nornir processors that participate in the task lifecycle.
    This class manages hook discovery and caching, but execution is delegated
    to the NornFlowHookProcessor during task runtime. Hook validation is abstracted
    to the run_hook_validations() method, allowing child classes to handle it as needed.

    Performance Characteristics:
    ===========================
    - Hook instances: Created ONCE per unique (hook_class, value) pair
    - Memory usage: O(unique_hooks) via Flyweight pattern
    - Thread safety: Guaranteed via locks during instance creation
    - Validation: Happens once per task, results cached
    """

    hooks: HashableDict[str, Any] | None = None
    _hooks_cache: list[Hook] | None = None

    @field_validator("hooks", mode="before")
    @classmethod
    def validate_hooks(cls, v: dict[str, Any] | None) -> HashableDict[str, Any] | None:
        """Convert hooks to hashable structure."""
        return convert_to_hashable(v)

    @classmethod
    def create(cls, model_dict: dict[str, Any], *args: Any, **kwargs: Any) -> "RunnableModel":
        """Create a RunnableModel instance, migrating hook fields to the hooks dict.

        This method processes the input model_dict to automatically move hook-related
        keywords (matching registered hook names) into the 'hooks' field. Unknown
        keywords remain as extras, triggering Pydantic's 'extra: forbid' error.

        This ensures hook configuration is properly structured during instantiation,
        maintaining model hashability.

        Args:
            model_dict: The input dictionary for model creation.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The created RunnableModel instance.
        """
        # Extract hook fields from model_dict
        hooks_dict = {}
        keys_to_remove = []
        for key, value in model_dict.items():
            if key in HOOK_REGISTRY:
                hooks_dict[key] = value
                keys_to_remove.append(key)

        # Remove hook fields from model_dict to avoid Pydantic extras
        for key in keys_to_remove:
            del model_dict[key]

        # Add hooks to model_dict if any were found
        if hooks_dict:
            model_dict["hooks"] = convert_to_hashable(hooks_dict)

        # Proceed with standard Pydantic creation
        return super().create(model_dict, *args, **kwargs)

    def _get_or_create_hook_instance(self, hook_class: type[Hook], hook_value: Any) -> Hook:
        """Get or create a cached hook instance using the Flyweight pattern."""
        cache_key = (hook_class, hook_value)

        if cache_key in _HOOK_INSTANCE_CACHE:
            return _HOOK_INSTANCE_CACHE[cache_key]

        with _HOOK_CACHE_LOCK:
            if cache_key not in _HOOK_INSTANCE_CACHE:
                _HOOK_INSTANCE_CACHE[cache_key] = hook_class(hook_value)
            return _HOOK_INSTANCE_CACHE[cache_key]

    def get_hooks(self) -> list[Hook]:
        """Get all hooks for this runnable."""
        if self._hooks_cache is not None:
            return self._hooks_cache

        hooks = []
        if self.hooks:
            for hook_name, hook_value in self.hooks.items():
                hook_class = HOOK_REGISTRY.get(hook_name)
                if hook_class:
                    hook = self._get_or_create_hook_instance(hook_class, hook_value)
                    hooks.append(hook)
                else:
                    logger.warning(f"Unknown hook '{hook_name}' in task configuration")

        self._hooks_cache = hooks
        return hooks

    def run_hook_validations(self) -> None:
        """Run hook validations for this runnable.

        This method should be explicitly called at the beginning of the run() method
        in subclasses to ensure hooks are validated before execution.
        """
        hooks = self.get_hooks()
        for hook in hooks:
            hook.execute_hook_validations(self)

    def prepare_task_context(
        self, vars_manager: NornFlowVariablesManager, nornir_manager: NornirManager
    ) -> dict[str, Any]:
        """Prepare task arguments with hook context for execution.

        This method assembles the task arguments, collects hooks, and injects
        the NornFlow context for processor-based hook execution.

        Args:
            vars_manager: The variables manager instance.
            nornir_manager: The Nornir manager instance.

        Returns:
            Dictionary of task arguments with injected context.
        """
        # Get hooks for this task
        hooks = self.get_hooks()

        # Create context for the processor
        nornflow_context = {
            "task_model": self,
            "hooks": hooks,
            "vars_manager": vars_manager,
            "nornir_manager": nornir_manager,
        }

        # Assemble task args
        task_args = {} if self.args is None else dict(self.args)

        # Inject context into task params
        task_args["_nornflow_context"] = nornflow_context

        return task_args

    def prepare_and_validate_task_context(
        self, vars_manager: NornFlowVariablesManager, nornir_manager: NornirManager
    ) -> dict[str, Any]:
        """Prepare and validate task context, returning ready-to-use task arguments.

        This method combines hook validation and task context preparation into a single
        operation, ensuring hooks are validated before execution and returning the
        fully prepared task arguments with injected context.

        Args:
            vars_manager: The variables manager instance.
            nornir_manager: The Nornir manager instance.

        Returns:
            Dictionary of task arguments with injected context, ready for execution.
        """
        self.run_hook_validations()
        return self.prepare_task_context(vars_manager, nornir_manager)

    @abstractmethod
    def run(
        self,
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
        tasks_catalog: dict[str, Callable],
    ) -> AggregatedResult:
        """Execute the runnable."""
        pass
