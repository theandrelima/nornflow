"""Custom Jinja2 filters for common automation workflows."""

import random
import re
from typing import Any

import jmespath
from jinja2 import pass_context
from jinja2.runtime import Context, Undefined


def flatten_list(lst: list[Any]) -> list[Any]:
    """Flatten nested lists.

    Example:
        >>> flatten_list([1, [2, [3, 4]], 5])
        [1, 2, 3, 4, 5]
    """
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def unique_list(lst: list[Any]) -> list[Any]:
    """Remove duplicates while preserving order.

    Example:
        >>> unique_list([1, 2, 2, 3, 1])
        [1, 2, 3]
    """
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def chunk_list(lst: list[Any], size: int) -> list[list[Any]]:
    """Split list into chunks of specified size.

    Example:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def regex_replace(string: str, pattern: str, replacement: str, flags: int = 0) -> str:
    """Advanced regex replacement.

    Example:
        >>> regex_replace('abc123', r'\\d+', 'X')
        'abcX'
    """
    return re.sub(pattern, replacement, string, flags=flags)


def to_snake_case(string: str) -> str:
    """Convert string to snake_case.

    Example:
        >>> to_snake_case('MyVariableName')
        'my_variable_name'
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", string)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_kebab_case(string: str) -> str:
    """Convert string to kebab-case.

    Example:
        >>> to_kebab_case('MyVariableName')
        'my-variable-name'
    """
    return to_snake_case(string).replace("_", "-")


def json_query(data: Any, query: str) -> Any:
    """Query JSON data using JMESPath.

    Example:
        >>> json_query({'a': {'b': 1}}, 'a.b')
        1
    """
    return jmespath.search(query, data)


def deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Example:
        >>> deep_merge({'a': 1, 'b': {'c': 2}}, {'b': {'d': 3}, 'e': 4})
        {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def random_choice(lst: list[Any]) -> Any:
    """Return random item from list.

    Example:
        >>> random_choice([1, 2, 3])  # result may vary
        2
    """
    return random.choice(lst) if lst else None  # noqa: S311


def _resolve_from_context(context: Context, key: str) -> tuple[bool, Any]:
    """Try to resolve a key from Jinja2 context.

    Args:
        context: The Jinja2 runtime context.
        key: The key to look up.

    Returns:
        Tuple of (found, value). If not found, returns (False, None).
    """
    try:
        value = context.resolve(key)

        if isinstance(value, Undefined):
            return (False, None)
        return (True, value)
    except Exception:
        return (False, None)


def _nested_exists(context: Context, path: str) -> bool:
    """Check if a nested path exists in the Jinja2 context.

    Supports dot-separated paths (e.g., 'data.key.subkey').
    Uses Jinja2's context.resolve() for the first key, then traverses nested structures.
    Returns False if any part of the path is missing or inaccessible.

    Args:
        context: The Jinja2 runtime context.
        path: Dot-separated path.

    Returns:
        True if the path exists and the final value is not None, False otherwise.
    """
    if not path:
        return False

    parts = path.split(".")

    found, current = _resolve_from_context(context, parts[0])
    if not found:
        return False

    for part in parts[1:]:
        if current is None:
            return False
        if isinstance(current, dict):
            if part not in current:
                return False
            current = current[part]
        else:
            try:
                current = getattr(current, part)
            except AttributeError:
                return False

    return current is not None


def _nested_exists_in_obj(obj: Any, path: str) -> bool:
    """Check if a nested path exists in an object or dict.

    Supports dot-separated paths (e.g., 'data.key.subkey').
    For dicts, uses key access. For objects, uses attribute access.
    Returns False if any part of the path is missing or inaccessible.

    Args:
        obj: The object or dict to check.
        path: Dot-separated path.

    Returns:
        True if the path exists and the final value is not None, False otherwise.
    """
    if not path:
        return obj is not None

    parts = path.split(".")
    current = obj

    for part in parts:
        if current is None:
            return False
        if isinstance(current, dict):
            if part not in current:
                return False
            current = current[part]
        else:
            try:
                current = getattr(current, part)
            except AttributeError:
                return False

    return current is not None


@pass_context
def is_set(context: Context, value: str) -> bool:
    """Check if a variable is set (not None/undefined) in the Jinja2 context.

    Supports namespace-aware checking with nested paths using dot notation:
    - 'x' or 'x.y.z': Checks in NornFlow default namespace.
    - 'host.x' or 'host.x.y.z': Checks in Nornir host namespace.

    Useful with the 'if' hook for conditional task execution based on variable existence.

    Args:
        context: The Jinja2 runtime context (passed automatically by @pass_context).
        value: The variable path string (e.g., 'my_var', 'host.platform', 'my_var.nested.key').

    Returns:
        True if the variable is set and not None, False otherwise.

    Examples:
        {{ 'my_var' | is_set }}              # True if my_var exists and is not None
        {{ 'my_var.nested.key' | is_set }}   # True if nested path exists
        {{ 'host.name' | is_set }}           # True if host.name exists and is not None
        {{ 'host.data.key' | is_set }}       # True if nested host data exists

        # With 'if' hook:
        tasks:
          - name: deploy_config
            if: "{{ 'backup_completed' | is_set }}"
    """
    if not isinstance(value, str):
        return False

    if value.startswith("host."):
        path = value[5:]
        found, host_obj = _resolve_from_context(context, "host")
        if not found or not host_obj:
            return False
        return _nested_exists_in_obj(host_obj, path)
    return _nested_exists(context, value)


CUSTOM_FILTERS = {
    "flatten_list": flatten_list,
    "unique_list": unique_list,
    "chunk_list": chunk_list,
    "regex_replace": regex_replace,
    "to_snake_case": to_snake_case,
    "to_kebab_case": to_kebab_case,
    "json_query": json_query,
    "deep_merge": deep_merge,
    "random_choice": random_choice,
    "is_set": is_set,
}
