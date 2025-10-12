"""Python builtin functions wrapped as Jinja2 filters."""

from collections.abc import Iterable
from typing import Any


def filter_enumerate(iterable: Iterable[Any], start: int = 0) -> list[tuple[int, Any]]:
    """Get index-value pairs."""
    return list(enumerate(iterable, start))


def filter_zip(*iterables: Iterable[Any]) -> list[tuple[Any, ...]]:
    """Combine sequences."""
    return list(zip(*iterables, strict=False))


def filter_range(*args: int) -> list[int]:
    """Generate number sequence."""
    return list(range(*args))


def filter_divmod(a: Any, b: Any) -> tuple[Any, Any]:
    """Division with remainder."""
    return divmod(a, b)


def filter_split(string: str, sep: str = None, maxsplit: int = -1) -> list[str]:
    """Split string."""
    return string.split(sep, maxsplit)


def filter_type(value: Any) -> str:
    """Get the type name of the value."""
    return type(value).__name__


# Registry of builtin filters
PY_WRAPPER_FILTERS = {
    "enumerate": filter_enumerate,
    "zip": filter_zip,
    "range": filter_range,
    "divmod": filter_divmod,
    "splitx": filter_split,
    "type": filter_type,
}