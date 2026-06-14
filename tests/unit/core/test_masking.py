import logging

import pytest

from nornflow.logger import MicrosecondFormatter
from nornflow.masking import (
    LARGE_TEXT_THRESHOLD,
    REDACTED,
    is_sensitive_key,
    mask_for_display,
    mask_structure,
    mask_text,
)


class TestIsSensitiveKey:
    """Tests for is_sensitive_key."""

    def test_exact_keyword_match(self):
        assert is_sensitive_key("password") is True

    def test_exact_keyword_match_case_insensitive(self):
        assert is_sensitive_key("PASSWORD") is True
        assert is_sensitive_key("Token") is True

    def test_segment_match(self):
        """Segment 'token' in 'nautobot_token' triggers match."""
        assert is_sensitive_key("nautobot_token") is True

    def test_segment_match_api_key(self):
        assert is_sensitive_key("api_key") is True

    def test_compound_keyword_exact_match(self):
        """db_connection_string has no segment atom; listed as an exact-only compound."""
        assert is_sensitive_key("db_connection_string") is True

    def test_segment_atoms_cover_former_compounds(self):
        """Segment atoms replace redundant compound PROTECTED_KEYWORDS entries."""
        assert is_sensitive_key("config_token") is True
        assert is_sensitive_key("client_secret") is True
        assert is_sensitive_key("encryption_key") is True
        assert is_sensitive_key("db_pass") is True
        assert is_sensitive_key("verification_code") is True
        assert is_sensitive_key("aws_secret_access_key") is True

    def test_no_false_positive_monkey(self):
        """'monkey' must not match keyword 'key' — segment 'monkey' != 'key'."""
        assert is_sensitive_key("monkey") is False

    def test_no_false_positive_identity_provider_url(self):
        """Segment 'identity' IS in PROTECTED_KEYWORDS, so this correctly matches."""
        assert is_sensitive_key("identity_provider_url") is True

    def test_no_match_hostname(self):
        assert is_sensitive_key("hostname") is False

    def test_no_match_description(self):
        assert is_sensitive_key("description") is False

    def test_hyphen_normalized(self):
        """Hyphens are normalized to underscores before matching."""
        assert is_sensitive_key("api-token") is True

    def test_dot_normalized(self):
        assert is_sensitive_key("auth.token") is True

    def test_sensitive_names_exact_match(self):
        names = frozenset(["vault_pin"])
        assert is_sensitive_key("vault_pin", names) is True
        assert is_sensitive_key("vault_pin") is False

    def test_sensitive_names_segment_match(self):
        """User sensitive_names use the same segment-aware rule as built-in keywords."""
        names = frozenset(["pin"])
        assert is_sensitive_key("vault_pin", names) is True
        assert is_sensitive_key("pin", names) is True
        assert is_sensitive_key("spin", names) is False


