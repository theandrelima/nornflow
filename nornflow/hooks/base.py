"""NornFlow Hook Framework

This module implements NornFlow's extensible hook system, designed to allow
customization of task execution behavior without modifying core framework code.

PHILOSOPHY
==========

Hooks provide a clean separation between NornFlow's core execution logic and
user-defined behaviors. They follow the Flyweight pattern for memory efficiency
and use mixin composition for declarative behavior specification.

EXECUTION PHASES
================

Hooks run in two phases:
- PreRunHook: Execute before task execution, can filter hosts or modify configuration
- PostRunHook: Execute after task execution, can process results

EXECUTION SCOPES
================

Hooks can execute in two scopes:
- RunOncePerTaskMixin: Hook runs once per task across all hosts
- RunPerHostMixin: Hook runs individually for each host

BEHAVIOR MIXINS
===============

PreRunHook behaviors (mix one or more):
- FilterHostsMixin: Filters host list at task level (requires RunOncePerTaskMixin)
- ConfigureTaskMixin: Modifies task configuration

PostRunHook behaviors:
- No mixins needed - PostRunHook.process_results() handles all result processing

ORTHOGONALITY MATRIX
====================

Valid combinations:

PreRunHook:
- FilterHostsMixin + RunOncePerTaskMixin: Bulk host filtering
- ConfigureTaskMixin + RunOncePerTaskMixin: Task configuration
- ConfigureTaskMixin + RunPerHostMixin: Per-host task modification
- FilterHostsMixin + ConfigureTaskMixin + RunOncePerTaskMixin: Both filtering and config

PostRunHook:
- RunOncePerTaskMixin: Process aggregated results from all hosts
- RunPerHostMixin: Process individual host results

INVALID COMBINATIONS
====================

- PostRunHook with any PreRunHook mixins (filtering/configuration can't happen post-execution)
- FilterHostsMixin with RunPerHostMixin (task-level filtering requires task scope)
- Hook without execution scope mixin (must specify per-task or per-host)
- Hook without any behavior (must do something useful)

VALIDATION
==========

Hooks are validated at instantiation:
- Mixin compatibility (above rules)
- Method implementation (mixins require their methods to be implemented)
- Task-specific validation via validate_* methods

PERFORMANCE
===========

- Flyweight pattern: Shared hook instances across tasks/hosts
- Lazy execution: Per-task hooks run only once per task
- Capability checks: Framework only calls methods that exist
- Thread-safe: Concurrent execution support
"""

import inspect
import logging
import threading
from typing import Any, ClassVar, TYPE_CHECKING, Union
from weakref import WeakKeyDictionary

from nornflow.hooks.exceptions import HookConfigurationError, HookValidationError

if TYPE_CHECKING:
    from nornir.core.inventory import Host
    from nornir.core.task import AggregatedResult, MultiResult

    from nornflow.models import TaskModel
    from nornflow.nornir_manager import NornirManager
    from nornflow.vars.manager import NornFlowVariablesManager

logger = logging.getLogger(__name__)


class HookContext:
    """Context object passed to hooks containing all necessary dependencies."""

    def __init__(
        self, nornir_manager: "NornirManager", vars_manager: "NornFlowVariablesManager", **kwargs: Any
    ):
        self.nornir_manager = nornir_manager
        self.vars_manager = vars_manager
        self.extra = kwargs


# ============================================================================
# EXECUTION SCOPE MIXINS
# ============================================================================


class RunOncePerTaskMixin:
    """Hook executes once for the entire task across all hosts."""

    run_once_per_task: ClassVar[bool] = True


class RunPerHostMixin:
    """Hook executes individually for each host."""

    run_once_per_task: ClassVar[bool] = False


# ============================================================================
# PRE-RUN BEHAVIOR MIXINS
# ============================================================================


class FilterHostsMixin:
    """Mixin for hooks that filter which hosts execute a task at the task level."""

    _filters_hosts: ClassVar[bool] = True

    def filter_hosts(self, task_model: "TaskModel", hosts: list[str], context: HookContext) -> list[str]:
        """Filter the list of hosts that should execute this task.

        Called once per task when using RunOncePerTaskMixin.

        Args:
            task_model: The task about to be executed
            hosts: Current list of host names
            context: Hook execution context

        Returns:
            Filtered list of host names
        """
        return hosts


