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


def filter_any(iterable: Iterable[Any]) -> bool:
    """Check if any element is truthy."""
    return any(iterable)


def filter_all(iterable: Iterable[Any]) -> bool:
    """Check if all elements are truthy."""
    return all(iterable)


def filter_len(value: Any) -> int:
    """Get the length of the value."""
    return len(value)


def filter_sorted(iterable: Iterable[Any], key: Any = None, reverse: bool = False) -> list[Any]:
    """Return a new sorted list from the iterable."""
    return sorted(iterable, key=key, reverse=reverse)


def filter_reversed(iterable: Iterable[Any]) -> list[Any]:
    """Return a new list with elements in reverse order."""
    return list(reversed(iterable))


def filter_strip(string: str, chars: str | None = None) -> str:
    """Remove leading and trailing whitespace or specified characters."""
    return string.strip(chars)


def filter_join(sep: str, iterable: Iterable[Any]) -> str:
    """Join iterable with separator."""
    return sep.join(str(item) for item in iterable)


def filter_startswith(string: str, prefix: str, start: int = 0, end: int | None = None) -> bool:
    """Check if string starts with prefix, optionally within start and end indices."""
    return string.startswith(prefix, start, end)


# Registry of builtin filters
PY_WRAPPER_FILTERS = {
    "enumerate": filter_enumerate,
    "zip": filter_zip,
    "range": filter_range,
    "divmod": filter_divmod,
    "splitx": filter_split,
    "type": filter_type,
    "any": filter_any,
    "all": filter_all,
    "len": filter_len,
    "sorted": filter_sorted,
    "reversed": filter_reversed,
    "strip": filter_strip,
    "joinx": filter_join,
    "startswith": filter_startswith,
}
