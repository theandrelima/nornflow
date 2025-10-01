import re
from enum import Enum

try:
    # Python 3.11+ provides StrEnum
    from enum import StrEnum
except Exception:

    class StrEnum(str, Enum):
        """Compatibility StrEnum for Python < 3.11"""

        @staticmethod
        def _generate_next_value_(name: str, start: int, count: int, last_values: list) -> str:
            return name

        def __str__(self) -> str:
            return str(self.value)


class FailureStrategy(StrEnum):
    """
    Defines how NornFlow handles task failures during workflow execution.

    Attributes:
        SKIP_FAILED: When a task fails on a host, that host is removed from
            subsequent tasks in the workflow. Other hosts continue normally.
            This is the default strategy for most automation scenarios.

        FAIL_FAST: When a failure is detected on any host, the workflow adds
            adds all hosts to Nonir's failed_hosts, effectivelly signaling no
            more tasks should run. Already-running threads will complete
            their current task before stopping. No new tasks will start.

        RUN_ALL: All tasks are executed on all hosts regardless of failures.
            Errors are collected and reported at the end. Useful for diagnostic
            or audit workflows where comprehensive results are needed.
    """

    SKIP_FAILED = "skip-failed"
    FAIL_FAST = "fail-fast"
    RUN_ALL = "run-all"

    @classmethod
    def _missing_(cls, value: object) -> "FailureStrategy | None":
        """Handle underscore/hyphen variations for flexibility."""
        if isinstance(value, str):
            # Normalize by replacing underscores with hyphens
            normalized = value.lower().replace("_", "-")
            for member in cls:
                if member.value == normalized:
                    return member
        return None


# Special inventory filter keys that use NornFlow provided custom filter functions
NORNFLOW_SPECIAL_FILTER_KEYS = ["hosts", "groups"]

# used to track the mandatory kwargs for a NornFlowSettings object
NONRFLOW_SETTINGS_MANDATORY = ("nornir_config_file",)

# used to track the optional kwargs for a NornFlowSettings object
NONRFLOW_SETTINGS_OPTIONAL = {
    "local_tasks_dirs": [],
    "local_workflows_dirs": [],
    "local_filters_dirs": [],
    "imported_packages": [],
    "processors": [],
    "vars_dir": "vars",
    "failure_strategy": FailureStrategy.SKIP_FAILED,
}

# Used to check if the kwargs passed to a NornFlow initializer are valid.
# The args listed here are can only be passed through a nornflow settings YAML file
# that will be used to initialize a NornFlowSettings object
NORNFLOW_INVALID_INIT_KWARGS = (
    "nornir_config_file",
    "local_tasks_dirs",
    "local_workflows_dirs",
    "local_filters_dirs",
    "imported_packages",
)

# Supported extensions
NORNFLOW_SUPPORTED_YAML_EXTENSIONS = (".yaml", ".yml")

# Default inventory filter keys
JINJA_PATTERN = re.compile(r"({{.*?}}|{%-?.*?-%?})")