class ConfigureTaskMixin:
    """Mixin for hooks that modify task configuration."""

    _modifies_task: ClassVar[bool] = True

    def configure_task(self, task_model: "TaskModel", context: HookContext) -> None:
        """Modify task configuration before execution.

        Args:
            task_model: The task to configure (can be modified)
            context: Hook execution context
        """


# ============================================================================
# BASE HOOK CLASS
# ============================================================================


class Hook:
    """Base class for all hook types implementing the Flyweight pattern.

    Hooks must be composed with:
    1. An execution phase (PreRunHook or PostRunHook)
    2. An execution scope (RunOncePerTaskMixin or RunPerHostMixin)
    3. For PreRunHook: One or more behavior mixins

    The hook_name attribute must be defined by all subclasses.
    """

    hook_name: str

    def __init__(self, value: str | None = None):
        """Initialize a hook with an optional immutable configuration value."""
        self.value = value
        self._executed_tasks = WeakKeyDictionary()
        self._task_lock = threading.RLock()

        self._validate_mixin_compatibility()
        self._validate_method_implementation()

    def _validate_mixin_compatibility(self) -> None:
        """Validate that the hook's mixin combination is valid.

        Subclasses override this in PreRunHook and PostRunHook.
        """

    def _validate_method_implementation(self) -> None:
        """Validate that mixins requiring methods have those methods implemented."""
        # Define capability-to-method mapping for validation
        required_methods = {
            "_filters_hosts": ("filter_hosts", "FilterHostsMixin"),
            "_modifies_task": ("configure_task", "ConfigureTaskMixin"),
        }

        # Check each capability's required method
        for capability, (method_name, mixin_name) in required_methods.items():
            if self.has_capability(capability):
                if not any(hasattr(cls, method_name) for cls in self.__class__.__mro__):
                    raise HookConfigurationError(
                        f"Hook '{self.__class__.__name__}' uses {mixin_name} but doesn't "
                        f"implement {method_name}()"
                    )

    def has_capability(self, capability: str) -> bool:
        """Check if this hook has a specific capability through mixins.

        Args:
            capability: The capability flag name (e.g., '_filters_hosts')

        Returns:
            True if the hook has this capability, False otherwise
        """
        return getattr(self.__class__, capability, False)

    def get_execution_scope(self) -> bool:
        """Get the execution scope from mixin.

        Returns:
            True if run_once_per_task, False otherwise
        """
        return getattr(self.__class__, "run_once_per_task", False)

    def is_first_execution(self, task_model: "TaskModel") -> bool:
        """Check if this is the first execution of the hook for this task."""
        if not self.get_execution_scope():
            return True

        with self._task_lock:
            if task_model not in self._executed_tasks:
                self._executed_tasks[task_model] = True
                return True
            return False

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """Run all validate_* methods for this hook against the given task model."""
        errors = []

        validate_methods = [
            (name, method)
            for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if name.startswith("validate_")
        ]

        for method_name, method in validate_methods:
            try:
                result = method(task_model)
                if not isinstance(result, tuple) or len(result) != 2:  # noqa: PLR2004
                    errors.append(
                        (method_name, f"Must return tuple (bool, str), got {type(result).__name__}")
                    )
                    continue

                is_valid, error_msg = result
                if not is_valid:
                    errors.append((method_name, error_msg))

            except Exception as e:
                errors.append((method_name, f"Exception during validation: {e!s}"))

        if errors:
            raise HookValidationError(self.__class__.__name__, errors)

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash((self.__class__, self.value))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hook):
            return False
        return self.__class__ == other.__class__ and self.value == other.value


# ============================================================================
# PRE-RUN HOOK
# ============================================================================


