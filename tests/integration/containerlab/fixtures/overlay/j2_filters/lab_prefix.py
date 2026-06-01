"""Local Jinja2 filter used by containerlab var-level integration workflows."""


def lab_prefix(value: str, prefix: str = "LAB") -> str:
    """Return value prefixed for lab assertions.

    Args:
        value: Input string from a template.
        prefix: Prefix to prepend.

    Returns:
        ``{prefix}:{value}`` string.
    """
    return f"{prefix}:{value}"
