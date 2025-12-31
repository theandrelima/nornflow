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

NORNFLOW_SETTINGS_OPTIONAL = {
    "local_tasks": [NORNFLOW_DEFAULT_TASKS_DIR],
    "local_workflows": [NORNFLOW_DEFAULT_WORKFLOWS_DIR],
    "local_filters": [NORNFLOW_DEFAULT_FILTERS_DIR],
    "local_hooks": [NORNFLOW_DEFAULT_HOOKS_DIR],
    "imported_packages": [],
    "processors": [],
    "vars_dir": NORNFLOW_DEFAULT_VARS_DIR,
    "failure_strategy": FailureStrategy.SKIP_FAILED,
    "dry_run": False,
}

# Kwargs that cannot be passed to NornFlow.__init__; they must be set via the settings YAML file.
# These are optional settings (see NORNFLOW_SETTINGS_OPTIONAL), but if customized, use YAML.
NORNFLOW_INVALID_INIT_KWARGS = (
    "nornir_config_file",
    "local_tasks",
    "local_workflows",
    "local_filters",
    "local_hooks",
    "imported_packages",
)

# Supported extensions
NORNFLOW_SUPPORTED_YAML_EXTENSIONS = (".yaml", ".yml")

# Default inventory filter keys
JINJA_PATTERN = re.compile(r"({{.*?}}|{%-?.*?-%?})")

# Keywords in variable names that should be masked in display
PROTECTED_KEYWORDS = [
    # Authentication
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "apikey",
    "api_key",
    "access_token",
    "auth_token",
    "authorization",
    "jwt",
    "bearer",
    "sessionid",
    "session_id",
    # Cloud credentials
    "aws_access_key_id",
    "aws_secret_access_key",
    "azure_client_secret",
    "gcp_credentials",
    "gcp_private_key",
    "gcp_client_secret",
    "gcp_token",
    # Database
    "db_password",
    "db_pass",
    "db_user",
    "db_username",
    "db_token",
    "db_connection_string",
    # SSH / TLS / Certificates
    "ssh_key",
    "private_key",
    "tls_key",
    "certificate",
    "cert",
    "pem",
    "pfx",
    "keystore",
    # Environment variables
    "env_secret",
    "env_token",
    "env_password",
    "env_key",
    # 2FA / MFA / OTP
    "2fa_code",
    "mfa_code",
    "otp",
    "one_time_password",
    "verification_code",
    "authenticator_code",
    "totp",
    "hotp",
    "backup_code",
    "recovery_code",
    "sms_code",
    "email_code",
    "push_token",
    "push_auth",
    "security_code",
    # Custom patterns
    "client_secret",
    "consumer_secret",
    "app_secret",
    "webhook_secret",
    "signing_key",
    "encryption_key",
    "master_key",
    "recovery_key",
    "reset_token",
    "magic_link",
    # Config file keys
    "config_secret",
    "config_token",
    "config_password",
    "config_key",
    # Generic
    "key",
    "secret",
    "credentials",
    "identity",
    "login",
]
