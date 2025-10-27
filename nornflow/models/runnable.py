import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from nornir.core.task import AggregatedResult
from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict
from pydantic_serdes.utils import convert_to_hashable

from nornflow.builtins.processors import NornFlowHookProcessor
from nornflow.hooks import Hook
from nornflow.hooks.loader import load_hooks
from nornflow.hooks.registry import HOOK_REGISTRY
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager
from .base import NornFlowBaseModel

logger = logging.getLogger(__name__)


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

    def get_hooks(self) -> list[Hook]:
        """Get all hooks for this runnable."""
        if self._hooks_cache is not None:
            return self._hooks_cache

        self._hooks_cache = load_hooks(self.hooks or {})
        return self._hooks_cache

    def run_hook_validations(self) -> None:
        """Run hook validations for this runnable.

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

    def register_hook_context_and_validate(
        self,
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
        task_func: Callable
    ) -> None:
        """Register hook context with the processor and validate hooks.

        This method encapsulates all hook-related setup:
        1. Validates hooks
        2. Finds the NornFlowHookProcessor
        3. Registers context for the upcoming task

        Args:
            nornir_manager: The Nornir manager instance.
            vars_manager: The variables manager instance.
            task_func: The task function that will be executed.
        """
        # Validate hooks first
        self.run_hook_validations()
        
        # Try to get the NornFlowHookProcessor from the Nornir instance
        try:
            hook_processor = nornir_manager.get_processor_by_type(NornFlowHookProcessor)
            
            # Prepare the context for this task
            nornflow_context = {
                "task_model": self,
                "hooks": self.get_hooks(),
                "vars_manager": vars_manager,
                "nornir_manager": nornir_manager,
            }
            
            # Register the context with the processor
            hook_processor.register_task_context(task_func, nornflow_context)
            
        except Exception as e:
            # If no hook processor found, hooks won't work but execution continues
            logger.debug(f"Could not register hook context: {e}")

    @abstractmethod
    def run(
        self,
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
        tasks_catalog: dict[str, Callable],
    ) -> AggregatedResult:
        """Execute the runnable."""
        pass
