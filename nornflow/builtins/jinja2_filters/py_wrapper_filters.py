"""Python builtin functions wrapped as Jinja2 filters."""

from typing import Any, Iterable


def filter_max(sequence: Iterable[Any], default: Any = None, key: Any = None) -> Any:
    """Get maximum value from sequence."""
    if default is not None:
        return max(sequence, default=default, key=key)
    return max(sequence, key=key) if key else max(sequence)


def filter_min(sequence: Iterable[Any], default: Any = None, key: Any = None) -> Any:
    """Get minimum value from sequence.""" 
    if default is not None:
        return min(sequence, default=default, key=key)
    return min(sequence, key=key) if key else min(sequence)


def filter_any(iterable: Iterable[Any]) -> bool:
    """Test if any element is truthy."""
    return any(iterable)


def filter_all(iterable: Iterable[Any]) -> bool:
    """Test if all elements are truthy."""
    return all(iterable)


def filter_len(obj: Any) -> int:
    """Get length of object."""
    return len(obj)


def filter_sum(iterable: Iterable[Any], start: Any = 0) -> Any:
    """Sum numeric values."""
    return sum(iterable, start)


def filter_sorted(iterable: Iterable[Any], key: Any = None, reverse: bool = False) -> list[Any]:
    """Sort sequence."""
    return sorted(iterable, key=key, reverse=reverse)


def filter_reversed(sequence: Iterable[Any]) -> list[Any]:
    """Reverse sequence."""
    return list(reversed(sequence))


def filter_enumerate(iterable: Iterable[Any], start: int = 0) -> list[tuple[int, Any]]:
    """Get index-value pairs."""
    return list(enumerate(iterable, start))


def filter_zip(*iterables: Iterable[Any]) -> list[tuple[Any, ...]]:
    """Combine sequences."""
    return list(zip(*iterables))


def filter_range(*args: int) -> list[int]:
    """Generate number sequence."""
    return list(range(*args))


def filter_abs(number: Any) -> Any:
    """Get absolute value."""
    return abs(number)


def filter_round(number: float, ndigits: int = 0) -> float:
    """Round number."""
    return round(number, ndigits)


def filter_divmod(a: Any, b: Any) -> tuple[Any, Any]:
    """Division with remainder."""
    return divmod(a, b)


def filter_upper(string: str) -> str:
    """Convert to uppercase."""
    return string.upper()


def filter_lower(string: str) -> str:
    """Convert to lowercase."""
    return string.lower()


def filter_title(string: str) -> str:
    """Convert to title case."""
    return string.title()


def filter_strip(string: str, chars: str = None) -> str:
    """Remove whitespace or specified characters."""
    return string.strip(chars)


def filter_split(string: str, sep: str = None, maxsplit: int = -1) -> list[str]:
    """Split string."""
    return string.split(sep, maxsplit)


def filter_join(separator: str, iterable: Iterable[str]) -> str:
    """Join sequence with separator."""
    return separator.join(iterable)


# Registry of builtin filters
PY_WRAPPER_FILTERS = {
    'max': filter_max,
    'min': filter_min,
    'any': filter_any,
    'all': filter_all,
    'len': filter_len,
    'sum': filter_sum,
    'sorted': filter_sorted,
    'reversed': filter_reversed,
    'enumerate': filter_enumerate,
    'zip': filter_zip,
    'range': filter_range,
    'abs': filter_abs,
    'round': filter_round,
    'divmod': filter_divmod,
    'upper': filter_upper,
    'lower': filter_lower,
    'title': filter_title,
    'strip': filter_strip,
    'split': filter_split,
    'join': filter_join,
}