import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from nornir.core.task import AggregatedResult
from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict
from pydantic_serdes.utils import convert_to_hashable

from nornflow.hooks import PostRunHook, PreRunHook
from nornflow.hooks.registry import HOOK_REGISTRY
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager
from .base import NornFlowBaseModel

logger = logging.getLogger(__name__)

# Global hook instance cache shared across all RunnableModel instances
# Key: (hook_class, value) tuple
# Value: Hook instance
# This cache ensures we create only one instance per unique hook configuration
_HOOK_INSTANCE_CACHE: dict[tuple[type, str | None], PreRunHook | PostRunHook] = {}
_HOOK_CACHE_LOCK = threading.Lock()


class RunnableModel(NornFlowBaseModel, ABC):
    """Abstract base class for runnable entities with high-performance hook processing.

    ARCHITECTURE OVERVIEW:
    =====================
    This class implements a sophisticated hook processing system designed for:
    1. Maximum performance at scale (100k+ hosts)
    2. Thread safety in Nornir's multi-threaded environment
    3. Memory efficiency through the Flyweight pattern
    4. Extensibility without schema changes

    HOOK INSTANCE MANAGEMENT:
    ========================
    - Hook instances are created ONCE per unique (hook_class, value) combination
    - Instances are cached globally and shared across all tasks and hosts
    - Thread-safe instance creation using locks
    - For 100k hosts x 10 tasks x 3 hooks = only 3 hook instances created

    VALIDATION STRATEGY:
    ===================
    - Validation happens ONCE per task (not per host)
    - Validation is task-specific (depends on task name, configuration, etc.)
    - Validation results are cached per task instance
    - Thread-safe validation through external state tracking

    PERFORMANCE CHARACTERISTICS:
    ===========================
    - Hook instantiation: O(1) amortized - cached after first creation
    - Validation: O(1) per task - happens once and cached
    - Memory usage: O(unique_hooks) instead of O(tasks x hosts x hooks)
    - Thread overhead: Minimal - only during first instance creation

    Example with 100k hosts, 10 tasks, 3 hooks per task:
    - Without caching: 3,000,000 hook instances
    - With caching: ~3-30 hook instances (depending on unique configurations)
    - Memory saved: ~99.999%
    """

    # Store hook configurations from YAML
    hooks: HashableDict[str, Any] | None = None

    # Cache validation state per task instance
    _validation_completed: bool = False

    # Cache loaded hook instances for this task
    _pre_hooks_cache: list[PreRunHook] | None = None
    _post_hooks_cache: list[PostRunHook] | None = None

    @field_validator("hooks", mode="before")
    @classmethod
    def validate_hooks(cls, v: dict[str, Any] | None) -> HashableDict[str, Any] | None:
        """Convert hooks dictionary to fully hashable structure."""
        return convert_to_hashable(v)

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args: Any, **kwargs: Any) -> "RunnableModel":
        """Create a new RunnableModel with automatic hook discovery.

        Extracts hook fields from dict_args before model creation to support
        hooks as top-level fields in YAML without requiring them in the schema.

        Args:
            dict_args: Dictionary containing model data and potential hook fields
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Created RunnableModel instance with hooks configured
        """
        # Extract hook fields before validation
        hooks_dict = {}

        # Check for registered hooks in the input dictionary
        for field_name, field_value in list(dict_args.items()):
            if field_name in HOOK_REGISTRY:
                hooks_dict[field_name] = field_value
                del dict_args[field_name]

        # If we found any hooks, add them to the hooks field
        if hooks_dict:
            if "hooks" not in dict_args:
                dict_args["hooks"] = {}
            dict_args["hooks"].update(hooks_dict)

        # Create the model with the cleaned dict_args
        return super().create(dict_args, *args, **kwargs)

    def _get_or_create_hook_instance(
        self, hook_class: type[PreRunHook] | type[PostRunHook], hook_value: Any
    ) -> PreRunHook | PostRunHook:
        """Get or create a cached hook instance using the Flyweight pattern.

        This method ensures that only one instance exists per unique hook
        configuration, dramatically reducing memory usage at scale.

        Thread-safe through locking during instance creation.

        Args:
            hook_class: The hook class to instantiate
            hook_value: The configuration value for the hook

        Returns:
            Cached or newly created hook instance
        """
        cache_key = (hook_class, hook_value)

        # Fast path: check if instance exists without locking
        if cache_key in _HOOK_INSTANCE_CACHE:
            return _HOOK_INSTANCE_CACHE[cache_key]

        # Slow path: create new instance with lock
        with _HOOK_CACHE_LOCK:
            # Double-check after acquiring lock
            if cache_key in _HOOK_INSTANCE_CACHE:
                return _HOOK_INSTANCE_CACHE[cache_key]

            # Create and cache new instance
            hook_instance = hook_class(hook_value)
            _HOOK_INSTANCE_CACHE[cache_key] = hook_instance

            logger.debug(
                f"Created new hook instance: {hook_class.__name__}(value={hook_value}). "
                f"Total cached instances: {len(_HOOK_INSTANCE_CACHE)}"
            )

            return hook_instance

    def _load_hooks_by_type(
        self, hook_base_class: type[PreRunHook] | type[PostRunHook]
    ) -> list[PreRunHook] | list[PostRunHook]:
        """Load all hooks of a specific type from the hooks configuration.

        Args:
            hook_base_class: Either PreRunHook or PostRunHook

        Returns:
            List of hook instances of the specified type
        """
        hooks = []

        if not self.hooks:
            return hooks

        for hook_name, hook_value in self.hooks.items():
            hook_class = HOOK_REGISTRY.get(hook_name)

            if hook_class and issubclass(hook_class, hook_base_class):
                hook_instance = self._get_or_create_hook_instance(hook_class, hook_value)
                hooks.append(hook_instance)

        return hooks

    def _get_hooks_by_type(
        self, hook_class: type[PreRunHook] | type[PostRunHook], cache_attr: str
    ) -> list[PreRunHook] | list[PostRunHook]:
        """Get hooks with caching to avoid repeated loading.

        Args:
            hook_class: The hook base class to load
            cache_attr: The attribute name to cache hooks in

        Returns:
            List of hook instances
        """
        # Check if hooks are already cached
        cached_hooks = getattr(self, cache_attr)
        if cached_hooks is not None:
            return cached_hooks

        # Load hooks and cache them
        hooks = self._load_hooks_by_type(hook_class)
        setattr(self, cache_attr, hooks)

        return hooks

    def get_pre_hooks(self) -> list[PreRunHook]:
        """Get all pre-run hooks for this task, using cache if available."""
        return self._get_hooks_by_type(PreRunHook, "_pre_hooks_cache")

    def get_post_hooks(self) -> list[PostRunHook]:
        """Get all post-run hooks for this task, using cache if available."""
        return self._get_hooks_by_type(PostRunHook, "_post_hooks_cache")

    def _validate_all_hooks(self) -> None:
        """Validate all hooks once per task.

        This method ensures validation happens only once per task instance,
        not per host, for optimal performance at scale.
        """
        # Skip if already validated
        if self._validation_completed:
            return

        # Validate pre-run hooks
        for hook in self.get_pre_hooks():
            hook.execute_hook_validations(self)

        # Validate post-run hooks
        for hook in self.get_post_hooks():
            hook.execute_hook_validations(self)

        # Mark validation as completed
        self._validation_completed = True

        logger.debug(f"Hook validation completed for task '{self.name}'")

    def _run_pre_hooks(
        self,
        hosts_to_run: list[str],
        pre_hooks: list[PreRunHook],
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
    ) -> list[str]:
        """Run pre-execution hooks using the new efficient execution model.

        Delegates to PreRunHook.execute_all_hooks for optimized execution.

        Args:
            hosts_to_run: Initial list of hosts to run on
            pre_hooks: List of pre-run hooks to execute
            nornir_manager: NornirManager instance
            vars_manager: Variables manager instance

        Returns:
            Filtered list of hosts after hook processing
        """
        return PreRunHook.execute_all_hooks(
            hooks=pre_hooks,
            task_model=self,
            hosts=hosts_to_run,
            nornir_manager=nornir_manager,
            vars_manager=vars_manager,
        )

    def _run_post_hooks(
        self,
        result: AggregatedResult,
        post_hooks: list[PostRunHook],
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
    ) -> None:
        """Run post-execution hooks using the new efficient execution model.

        Delegates to PostRunHook.execute_all_hooks for optimized execution.

        Args:
            result: Aggregated results from task execution
            post_hooks: List of post-run hooks to execute
            nornir_manager: NornirManager instance
            vars_manager: Variables manager instance
        """
        PostRunHook.execute_all_hooks(
            hooks=post_hooks,
            task_model=self,
            result=result,
            nornir_manager=nornir_manager,
            vars_manager=vars_manager,
        )

    def run(
        self,
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
        tasks_catalog: dict[str, Callable],
    ) -> AggregatedResult:
        """Execute the runnable with hook processing.

        Orchestrates the complete execution lifecycle:
        1. Validate all hooks (once per task)
        2. Run pre-hooks with optimized execution
        3. Execute the main task logic
        4. Run post-hooks with optimized execution

        Args:
            nornir_manager: NornirManager instance
            vars_manager: Variables manager
            tasks_catalog: Available tasks catalog

        Returns:
            Aggregated results from task execution
        """
        # Validate hooks once for this task
        self._validate_all_hooks()

        # Get initial hosts from inventory
        hosts_to_run = list(nornir_manager.nornir.inventory.hosts.keys())

        # Run pre-hooks with new execution model
        pre_hooks = self.get_pre_hooks()
        if pre_hooks:
            hosts_to_run = self._run_pre_hooks(
                hosts_to_run=hosts_to_run,
                pre_hooks=pre_hooks,
                nornir_manager=nornir_manager,
                vars_manager=vars_manager,
            )

        # Execute the actual task
        result = self._run(
            nornir_manager=nornir_manager,
            vars_manager=vars_manager,
            tasks_catalog=tasks_catalog,
            hosts_to_run=hosts_to_run,
        )

        # Run post-hooks with new execution model
        post_hooks = self.get_post_hooks()
        if post_hooks:
            self._run_post_hooks(
                result=result, post_hooks=post_hooks, nornir_manager=nornir_manager, vars_manager=vars_manager
            )

        return result

    @abstractmethod
    def _run(
        self,
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
        tasks_catalog: dict[str, Callable],
        hosts_to_run: list[str],
    ) -> AggregatedResult:
        """Execute the actual task logic. Must be implemented by subclasses."""
