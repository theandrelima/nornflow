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


def test_settings_load_successful_load(tmp_path):
    """Load from YAML and ensure core values are populated."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_tasks": ["tasks"],
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.load(str(settings_file))

    assert settings.nornir_config_file == str(tmp_path / "config.yaml")
    assert settings.local_tasks == [str(tmp_path / "tasks")]
    assert settings.vars_dir == str(tmp_path / "vars")


def test_settings_load_file_not_found():
    """Test error when settings file doesn't exist."""
    with pytest.raises(SettingsError, match="Settings file not found"):
        NornFlowSettings.load("nonexistent.yaml")


def test_settings_load_invalid_yaml(tmp_path):
    """Test error when YAML file is invalid."""
    settings_file = tmp_path / "bad_settings.yaml"
    settings_file.write_text("invalid: yaml: content:")

    with pytest.raises(SettingsError, match="Failed to load settings"):
        NornFlowSettings.load(str(settings_file))


def test_settings_load_missing_required_field(tmp_path):
    """Test error when required field is missing."""
    settings_file = tmp_path / "incomplete_settings.yaml"
    settings_data = {
        "local_tasks": ["tasks"],
    }
    settings_file.write_text(yaml.dump(settings_data))

    with pytest.raises(Exception):
        NornFlowSettings.load(str(settings_file))


def test_settings_load_with_overrides(tmp_path):
    """Ensure overrides passed to load() are respected."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.load(str(settings_file), vars_dir="custom_vars")

    assert settings.vars_dir == str(tmp_path / "custom_vars")


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


def test_relative_paths_resolved_via_load(tmp_path):
    """Resolve all relative directories against the settings file location."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_tasks": ["tasks", "nested/tasks"],
        "local_workflows": ["workflows"],
        "local_filters": ["filters"],
        "local_hooks": ["hooks"],
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.load(str(settings_file))

    assert settings.nornir_config_file == str(tmp_path / "config.yaml")
    assert settings.local_tasks == [
        str(tmp_path / "tasks"),
        str(tmp_path / "nested/tasks"),
    ]
    assert settings.local_workflows == [str(tmp_path / "workflows")]
    assert settings.local_filters == [str(tmp_path / "filters")]
    assert settings.local_hooks == [str(tmp_path / "hooks")]
    assert settings.vars_dir == str(tmp_path / "vars")


def test_paths_remain_unresolved_with_direct_instantiation():
    """Direct instantiation leaves incoming paths untouched."""
    settings_dict = make_valid_settings_dict()
    settings_dict["nornir_config_file"] = "config.yaml"
    settings_dict["local_tasks"] = ["tasks"]
    settings_dict["vars_dir"] = "vars"

    settings = NornFlowSettings(**settings_dict)

    assert settings.nornir_config_file == "config.yaml"
    assert settings.local_tasks == ["tasks"]
    assert settings.vars_dir == "vars"


