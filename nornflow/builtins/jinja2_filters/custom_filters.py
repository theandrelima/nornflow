"""Custom Jinja2 filters for common automation workflows."""

import random
import re
from typing import Any

import jmespath
from jinja2 import pass_context


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


@pass_context
def is_set(context: dict[str, Any], value: str) -> bool:
    """
    Check if a variable is set (not None/undefined) in the current Jinja2 context.

    Supports namespace-aware checking:
    - 'x': Checks in NornFlow default namespace (context['x'])
    - 'host.x': Checks in Nornir host namespace (context['host'].x or context['host']['x'])

    This filter is particularly useful with the 'if' hook for conditional task execution
    based on variable existence, allowing workflows to adapt dynamically to runtime state.

    Args:
        context: The Jinja2 context dictionary (passed via @pass_context).
        value: The variable path string to check (e.g., 'my_var' or 'host.platform').

    Returns:
        True if the variable is set and not None, False otherwise.

    Examples:
        Basic usage in Jinja2 expressions:

        {{ 'my_var' | is_set }}          # True if my_var exists and is not None
        {{ 'host.name' | is_set }}       # True if host.name exists and is not None

        Usage with the 'if' hook for conditional task execution:

        # Skip task if a required variable is not set
        tasks:
          - name: deploy_config
            if: "{{ 'backup_completed' | is_set }}"
            # Task only runs if 'backup_completed' variable exists and is not None

        # Check host-specific data before running task
        tasks:
          - name: ios_upgrade
            if: "{{ 'host.ios_version' | is_set }}"
            # Task only runs on hosts where ios_version is defined

        # Combine with other conditions using Jinja2 logic
        tasks:
          - name: security_scan
            if: "{{ ('host.platform' | is_set) and ('scan_enabled' | is_set) }}"
            # Task runs only if both host.platform and scan_enabled are set

        # Use in complex expressions with defaults
        tasks:
          - name: conditional_backup
            if: "{{ 'force_backup' | is_set or 'host.needs_backup' | is_set }}"
            # Task runs if either force_backup OR host.needs_backup is set
    """
    if not isinstance(value, str):
        return False

    # Split on first dot to separate namespace from key
    parts = value.split(".", 1)
    if len(parts) == 1:
        # No namespace specified, check NornFlow default namespace
        var_name = parts[0]
        return var_name in context and context[var_name] is not None
    # Namespace specified
    namespace, var_name = parts
    if namespace == "host":
        # Check Nornir host namespace
        host_obj = context.get("host")
        if host_obj is None:
            return False
        # Try attribute access first, then dict access
        try:
            val = getattr(host_obj, var_name, None)
            return val is not None
        except AttributeError:
            # Fallback to dict-like access if host supports it
            return (
                hasattr(host_obj, "__getitem__") and var_name in host_obj and host_obj[var_name] is not None
            )
    else:
        # Unknown namespace, treat as not set
        return False


# Registry of custom filters
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