class TestMaskText:
    """Tests for mask_text."""

    def test_masks_key_equals_value(self):
        result = mask_text("password=supersecret")
        assert "supersecret" not in result
        assert REDACTED in result

    def test_masks_key_colon_value(self):
        result = mask_text("token: abc123")
        assert "abc123" not in result
        assert REDACTED in result

    def test_masks_quoted_value(self):
        result = mask_text('api_key = "mykey"')
        assert "mykey" not in result
        assert REDACTED in result

    def test_does_not_mask_non_sensitive(self):
        original = "hostname = router1"
        assert mask_text(original) == original

    def test_does_not_redact_substring_key_false_positive(self):
        """Segment keyword 'key' must not match inside 'monkey='."""
        assert mask_text("monkey=abc") == "monkey=abc"

    def test_reveal_returns_unchanged(self):
        text = "password=topsecret"
        assert mask_text(text, reveal=True) == text

    def test_non_string_returned_as_is(self):
        assert mask_text(42) == 42  # type: ignore[arg-type]
        assert mask_text(None) is None  # type: ignore[arg-type]

    def test_empty_string(self):
        assert mask_text("") == ""

    def test_multiple_secrets_in_one_string(self):
        result = mask_text("password=abc token=xyz hostname=router1")
        assert "abc" not in result
        assert "xyz" not in result
        assert "router1" in result
        assert result.count(REDACTED) == 2

    def test_large_string_without_keywords_skips_regex(self):
        """Large blobs with no protected keywords return unchanged."""
        text = "x" * (LARGE_TEXT_THRESHOLD + 1000)
        assert mask_text(text) == text

    def test_large_string_with_keyword_still_masks(self):
        text = "x" * LARGE_TEXT_THRESHOLD + " password=leaked_secret"
        result = mask_text(text)
        assert "leaked_secret" not in result
        assert REDACTED in result

    def test_masks_hyphenated_key_in_text(self):
        result = mask_text("db-connection-string=supersecret")
        assert "supersecret" not in result
        assert REDACTED in result

    def test_masks_dotted_key_in_text(self):
        result = mask_text("api.key=supersecret")
        assert "supersecret" not in result
        assert REDACTED in result

    def test_large_string_with_hyphenated_keyword_still_masks(self):
        text = "x" * LARGE_TEXT_THRESHOLD + " db-connection-string=leaked_secret"
        result = mask_text(text)
        assert "leaked_secret" not in result
        assert REDACTED in result

    def test_masks_user_sensitive_name_in_text(self):
        names = frozenset(["credential_x"])
        result = mask_text("credential_x=not-in-protected-keywords", sensitive_names=names)
        assert "not-in-protected-keywords" not in result
        assert REDACTED in result

    def test_large_string_with_sensitive_name_still_masks(self):
        names = frozenset(["credential_x"])
        text = "x" * LARGE_TEXT_THRESHOLD + " credential_x=leaked_secret"
        result = mask_text(text, sensitive_names=names)
        assert "leaked_secret" not in result
        assert REDACTED in result


