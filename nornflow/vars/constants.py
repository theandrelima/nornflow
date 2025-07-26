# Prefix for environment variables that should be loaded into the variable system
ENV_VAR_PREFIX = "NORNFLOW_VAR_"

# Default directory for variable files
VARS_DIR_DEFAULT = "vars"

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