def test_absolute_paths_remain_unchanged(tmp_path):
    """Absolute input paths should not be modified."""
    settings_file = tmp_path / "test_settings.yaml"
    abs_tasks_dir = "/absolute/path/to/tasks"
    settings_data = {
        "nornir_config_file": "/absolute/config.yaml",
        "local_tasks": [abs_tasks_dir],
        "vars_dir": "/absolute/vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.load(str(settings_file))

    assert settings.nornir_config_file == "/absolute/config.yaml"
    assert settings.local_tasks == [abs_tasks_dir]
    assert settings.vars_dir == "/absolute/vars"


def test_as_dict_property():
    """Test as_dict property."""
    settings_dict = make_valid_settings_dict()
    settings = NornFlowSettings(**settings_dict)

    result = settings.as_dict

    assert isinstance(result, dict)
    assert "nornir_config_file" in result
    assert "_base_dir" not in result
    assert "_settings_file" not in result


def test_base_dir_property_set_when_loaded(tmp_path):
    """Loading from disk sets base_dir to the settings file directory."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_tasks": ["tasks"],
        "vars_dir": "vars",
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.load(str(settings_file))

    assert settings.base_dir == tmp_path


def test_base_dir_property_none_with_direct_instantiation():
    """Direct instantiation leaves base_dir unset."""
    settings_dict = make_valid_settings_dict()
    settings = NornFlowSettings(**settings_dict)

    assert settings.base_dir is None


def test_loaded_settings_property():
    """Test loaded_settings backward compatibility property."""
    settings_dict = make_valid_settings_dict()
    settings = NornFlowSettings(**settings_dict)

    result = settings.loaded_settings

    assert isinstance(result, dict)
    assert result == settings.as_dict


def test_local_blueprints_default_value():
    """Test local_blueprints default value."""
    settings_dict = make_valid_settings_dict()
    settings = NornFlowSettings(**settings_dict)

    assert settings.local_blueprints == ["blueprints"]


def test_local_blueprints_single_directory(tmp_path):
    """Test local_blueprints with single custom directory."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_blueprints": ["custom_blueprints"],
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.load(str(settings_file))

    assert settings.local_blueprints == [str(tmp_path / "custom_blueprints")]


def test_local_blueprints_multiple_directories(tmp_path):
    """Test local_blueprints with multiple directories."""
    settings_file = tmp_path / "test_settings.yaml"
    settings_data = {
        "nornir_config_file": "config.yaml",
        "local_blueprints": ["blueprints1", "blueprints2"],
    }
    settings_file.write_text(yaml.dump(settings_data))

    settings = NornFlowSettings.load(str(settings_file))

    assert len(settings.local_blueprints) == 2
    assert str(tmp_path / "blueprints1") in settings.local_blueprints
    assert str(tmp_path / "blueprints2") in settings.local_blueprints


class TestRedactionSettings:
    """Tests for the redaction configuration field and redaction_enabled property."""

    def test_redaction_default(self):
        """redaction defaults to enabled=True."""
        settings_dict = make_valid_settings_dict()
        settings = NornFlowSettings(**settings_dict)

        assert settings.redaction == {"enabled": True, "logs_enabled": True}
        assert settings.redaction_enabled is True
        assert settings.redaction_logs_enabled is True

    def test_redaction_disabled_via_dict(self):
        """redaction.enabled can be set to False."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = {"enabled": False}
        settings = NornFlowSettings(**settings_dict)

        assert settings.redaction["enabled"] is False
        assert settings.redaction_enabled is False

    def test_redaction_partial_override_merges_defaults(self):
        """An empty redaction dict is valid and merges with defaults."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = {}
        settings = NornFlowSettings(**settings_dict)

        assert settings.redaction == {"enabled": True, "logs_enabled": True}

    def test_redaction_not_a_dict_raises(self):
        """Non-dict redaction value must raise SettingsError."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = "true"

        with pytest.raises(Exception):
            NornFlowSettings(**settings_dict)

    def test_redaction_enabled_non_bool_raises(self):
        """A non-bool enabled must raise SettingsError."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = {"enabled": "yes"}

        with pytest.raises(Exception):
            NornFlowSettings(**settings_dict)

    def test_redaction_loaded_from_yaml(self, tmp_path):
        """redaction.enabled can be set via YAML file."""
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(yaml.dump({"nornir_config_file": "c.yaml", "redaction": {"enabled": False}}))

        settings = NornFlowSettings.load(str(settings_file))

        assert settings.redaction_enabled is False
        assert settings.redaction_logs_enabled is False

    def test_logs_enabled_inherits_enabled_when_omitted(self):
        """logs_enabled follows enabled when not set explicitly."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = {"enabled": False}
        settings = NornFlowSettings(**settings_dict)

        assert settings.redaction["logs_enabled"] is False
        assert settings.redaction_logs_enabled is False

    def test_logs_enabled_explicit_override(self):
        """logs_enabled can differ from enabled when set explicitly."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = {"enabled": True, "logs_enabled": False}
        settings = NornFlowSettings(**settings_dict)

        assert settings.redaction_enabled is True
        assert settings.redaction_logs_enabled is False

    def test_redaction_unknown_key_raises(self):
        """Unknown keys under redaction must raise SettingsError."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = {"enabled": True, "extra": True}

        with pytest.raises(Exception):
            NornFlowSettings(**settings_dict)

    def test_redaction_logs_enabled_non_bool_raises(self):
        """A non-bool logs_enabled must raise SettingsError."""
        settings_dict = make_valid_settings_dict()
        settings_dict["redaction"] = {"logs_enabled": "no"}

        with pytest.raises(Exception):
            NornFlowSettings(**settings_dict)
