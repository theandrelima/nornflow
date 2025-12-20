from collections.abc import Callable
from typing import Any, ClassVar

from nornir.core.task import AggregatedResult
from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict
from pydantic_serdes.utils import convert_to_hashable

from nornflow.exceptions import TaskError
from nornflow.models import HookableModel
from nornflow.models.validators import run_post_creation_task_validation
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager


class TaskModel(HookableModel):
    """Task model with processor-based hook support.

    CRITICAL - Model Immutability:
    ==============================
    TaskModel instances are PydanticSerdes models and are hashable by design.
    NEVER modify TaskModel attributes within Hook classes!

    Why This Matters:
    - Hashability: Changing attributes after initialization breaks the hash contract
    - Cache Corruption: Modified models could corrupt internal caches using models as keys
    - Thread Safety: Mutable models in concurrent execution could cause race conditions

    Correct Approach:
    Modify Nornir task parameters instead of the model:
        task.params["new_key"] = "value"  # Safe
    NOT:
        task_model.args["new_key"] = "value"  # BREAKS HASHABILITY!

    Hook Agnosticism:
    =================
    TaskModel is mostly agnostic to hooks. Hook validation is delegated to the parent
    via run_hook_validations(), so TaskModel focuses solely on task execution logic.
    """

    _key = ("id", "name")
    _directive = "tasks"
    _err_on_duplicate = False
    _exclude_from_universal_validations: ClassVar[tuple[str, ...]] = ("args", "hooks")

    id: int | None = None
    name: str
    args: HashableDict[str, Any | None] | None = None

    @property
    def canonical_id(self) -> str:
        """
        Combines the task name with the model ID to create a garanteed always-unique
        identifier that distinguishes between different instances of the same task
        function in a workflow execution.

        Returns:
            A unique string identifier for this task instance.
        """
        if self.id:
            return f"{self.name}_{self.id}"
        return self.name

    @field_validator("args", mode="before")
    @classmethod
    def validate_args(cls, v: HashableDict[str, Any] | None) -> HashableDict[str, Any] | None:
        """Validate and convert args to hashable structure."""
        return convert_to_hashable(v)

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args: Any, **kwargs: Any) -> "TaskModel":
        """Create a new TaskModel with auto-incrementing id."""
        current_tasks = cls.get_all()
        next_id = len(current_tasks) + 1 if current_tasks else 1
        dict_args["id"] = next_id

        new_task = super().create(dict_args, *args, **kwargs)
        run_post_creation_task_validation(new_task)
        return new_task

    def run(
        self,
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
        tasks_catalog: dict[str, Callable],
    ) -> AggregatedResult:
        """Execute the task using the provided managers and tasks catalog."""
        task_func = tasks_catalog.get(self.name)
        if not task_func:
            raise TaskError(f"Task function for '{self.name}' not found in tasks catalog")

        task_args = self.get_task_args()

        self.validate_hooks_and_set_task_context(nornir_manager, vars_manager, task_func)

        result = nornir_manager.nornir.run(task=task_func, **task_args)
        return result
