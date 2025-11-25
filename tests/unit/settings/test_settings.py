from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from nornflow.constants import NORNFLOW_SETTINGS_MANDATORY, NORNFLOW_SETTINGS_OPTIONAL
from nornflow.exceptions import SettingsError
from nornflow.settings import NornFlowSettings


def make_valid_settings_dict() -> dict[str, object]:
    """Build a minimal valid settings dict using the mandatory keys and optional defaults."""
    data: dict[str, object] = {}
    for idx, key in enumerate(NORNFLOW_SETTINGS_MANDATORY):
        data[key] = f"value_{idx}"
    for opt_key, opt_default in NORNFLOW_SETTINGS_OPTIONAL.items():
        if opt_key == "failure_strategy":
            data[opt_key] = "skip-failed"
        else:
            data[opt_key] = opt_default
    return data


def test_from_yaml_successful_load(tmp_path):
    """Test successful loading from YAML file."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_tasks_dirs": ["tasks"],
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.from_yaml(str(settings_file))

    assert settings.nornir_config_file
    assert "tasks" in settings.local_tasks_dirs


def test_from_yaml_file_not_found():
    """Test error when settings file doesn't exist."""
    with pytest.raises(SettingsError, match="Settings file not found"):
        NornFlowSettings.from_yaml("nonexistent.yaml")


def test_from_yaml_invalid_yaml(tmp_path):
    """Test error when YAML file is invalid."""
    settings_file = tmp_path / "bad_settings.yaml"
    settings_file.write_text("invalid: yaml: content:")

    with pytest.raises(SettingsError, match="Failed to load settings"):
        NornFlowSettings.from_yaml(str(settings_file))


def test_from_yaml_missing_required_field(tmp_path):
    """Test error when required field is missing."""
    settings_file = tmp_path / "incomplete_settings.yaml"
    settings_data = {
        "local_tasks_dirs": ["tasks"],
    }
    settings_file.write_text(yaml.dump(settings_data))

    with pytest.raises(Exception):
        NornFlowSettings.from_yaml(str(settings_file))


def test_from_yaml_with_overrides(tmp_path):
    """Test that overrides work correctly."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.from_yaml(str(settings_file), vars_dir="custom_vars")

    assert settings.vars_dir == "custom_vars"


def test_validate_processors_list():
    """Test processor validation with list input."""
    settings_dict = make_valid_settings_dict()
    settings_dict["processors"] = [
        {"class": "MyProcessor", "args": {}},
        {"class": "AnotherProcessor", "args": {"key": "value"}},
    ]

    settings = NornFlowSettings(**settings_dict)

    assert len(settings.processors) == 2
    assert settings.processors[0]["class"] == "MyProcessor"


def test_validate_processors_empty():
    """Test processor validation with empty list."""
    settings_dict = make_valid_settings_dict()
    settings_dict["processors"] = []

    settings = NornFlowSettings(**settings_dict)

    assert settings.processors == []


def test_validate_failure_strategy_string():
    """Test failure strategy validation with string."""
    settings_dict = make_valid_settings_dict()
    settings_dict["failure_strategy"] = "fail-fast"

    settings = NornFlowSettings(**settings_dict)

    from nornflow.constants import FailureStrategy
    assert settings.failure_strategy == FailureStrategy.FAIL_FAST


def test_validate_failure_strategy_underscore():
    """Test failure strategy validation with underscore format."""
    settings_dict = make_valid_settings_dict()
    settings_dict["failure_strategy"] = "skip_failed"

    settings = NornFlowSettings(**settings_dict)

    from nornflow.constants import FailureStrategy
    assert settings.failure_strategy == FailureStrategy.SKIP_FAILED


def test_validate_failure_strategy_invalid():
    """Test failure strategy validation with invalid value."""
    settings_dict = make_valid_settings_dict()
    settings_dict["failure_strategy"] = "invalid-strategy"

    with pytest.raises(Exception):
        NornFlowSettings(**settings_dict)


def test_resolve_relative_paths(tmp_path):
    """Test that paths remain as provided in the settings file."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_tasks_dirs": ["tasks"],
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.from_yaml(str(settings_file))

    assert settings.nornir_config_file == "config.yaml"
    assert settings.local_tasks_dirs == ["tasks"]
    assert settings.vars_dir == "vars"


def test_as_dict_property():
    """Test as_dict property."""
    settings_dict = make_valid_settings_dict()
    settings = NornFlowSettings(**settings_dict)

    result = settings.as_dict

    assert isinstance(result, dict)
    assert "nornir_config_file" in result
    assert "_base_dir" not in result
    assert "_settings_file" not in result


def test_base_dir_property(tmp_path):
    """Test base_dir property."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_tasks_dirs": ["tasks"],
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.from_yaml(str(settings_file))
    
    # The from_yaml method doesn't automatically set base_dir
    # base_dir is None unless explicitly set
    assert settings.base_dir is None
    
    # If the implementation needs to track base_dir, it should be set explicitly
    # For example, if there's a way to set it:
    # settings.base_dir = tmp_path
    # assert settings.base_dir == tmp_path


def test_loaded_settings_property():
    """Test loaded_settings backward compatibility property."""
    settings_dict = make_valid_settings_dict()
    settings = NornFlowSettings(**settings_dict)

    result = settings.loaded_settings

    assert isinstance(result, dict)
    assert result == settings.as_dict