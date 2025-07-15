"""Custom Jinja2 filters for common automation workflows."""

import random
import re
import jmespath
from typing import Any


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
    return [lst[i:i + size] for i in range(0, len(lst), size)]


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
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def to_kebab_case(string: str) -> str:
    """Convert string to kebab-case.

    Example:
        >>> to_kebab_case('MyVariableName')
        'my-variable-name'
    """
    return to_snake_case(string).replace('_', '-')


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


def default_if_none(value: Any, default_value: Any) -> Any:
    """Return default only if value is None.

    Example:
        >>> default_if_none(None, 'fallback')
        'fallback'
        >>> default_if_none('', 'fallback')
        ''
    """
    return default_value if value is None else value


def random_choice(lst: list[Any]) -> Any:
    """Return random item from list.

    Example:
        >>> random_choice([1, 2, 3])  # result may vary
        2
    """
    return random.choice(lst) if lst else None


# Registry of custom filters
CUSTOM_FILTERS = {
    'flatten_list': flatten_list,
    'unique_list': unique_list,
    'chunk_list': chunk_list,
    'regex_replace': regex_replace,
    'to_snake_case': to_snake_case,
    'to_kebab_case': to_kebab_case,
    'json_query': json_query,
    'deep_merge': deep_merge,
    'default_if_none': default_if_none,
    'random_choice': random_choice,
}