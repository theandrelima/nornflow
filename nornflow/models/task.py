from collections.abc import Callable
from typing import Any, ClassVar

from nornir.core.task import AggregatedResult
from pydantic import field_validator
from pydantic_serdes.custom_collections import HashableDict
from pydantic_serdes.utils import convert_to_hashable

from nornflow.exceptions import TaskError
from nornflow.models import RunnableModel
from nornflow.models.validators import run_post_creation_task_validation
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager


class TaskModel(RunnableModel):
    _key = (
        "id",
        "name",
    )
    _directive = "tasks"
    _err_on_duplicate = False

    # Exclude 'args' from universal Jinja2 validation since it's allowed there
    _exclude_from_universal_validations: ClassVar[tuple[str, ...]] = ("args",)

    id: int | None = None
    name: str
    args: HashableDict[str, Any | None] | None = None

    @classmethod
    def create(cls, dict_args: dict[str, Any], *args: Any, **kwargs: Any) -> "TaskModel":
        """Create a new TaskModel with auto-incrementing id and hook discovery."""
        # Get current tasks and calculate next id
        current_tasks = cls.get_all()
        next_id = len(current_tasks) + 1 if current_tasks else 1

        # Set the id in dict_args
        dict_args["id"] = next_id

        # Call parent's create method (handles hook discovery and runs universal validation)
        new_task = super().create(dict_args, *args, **kwargs)
        run_post_creation_task_validation(new_task)
        return new_task

    @field_validator("args", mode="before")
    @classmethod
    def validate_args(cls, v: HashableDict[str, Any] | None) -> HashableDict[str, Any] | None:
        """Validate the args dictionary and convert to fully hashable structure.

        Args:
            v: The args dictionary to validate.

        Returns:
            The validated args with all nested structures converted to hashable equivalents.
        """
        return convert_to_hashable(v)

    def _run(
        self,
        nornir_manager: NornirManager,
        vars_manager: NornFlowVariablesManager,
        tasks_catalog: dict[str, Callable],
        hosts_to_run: list[str],
    ) -> AggregatedResult:
        """Execute the task logic.

        Args:
            nornir_manager: The NornirManager instance.
            vars_manager: The variables manager.
            tasks_catalog: Task catalog.
            hosts_to_run: Filtered list of host names.

        Returns:
            The aggregated result.

        Raises:
            TaskError: If task not found.
        """
        # Get the task function from the catalog
        task_func = tasks_catalog.get(self.name)
        if not task_func:
            raise TaskError(f"Task function for '{self.name}' not found in tasks catalog")

        # Prepare task arguments
        task_args = {} if self.args is None else dict(self.args)

        # Filter the nornir object to only run on specified hosts
        if hosts_to_run:
            filtered_nornir = nornir_manager.nornir.filter(filter_func=lambda host: host.name in hosts_to_run)
        else:
            # If no hosts to run, return empty result
            return AggregatedResult(name=self.name)

        # Execute the task on the filtered nornir instance
        return filtered_nornir.run(task=task_func, **task_args)
