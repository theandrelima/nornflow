# Prefix for environment variables that should be loaded into the variable system
ENV_VAR_PREFIX = "NORNFLOW_VAR_"

# File name for default variables
DEFAULTS_FILENAME = "defaults.yaml"

# Template markers for detecting Jinja2 templates - all opening variations
JINJA2_MARKERS = [
    "{{",  # Standard variable output
    "{{-",  # Variable with left whitespace control
    "{%",  # Statement/control structure
    "{%-",  # Statement with left whitespace control
    "{#",  # Comment
    "{#-",  # Comment with left whitespace control
]

# Lower case string values that evaluate to True when converting to boolean.
# This provides a centralized reference point to avoid ambiguity across the codebase.
# Note: This has limited use - primarily for hook configurations and CLI flags.
TRUTHY_STRING_VALUES = ("true", "yes", "1", "on", "y", "t", "enabled")
