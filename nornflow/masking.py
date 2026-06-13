"""
Centralized output masking for NornFlow.

All user-facing output paths (CLI tables, workflow overview, log formatters) must
pass data through this module before rendering. In-memory runtime objects are never
masked here; masking applies only at display and log boundaries.

Key-name policy merges built-in 'PROTECTED_KEYWORDS' with user
'redaction.sensitive_names' and applies one segment-aware rule to both:
normalize the key, then match the full name or any '_'-delimited segment.

Three public entry points cover all output sinks:
- mask_for_display: top-level entry point; dispatches by type.
- mask_structure:   recursive key-based redaction for dicts / lists / tuples.
- mask_text:        regex-based best-effort redaction for unstructured strings.
"""

import re
from typing import Any

from nornflow.constants import LARGE_TEXT_THRESHOLD, PROTECTED_KEYWORDS, REDACTED

# Frozenset for O(1) lookup; normalized to lowercase once at import time.
_KEYWORDS_SET: frozenset[str] = frozenset(kw.lower() for kw in PROTECTED_KEYWORDS)

_MASK_TEXT_PATTERNS: dict[frozenset[str], re.Pattern[str]] = {}


def _normalize_identifier(name: str) -> str:
    """Normalize a key or identifier for sensitivity comparison."""
    return name.lower().replace("-", "_").replace(".", "_")


def _effective_keywords(sensitive_names: frozenset[str] | None = None) -> frozenset[str]:
    """Built-in and user keywords merged for a single matching policy."""
    if sensitive_names:
        return _KEYWORDS_SET | sensitive_names
    return _KEYWORDS_SET


def _get_mask_text_pattern(sensitive_names: frozenset[str] | None = None) -> re.Pattern[str]:
    """Get or lazily build the compiled regex for text-based sensitive data detection.

    Args:
        sensitive_names: Optional user-declared identifiers to include in the regex.

    Returns:
        Compiled pattern matching 'key=value' and 'key: value' forms.
    """
    cache_key = sensitive_names or frozenset()
    if cache_key not in _MASK_TEXT_PATTERNS:
        keywords = list(PROTECTED_KEYWORDS)
        if sensitive_names:
            keywords.extend(sorted(sensitive_names))
        alternation = "|".join(re.escape(kw) for kw in keywords)
        _MASK_TEXT_PATTERNS[cache_key] = re.compile(
            rf"({alternation})(\s*[:=]\s*)(['\"]?)(\S+?)(\3)(?=\s|,|}}|\]|$)", re.IGNORECASE
        )
    return _MASK_TEXT_PATTERNS[cache_key]


def is_sensitive_key(key: str, sensitive_names: frozenset[str] | None = None) -> bool:
    """Return True if a key name is considered sensitive under the masking policy.

    Uses segment-aware matching for built-in 'PROTECTED_KEYWORDS' and user
    'sensitive_names' alike:

    1. Normalize the key (lowercase, hyphens and dots → underscores).
    2. Exact match: the normalized full key equals a keyword.
    3. Segment match: any '_'-delimited segment equals a keyword
       (e.g. 'token' matches 'nautobot_token'; user 'pin' matches 'vault_pin').

    Args:
        key: The key name to evaluate.
        sensitive_names: Optional user-configured identifiers from settings.

    Returns:
        True if the key is considered sensitive.
    """
    normalized = _normalize_identifier(key)
    keywords = _effective_keywords(sensitive_names)

    if normalized in keywords:
        return True

    return any(segment in keywords for segment in normalized.split("_") if segment)


def mask_text(
    text: str,
    *,
    reveal: bool = False,
    sensitive_names: frozenset[str] | None = None,
) -> str:
    """Redact sensitive key=value / key: value patterns from an unstructured string.

    Regex-based best-effort pass suitable for log lines, task output, and error
    messages. Matches built-in 'PROTECTED_KEYWORDS' and user 'sensitive_names'.

    Args:
        text: The string to sanitize.
        reveal: If True, return the string unchanged (zero processing).
        sensitive_names: Optional user-declared identifiers to include in the regex.

    Returns:
        String with sensitive values replaced by REDACTED, or the original string
        if reveal is True or input is not a str.
    """
    if reveal or not isinstance(text, str) or not text:
        return text

    if len(text) >= LARGE_TEXT_THRESHOLD and not _text_may_contain_secrets(text, sensitive_names):
        return text

    return _get_mask_text_pattern(sensitive_names).sub(rf"\1\2\3{REDACTED}\5", text)


def _text_may_contain_secrets(text: str, sensitive_names: frozenset[str] | None = None) -> bool:
    """Cheap pre-check: True if any keyword appears as a substring."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in _effective_keywords(sensitive_names))


def mask_structure(
    data: Any,
    *,
    reveal: bool = False,
    sensitive_names: frozenset[str] | None = None,
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
        sensitive_names: Optional user-configured identifiers from settings.

    Returns:
        A new structure with sensitive leaf values replaced by REDACTED.
    """
    if reveal:
        return data

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if is_sensitive_key(str(key), sensitive_names):
                result[key] = REDACTED
            else:
                result[key] = mask_structure(value, reveal=reveal, sensitive_names=sensitive_names)
        return result

    if isinstance(data, list):
        return [mask_structure(item, reveal=reveal, sensitive_names=sensitive_names) for item in data]

    if isinstance(data, tuple):
        return tuple(
            mask_structure(item, reveal=reveal, sensitive_names=sensitive_names) for item in data
        )

    return data


def mask_for_display(
    data: Any,
    *,
    reveal: bool = False,
    sensitive_names: frozenset[str] | None = None,
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
        sensitive_names: Optional user-configured identifiers from settings.

    Returns:
        Masked version of data, safe for display.
    """
    if reveal:
        return data

    if isinstance(data, dict | list | tuple):
        return mask_structure(data, sensitive_names=sensitive_names)

    if isinstance(data, str):
        return mask_text(data, sensitive_names=sensitive_names)

    return data