class PreRunHook(Hook):
    """Base class for hooks that run before task execution.

    PreRunHooks must use one or more of:
    - FilterHostsMixin: Filter hosts at the task level
    - ConfigureTaskMixin: Modify task configuration

    They must also use either RunOncePerTaskMixin or RunPerHostMixin.
    """

    def _validate_mixin_compatibility(self) -> None:
        """Validate that PreRunHook uses valid mixins."""
        if not any([self.has_capability("_filters_hosts"), self.has_capability("_modifies_task")]):
            raise HookConfigurationError(
                f"PreRunHook '{self.__class__.__name__}' must use at least one behavior mixin "
                "(FilterHostsMixin or ConfigureTaskMixin)"
            )

        if not hasattr(self.__class__, "run_once_per_task"):
            raise HookConfigurationError(
                f"PreRunHook '{self.__class__.__name__}' must use either "
                "RunOncePerTaskMixin or RunPerHostMixin"
            )

        # FilterHostsMixin requires RunOncePerTaskMixin
        if self.has_capability("_filters_hosts") and not self.get_execution_scope():
            raise HookConfigurationError(
                f"PreRunHook '{self.__class__.__name__}' cannot use FilterHostsMixin with RunPerHostMixin. "
                "Task-level filtering requires RunOncePerTaskMixin"
            )

    @classmethod
    def execute_all_hooks(
        cls,
        hooks: list["PreRunHook"],
        task_model: "TaskModel",
        hosts: list[str],
        nornir_manager: "NornirManager",
        vars_manager: "NornFlowVariablesManager",
    ) -> list[str]:
        """Execute all pre-run hooks efficiently, respecting their capabilities."""
        if not hooks:
            return hosts

        context = HookContext(nornir_manager=nornir_manager, vars_manager=vars_manager)
        filtered_hosts = hosts.copy()

        for hook in hooks:
            scope_once = hook.get_execution_scope()

            if scope_once and hook.is_first_execution(task_model):
                if hook.has_capability("_modifies_task"):
                    hook.configure_task(task_model, context)

                if hook.has_capability("_filters_hosts"):
                    filtered_hosts = hook.filter_hosts(task_model, filtered_hosts, context)

            elif not scope_once:
                if hook.has_capability("_modifies_task") and hook.is_first_execution(task_model):
                    hook.configure_task(task_model, context)

        return filtered_hosts


# ============================================================================
# POST-RUN HOOK
# ============================================================================


class PostRunHook(Hook):
    """Base class for hooks that run after task execution.

    PostRunHooks process task execution results. The format of results
    depends on the execution scope:
    - With RunOncePerTaskMixin: receives AggregatedResult (all hosts)
    - With RunPerHostMixin: receives tuple of (Host, MultiResult) per host

    Subclasses must use either RunOncePerTaskMixin or RunPerHostMixin.
    """

    def _validate_mixin_compatibility(self) -> None:
        """Validate that PostRunHook uses valid mixins."""
        if not hasattr(self.__class__, "run_once_per_task"):
            raise HookConfigurationError(
                f"PostRunHook '{self.__class__.__name__}' must use either "
                "RunOncePerTaskMixin or RunPerHostMixin"
            )

    def process_results(
        self,
        task_model: "TaskModel",
        results: Union["AggregatedResult", tuple["Host", "MultiResult"]],
        context: "HookContext",
    ) -> None:
        """Process task results.

        Override this method to implement result processing logic.

        Args:
            task_model: The task that was executed
            results: Either AggregatedResult (with RunOncePerTaskMixin)
                    or tuple of (Host, MultiResult) (with RunPerHostMixin)
            context: Hook execution context
        """

    @classmethod
    def execute_all_hooks(
        cls,
        hooks: list["PostRunHook"],
        task_model: "TaskModel",
        result: "AggregatedResult",
        nornir_manager: "NornirManager",
        vars_manager: "NornFlowVariablesManager",
    ) -> None:
        """Execute all post-run hooks efficiently."""
        if not hooks or not result:
            return

        context = HookContext(nornir_manager=nornir_manager, vars_manager=vars_manager)

        for hook in hooks:
            scope_once = hook.get_execution_scope()

            if scope_once and hook.is_first_execution(task_model):
                hook.process_results(task_model, result, context)

            elif not scope_once:
                for host_name, host_result in result.items():
                    host = nornir_manager.nornir.inventory.hosts[host_name]
                    hook.process_results(task_model, (host, host_result), context)
