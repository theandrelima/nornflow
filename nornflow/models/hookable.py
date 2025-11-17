import logging
from abc import ABC
from collections.abc import Callable
from typing import Any

from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict
from pydantic_serdes.utils import convert_to_hashable

from nornflow.builtins.processors import NornFlowHookProcessor
from nornflow.exceptions import ProcessorError
from nornflow.hooks import Hook, HOOK_REGISTRY
from nornflow.hooks.loader import load_hooks
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager
from .base import NornFlowBaseModel

logger = logging.getLogger(__name__)


class HookableModel(NornFlowBaseModel, ABC):
    """Abstract base class for models that support hooks.

    Hook Processing Architecture:
    =============================
    Hooks are full Nornir processors that participate in the task lifecycle.
    This class manages hook discovery and caching, but execution is delegated
    to the NornFlowHookProcessor during task runtime. Hook validation is abstracted
    to the run_hook_validations() method, allowing child classes to handle it as needed.

    Performance Characteristics:
    ===========================
    - Hook instances: Created ONCE per unique (hook_class, value) pair
    - Memory usage: O(unique_hooks) via Flyweight pattern
    - Thread safety: Guaranteed via locks during instance creation
    - Validation: Happens once per task, results cached
    - Processor caching: Hook processor reference cached to avoid repeated lookups
    """

    hooks: HashableDict[str, Any] | None = None
    _hooks_cache: list[Hook] | None = None
    _hook_processor_cache: NornFlowHookProcessor | None = None

    @field_validator("hooks", mode="before")
    @classmethod
    def validate_hooks(cls, v: dict[str, Any] | None) -> HashableDict[str, Any] | None:
        """Convert hooks to hashable structure."""
        return convert_to_hashable(v)

    @classmethod
    def create(cls, model_dict: dict[str, Any], *args: Any, **kwargs: Any) -> "HookableModel":
        """Create a HookableModel instance, migrating hook fields to the hooks dict.

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
            The created HookableModel instance.
        """
        hooks_dict = {}
        keys_to_remove = []
        for key, value in model_dict.items():
            if key in HOOK_REGISTRY:
                hooks_dict[key] = value
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del model_dict[key]

        if hooks_dict:
            model_dict["hooks"] = convert_to_hashable(hooks_dict)

        return super().create(model_dict, *args, **kwargs)

    def get_hooks(self) -> list[Hook]:
        """Get all hooks for this hookable model."""
        if self._hooks_cache is not None:
            return self._hooks_cache

        self._hooks_cache = load_hooks(self.hooks or {})
        return self._hooks_cache

    def run_hook_validations(self) -> None:
        """Run hook validations for this hookable model.

        This method should be explicitly called at the beginning of the run() method
        in subclasses to ensure hooks are validated before execution.
        """
        hooks = self.get_hooks()
        for hook in hooks:
            hook.execute_hook_validations(self)

    def get_task_args(self) -> dict[str, Any]:
        """Get clean task arguments without any NornFlow context.

        Returns:
            Dictionary of task arguments for the task function.
        """
        return {} if self.args is None else dict(self.args)

    def validate_hooks_and_set_task_context(
        self, nornir_manager: NornirManager, vars_manager: NornFlowVariablesManager, task_func: Callable
    ) -> None:
        """Validate hooks and set task-specific context in the hook processor.

        This method:
        1. Validates hooks
        2. Gets/caches the hook processor reference (once per HookableModel lifecycle)
        3. Sets task-specific context on the processor

        Args:
            nornir_manager: The Nornir manager instance.
            vars_manager: The variables manager instance.
            task_func: The task function that will be executed.

        Raises:
            ProcessorError: If hooks are configured but hook processor cannot be retrieved.
        """
        self.run_hook_validations()

        hooks = self.get_hooks()

        if not self._hook_processor_cache:
            try:
                self._hook_processor_cache = nornir_manager.get_processor_by_type(NornFlowHookProcessor)
            except Exception as e:
                raise ProcessorError(
                    f"Hooks are configured but NornFlowHookProcessor could not be retrieved: {e}"
                ) from e

        task_context = {
            "task_model": self,
            "hooks": hooks,
        }
        self._hook_processor_cache.task_specific_context = task_context
