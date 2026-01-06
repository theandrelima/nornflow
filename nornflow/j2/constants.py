"""Jinja2-related constants for NornFlow."""

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
TRUTHY_STRING_VALUES = ("true", "yes", "1", "on", "y", "t", "enabled")