class TestMicrosecondFormatter:
    """Tests for log formatter masking."""

    def test_format_masks_sensitive_message(self):
        formatter = MicrosecondFormatter("%(message)s")
        record = logging.LogRecord(
            name="nornflow",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="password=secret123",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "secret123" not in result
        assert REDACTED in result

    def test_format_skips_redaction_when_disabled(self):
        formatter = MicrosecondFormatter("%(message)s", redaction_enabled=False)
        record = logging.LogRecord(
            name="nornflow",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="password=secret123",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "secret123" in result
        assert REDACTED not in result

    def test_format_masks_user_sensitive_name(self):
        names = frozenset(["credential_x"])
        formatter = MicrosecondFormatter("%(message)s", sensitive_names=names)
        record = logging.LogRecord(
            name="nornflow",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="credential_x=lab-secret",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "lab-secret" not in result
        assert REDACTED in result

    def test_format_masks_interpolated_args(self):
        """Redact secrets passed as logging format args after interpolation."""
        formatter = MicrosecondFormatter("%(message)s")
        record = logging.LogRecord(
            name="nornflow",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="password=%s",
            args=("secret123",),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "secret123" not in result
        assert REDACTED in result

    def test_format_does_not_mutate_log_record(self):
        formatter = MicrosecondFormatter("%(message)s")
        record = logging.LogRecord(
            name="nornflow",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="password=%s",
            args=("secret123",),
            exc_info=None,
        )
        formatter.format(record)
        assert record.msg == "password=%s"
        assert record.args == ("secret123",)


class TestMaskStructure:
    """Tests for mask_structure."""

    def test_flat_dict_sensitive_key(self):
        data = {"password": "secret123", "hostname": "router1"}
        result = mask_structure(data)
        assert result["password"] == REDACTED
        assert result["hostname"] == "router1"

    def test_nested_dict_sensitive_key(self):
        """Phase 1 acceptance criterion: nautobot_token in nested options dict."""
        data = {
            "inventory": {
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://localhost:8080",
                    "nautobot_token": "3ff4118f836dfa3c2fc1b4bc0db7afccfb87dcd3",
                },
            }
        }
        result = mask_structure(data)
        assert result["inventory"]["options"]["nautobot_token"] == REDACTED
        assert result["inventory"]["options"]["nautobot_url"] == "http://localhost:8080"
        assert result["inventory"]["plugin"] == "NautobotInventory"

    def test_does_not_mutate_input(self):
        data = {"password": "secret", "name": "alice"}
        original_value = data["password"]
        mask_structure(data)
        assert data["password"] == original_value

    def test_list_of_dicts(self):
        data = [{"token": "abc"}, {"hostname": "router1"}]
        result = mask_structure(data)
        assert result[0]["token"] == REDACTED
        assert result[1]["hostname"] == "router1"

    def test_tuple_passthrough(self):
        data = ({"secret": "x"}, "plain")
        result = mask_structure(data)
        assert isinstance(result, tuple)
        assert result[0]["secret"] == REDACTED
        assert result[1] == "plain"

    def test_scalar_passthrough(self):
        assert mask_structure("just a string") == "just a string"
        assert mask_structure(42) == 42
        assert mask_structure(None) is None

    def test_reveal_returns_unchanged(self):
        data = {"password": "secret"}
        assert mask_structure(data, reveal=True) is data

    def test_sensitive_names(self):
        names = frozenset(["vault_pin"])
        data = {"vault_pin": "1234", "name": "test"}
        result = mask_structure(data, sensitive_names=names)
        assert result["vault_pin"] == REDACTED
        assert result["name"] == "test"

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": {"password": "deep_secret", "ok": "visible"}}}}
        result = mask_structure(data)
        assert result["a"]["b"]["c"]["password"] == REDACTED
        assert result["a"]["b"]["c"]["ok"] == "visible"

    def test_empty_dict(self):
        assert mask_structure({}) == {}

    def test_empty_list(self):
        assert mask_structure([]) == []

    def test_non_sensitive_dict_unchanged(self):
        data = {"hostname": "r1", "platform": "ios", "port": 22}
        assert mask_structure(data) == data


class TestMaskForDisplay:
    """Tests for mask_for_display (the public entry point)."""

    def test_dict_dispatches_to_structure(self):
        data = {"api_token": "secret", "name": "test"}
        result = mask_for_display(data)
        assert result["api_token"] == REDACTED
        assert result["name"] == "test"

    def test_list_dispatches_to_structure(self):
        data = [{"password": "x"}, {"ok": "y"}]
        result = mask_for_display(data)
        assert result[0]["password"] == REDACTED
        assert result[1]["ok"] == "y"

    def test_str_dispatches_to_mask_text(self):
        result = mask_for_display("token=abcdef")
        assert "abcdef" not in result
        assert REDACTED in result

    def test_int_passthrough(self):
        assert mask_for_display(42) == 42

    def test_none_passthrough(self):
        assert mask_for_display(None) is None

    def test_reveal_fast_path(self):
        data = {"password": "secret"}
        assert mask_for_display(data, reveal=True) is data

    def test_sensitive_names_on_all_surfaces(self):
        names = frozenset(["credential_x"])
        assert mask_for_display({"credential_x": "secret"}, sensitive_names=names)["credential_x"] == REDACTED
        assert "secret" not in mask_for_display("credential_x=secret", sensitive_names=names)

    def test_nornir_config_acceptance_criterion(self):
        """
        Acceptance criterion from the arch doc:
        nornflow show --nornir-configs must never print the literal token value.
        """
        nornir_cfg = {
            "inventory": {
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://localhost:8080",
                    "nautobot_token": "3ff4118f836dfa3c2fc1b4bc0db7afccfb87dcd3",
                },
            },
            "runner": {
                "plugin": "threaded",
                "options": {"num_workers": 5},
            },
            "logging": {"level": "DEBUG"},
        }
        result = mask_for_display(nornir_cfg)
        assert result["inventory"]["options"]["nautobot_token"] == REDACTED
        assert result["inventory"]["options"]["nautobot_url"] == "http://localhost:8080"
        assert result["runner"]["options"]["num_workers"] == 5
        assert result["logging"]["level"] == "DEBUG"
        assert "3ff4118f836dfa3c2fc1b4bc0db7afccfb87dcd3" not in str(result)
