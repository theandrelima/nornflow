from unittest.mock import patch

import yaml
import pytest

from nornflow.settings import NornFlowSettings, NONRFLOW_SETTINGS_MANDATORY, NONRFLOW_SETTINGS_OPTIONAL
from nornflow.exceptions import ResourceError, SettingsError, NornFlowError


def make_valid_settings_dict() -> dict[str, object]:
    """Build a minimal valid settings dict using the mandatory keys and optional defaults."""
    data: dict[str, object] = {}
    for idx, key in enumerate(NONRFLOW_SETTINGS_MANDATORY):
        data[key] = f"value_{idx}"
    for opt_key, opt_default in NONRFLOW_SETTINGS_OPTIONAL.items():
        data[opt_key] = opt_default
    return data


def test_successful_load_and_optional_override():
    settings_dict = make_valid_settings_dict()
    opt_keys = list(NONRFLOW_SETTINGS_OPTIONAL.keys())
    override_key = opt_keys[0] if opt_keys else None

    with patch("nornflow.settings.load_file_to_dict", return_value=settings_dict):
        if override_key:
            s = NornFlowSettings(settings_file="ignored", **{override_key: "overridden"})
            assert s.as_dict[override_key] == "overridden"
        else:
            s = NornFlowSettings(settings_file="ignored")
        for k in NONRFLOW_SETTINGS_MANDATORY:
            assert k in s.as_dict
            assert s.as_dict[k] is not None
        sample_key = NONRFLOW_SETTINGS_MANDATORY[0] if NONRFLOW_SETTINGS_MANDATORY else next(iter(s.as_dict))
        assert getattr(s, sample_key) == s.as_dict[sample_key]
        assert isinstance(str(s), str)
        assert sample_key in str(s)


def test_file_not_found_raises_resource_error():
    with patch("nornflow.settings.load_file_to_dict", side_effect=FileNotFoundError()):
        with pytest.raises(ResourceError):
            NornFlowSettings(settings_file="missing.yaml")


def test_permission_error_raises_resource_error():
    with patch("nornflow.settings.load_file_to_dict", side_effect=PermissionError()):
        with pytest.raises(ResourceError):
            NornFlowSettings(settings_file="unreadable.yaml")


def test_yaml_parse_error_raises_settings_error():
    with patch("nornflow.settings.load_file_to_dict", side_effect=yaml.YAMLError("bad yaml")):
        with pytest.raises(SettingsError):
            NornFlowSettings(settings_file="bad.yaml")


def test_load_returns_non_dict_raises_nornflow_error():
    # Current implementation wraps non-dict load result into a NornFlowError
    with patch("nornflow.settings.load_file_to_dict", return_value=["not", "a", "dict"]):
        with pytest.raises(NornFlowError):
            NornFlowSettings(settings_file="weird.yaml")


def test_load_raises_type_error_is_wrapped_as_settings_error():
    with patch("nornflow.settings.load_file_to_dict", side_effect=TypeError("type problem")):
        with pytest.raises(SettingsError):
            NornFlowSettings(settings_file="type.yaml")


def test_missing_mandatory_setting_raises_settings_error():
    if len(NONRFLOW_SETTINGS_MANDATORY) < 1:
        pytest.skip("No mandatory settings defined")
    partial = make_valid_settings_dict()
    missing_key = NONRFLOW_SETTINGS_MANDATORY[0]
    partial.pop(missing_key, None)
    with patch("nornflow.settings.load_file_to_dict", return_value=partial):
        with pytest.raises(SettingsError):
            NornFlowSettings(settings_file="missing_mandatory.yaml")


def test_empty_mandatory_setting_raises_settings_error():
    if len(NONRFLOW_SETTINGS_MANDATORY) < 1:
        pytest.skip("No mandatory settings defined")
    data = make_valid_settings_dict()
    empty_key = NONRFLOW_SETTINGS_MANDATORY[0]
    data[empty_key] = ""
    with patch("nornflow.settings.load_file_to_dict", return_value=data):
        with pytest.raises(SettingsError):
            NornFlowSettings(settings_file="empty_mandatory.yaml")
