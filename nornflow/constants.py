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
NORNFLOW_SETTINGS_MANDATORY = ("nornir_config_file",)

NORNFLOW_DEFAULT_TASKS_DIR = "tasks"
NORNFLOW_DEFAULT_WORKFLOWS_DIR = "workflows"
NORNFLOW_DEFAULT_FILTERS_DIR = "filters"
NORNFLOW_DEFAULT_HOOKS_DIR = "hooks"
NORNFLOW_DEFAULT_BLUEPRINTS_DIR = "blueprints"
NORNFLOW_DEFAULT_VARS_DIR = "vars"
NORNFLOW_DEFAULT_J2_FILTERS_DIR = "j2_filters"
NORNFLOW_DEFAULT_LOGGER = {"directory": ".nornflow/logs", "level": "INFO"}
NORNFLOW_DEFAULT_REDACTION = {"enabled": True, "sensitive_names": []}

NORNFLOW_SETTINGS_OPTIONAL = {
    "local_tasks": [NORNFLOW_DEFAULT_TASKS_DIR],
    "local_workflows": [NORNFLOW_DEFAULT_WORKFLOWS_DIR],
    "local_filters": [NORNFLOW_DEFAULT_FILTERS_DIR],
    "local_hooks": [NORNFLOW_DEFAULT_HOOKS_DIR],
    "local_j2_filters": [NORNFLOW_DEFAULT_J2_FILTERS_DIR],
    "packages": [],
    "processors": [],
    "vars_dir": NORNFLOW_DEFAULT_VARS_DIR,
    "failure_strategy": FailureStrategy.SKIP_FAILED,
    "dry_run": False,
    "logger": NORNFLOW_DEFAULT_LOGGER,
    "redaction": NORNFLOW_DEFAULT_REDACTION,
}

# Kwargs that cannot be passed to NornFlow.__init__; they must be set via the settings YAML file.
# These are optional settings (see NORNFLOW_SETTINGS_OPTIONAL), but if customized, use YAML.
NORNFLOW_INVALID_INIT_KWARGS = (
    "nornir_config_file",
    "local_tasks",
    "local_workflows",
    "local_filters",
    "local_hooks",
    "local_j2_filters",
    "packages",
    "logger",
    # 'redaction' is settings-only; use '--no-redact' / 'no_redact=True' to disable terminal masking per run
    "redaction",
)

# Supported extensions
NORNFLOW_SUPPORTED_YAML_EXTENSIONS = (".yaml", ".yml")

# Default inventory filter keys
JINJA_PATTERN = re.compile(r"({{.*?}}|{%-?.*?-%?})")

# Output redaction — CLI warnings and masking engine
REDACTION_FULL_DISABLED_WARNING = (
    "Warning: All output redaction is disabled. Sensitive values may appear in terminal output "
    "and log files."
)
# Terminal off, logs on (e.g. --no-redact with default settings).
REDACTION_TERMINAL_DISABLED_WARNING = (
    "Warning: Terminal output redaction is disabled. Sensitive values may appear in "
    "terminal output. Log files remain redacted per settings."
)
# Terminal on, logs off (e.g. logs_enabled: false with enabled: true).
REDACTION_LOGS_DISABLED_WARNING = (
    "Warning: Log redaction is disabled. Sensitive values may appear in log files "
    "and stderr log output."
)

REDACTED = "***REDACTED***"
# Strings below this size always run the regex pass; larger strings use a keyword
# substring pre-check first to avoid scanning huge blobs with no secrets.
LARGE_TEXT_THRESHOLD = 8192

# Protected keywords for output redaction (see nornflow.masking).
#
# Segment-aware matching: normalize the key (lowercase; '-' and '.' → '_'), then
# redact when the full name or any '_'-delimited segment equals an entry below
# (e.g. token → nautobot_token; key → api_key; secret → client_secret).
#
# Prefer short keywords over compound synonyms. List a compound only when it
# cannot be inferred from segments (e.g. apikey, db_connection_string).
PROTECTED_KEYWORDS = [
    # Core secret-bearing keywords (match as full key or as a segment)
    "password",
    "passwd",
    "pwd",
    "pass",
    "secret",
    "token",
    "key",
    "credentials",
    "code",
    # Auth / session
    "authorization",
    "auth",
    "jwt",
    "bearer",
    "login",
    "session",
    "sessionid",
    # MFA
    "otp",
    "totp",
    "hotp",
    "2fa",
    "mfa",
    # TLS / crypto material
    "certificate",
    "cert",
    "pem",
    "pfx",
    "keystore",
    # Identity / federation
    "identity",
    # Non-segment spellings and exact-only compounds
    "apikey",
    "db_connection_string",
    "magic_link",
    "push_auth",
]

# Catalog namespaces and bare-name resolution tiers (see nornflow.catalogs).
BUILTIN_NAMESPACE = "nornflow"
LOCAL_NAMESPACE = "local"
TIER_BUILTIN = "builtin"
TIER_LOCAL = "local"
TIER_PACKAGE = "package"
TIER_ORDER = (TIER_BUILTIN, TIER_LOCAL, TIER_PACKAGE)
