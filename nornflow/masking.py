"""
Centralized output masking for NornFlow.

All user-facing output paths (CLI tables, workflow overview, log formatters( must
pass data through this module before rendering. In-memory runtime objects are never
masked here; masking applies only at display and log boundaries.

Three public entry points cover all output sinks:
- mask_for_display: top-level entry point; dispatches by type.
- mask_structure:   recursive key-based redaction for dicts / lists / tuples.
- mask_text:        regex-based best-effort redaction for unstructured strings.
"""

import re
from typing import Any

from nornflow.constants import PROTECTED_KEYWORDS

REDACTED = "***REDACTED***"

# Frozenset for O(1) lookup; normalized to lowercase once at import time.
_KEYWORDS_SET: frozenset[str] = frozenset(kw.lower() for kw in PROTECTED_KEYWORDS)


def _get_mask_text_pattern() -> re.Pattern:
    """Get or lazily build the compiled regex for text-based sensitive data detection."""
    if not hasattr(_get_mask_text_pattern, "_pattern"):
        keywords = "|".join(re.escape(kw) for kw in PROTECTED_KEYWORDS)
        _get_mask_text_pattern._pattern = re.compile(  # noqa: SLF001
            rf"({keywords})(\s*[:=]\s*)(['\"]?)(\S+?)(\3)(?=\s|,|}}|\]|$)", re.IGNORECASE
        )

    return _get_mask_text_pattern._pattern  # noqa: SLF001


def is_sensitive_key(key: str, extra_keywords: frozenset[str] | None = None) -> bool:
    """Return True if a key name is considered sensitive under the masking policy.

    Uses segment-aware matching to avoid false positives from naive substring
    checks (e.g. 'key' must not match inside 'monkey'):

    1. Normalize the key (lowercase, hyphens and dots → underscores).
    2. Exact match: the normalized full key equals a keyword in the set
       (catches compound keywords like 'db_connection_string').
    3. Segment match: any individual segment produced by splitting on '_'
       equals a keyword in the set (catches 'nautobot_token' via 'token').

    Args:
        key: The key name to evaluate.
        extra_keywords: Optional additional keywords to include (user-configured).

    Returns:
        True if the key is considered sensitive.
    """
    normalized = key.lower().replace("-", "_").replace(".", "_")
    keywords = _KEYWORDS_SET
    if extra_keywords:
        keywords = keywords | frozenset(kw.lower() for kw in extra_keywords)

    if normalized in keywords:
        return True

    return any(segment in keywords for segment in normalized.split("_") if segment)


def mask_text(text: str, *, reveal: bool = False) -> str:
    """Redact sensitive key=value / key: value patterns from an unstructured string.

    Regex-based best-effort pass suitable for log lines, task output, and error
    messages. Does not guarantee full coverage of all possible secret representations
    (e.g. bare values without a key prefix are not caught).

    Args:
        text: The string to sanitize.
        reveal: If True, return the string unchanged (zero processing).

    Returns:
        String with sensitive values replaced by REDACTED, or the original string
        if reveal is True or input is not a str.
    """
    if reveal or not isinstance(text, str):
        return text
    return _get_mask_text_pattern().sub(rf"\1\2\3{REDACTED}\5", text)


def mask_structure(
    data: Any,
    *,
    reveal: bool = False,
    extra_keywords: frozenset[str] | None = None,
) -> Any:
    """Recursively walk a dict / list / tuple and redact values whose keys are sensitive.

    Produces a new container (shallow copies of dicts / lists / tuples, replacing only
    the redacted leaves). Input objects are never mutated.

    For dict values whose key matches the sensitivity policy, the value is replaced by
    REDACTED regardless of its type. Non-sensitive dict values and all list / tuple
    elements are recursed into.

    Args:
        data: The data structure to mask.
        reveal: If True, return data unchanged.
        extra_keywords: Optional additional keywords beyond PROTECTED_KEYWORDS.

    Returns:
        A new structure with sensitive leaf values replaced by REDACTED.
    """
    if reveal:
        return data

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if is_sensitive_key(str(key), extra_keywords):
                result[key] = REDACTED
            else:
                result[key] = mask_structure(value, reveal=reveal, extra_keywords=extra_keywords)
        return result

    if isinstance(data, list):
        return [mask_structure(item, reveal=reveal, extra_keywords=extra_keywords) for item in data]

    if isinstance(data, tuple):
        return tuple(
            mask_structure(item, reveal=reveal, extra_keywords=extra_keywords) for item in data
        )

    return data


def mask_for_display(
    data: Any,
    *,
    reveal: bool = False,
    extra_keywords: frozenset[str] | None = None,
) -> Any:
    """Mask data before any user-facing rendering.

    Dispatches by type:
    - dict / list / tuple  → structural key-based redaction via mask_structure.
    - str                  → regex-based text redaction via mask_text.
    - anything else        → returned as-is.

    This is the preferred entry point for all display sinks. In-memory runtime objects
    (e.g. nornflow.nornir_configs used by tasks) must NOT be passed here; call only
    when about to render to terminal, log file, or panel.

    Args:
        data: The data to mask.
        reveal: If True, return data completely unchanged (zero processing fast path).
        extra_keywords: Optional additional keywords beyond PROTECTED_KEYWORDS.

    Returns:
        Masked version of data, safe for display.
    """
    if reveal:
        return data

    if isinstance(data, dict | list | tuple):
        return mask_structure(data, extra_keywords=extra_keywords)

    if isinstance(data, str):
        return mask_text(data)

    return data
