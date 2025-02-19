import os
from collections import defaultdict
from typing import Any

import yaml

from nornflow.constants import NONRFLOW_SETTINGS_MANDATORY, NONRFLOW_SETTINGS_OPTIONAL
from nornflow.exceptions import (
    EmptyMandatorySettingError,
    MissingMandatorySettingError,
    NornFlowError,
    SettingsDataTypeError,
    SettingsFileNotFoundError,
    SettingsFileParsingError,
    SettingsFilePermissionError,
)
from nornflow.utils import read_yaml_file


class NornFlowSettings:
    """
    This class is used to store NornFlow settings for access during runtime.

    For initialization, it requires the location of a YAML file that holds the settings.
    This will be determined with the following order of preference:
        - through an environment variable named `NORNFLOW_CONFIG_FILE`.
        - through the `config_file` argument.
        - a default file named 'nornflow.yaml' is assumed to exist.

    To allow for extensibility and customizations, NornFlow was designed with the following
    principles in mind:
        1 - NornFlow settings and Nornir settings are kept separate, hence the need for a
           `nornir_config_file` setting in the NornFlow YAML settings file.

        2 - a minimal set of REQUIRED settings.

        3 - a minimal set of OPTIONAL settings that can also be passed explicitly to the Class
            initializer as keyword arguments.

        4 - there's no fixed set of "acceptable settings". Users can add more settings if
            they want to extend NornFlow to support custom use-cases, but currently this is
            only supported through the YAML file, not through keyword arguments.

        5 - settings can be accessed as attributes of a NornFlowSettings object:
            NornFlowSettings().local_tasks_dirs # returns the 'local_tasks_dirs' setting

        6 - trying to access non-supported settings also not informed in the YAML file
            will simply return None:
            NornFlowSettings().non_existing_setting_not_informed_in_yaml_either  # returns None
    """

    def __init__(self, settings_file: str = "nornflow.yaml", **kwargs):
        # Use environment variable to override config file path if set
        self.settings_file = os.getenv("NORNFLOW_CONFIG_FILE", settings_file)
        self._load_settings()
        self._check_mandatory_settings()
        self._set_optional_settings(**kwargs)

    @property
    def as_dict(self) -> dict[str, Any]:
        return dict(self.loaded_settings)

    def _load_settings(self) -> None:
        """
        This method reads the configuration file specified by `self.settings_file`, parses its
        contents, and stores them in `self.loaded_settings`. If any errors occur during this
        process, appropriate custom exceptions are raised.

        Raises:
            SettingsFileNotFoundException: If the configuration file does not exist.
            SettingsFilePermissionException: If there is a permission error accessing the configuration file.
            SettingsFileParsingException: If there is an error parsing the YAML file.
            SettingsDataTypeException: If the configuration data is not a dictionary.
        """
        try:
            config_data = read_yaml_file(self.settings_file)

            if not isinstance(config_data, dict):
                raise SettingsDataTypeError()

            self.loaded_settings = defaultdict(lambda: None, config_data)
        except FileNotFoundError as e:
            raise SettingsFileNotFoundError(self.settings_file) from e
        except PermissionError as e:
            raise SettingsFilePermissionError(self.settings_file) from e
        except yaml.YAMLError as e:
            raise SettingsFileParsingError(self.settings_file, str(e)) from e
        except TypeError as e:
            raise SettingsDataTypeError() from e
        except Exception as e:
            raise NornFlowError(f"An unexpected error occurred: {e}") from e

    def _check_mandatory_settings(self) -> None:
        """
        Check if all mandatory settings are present and not empty in the configuration.

        Raises:
            ValueError: If a mandatory setting is missing or empty.
        """
        for setting in NONRFLOW_SETTINGS_MANDATORY:
            if setting not in self.loaded_settings:
                raise MissingMandatorySettingError(setting)
            if not self.loaded_settings[setting]:
                raise EmptyMandatorySettingError(setting)

    def _set_optional_settings(self, **kwargs: Any) -> None:
        """
        Set optional settings from kwargs or default to existing attributes.
        This enforces preference for optional settings passed as keyword arguments.

        The preference algorithm is as follows:
        1. Use the value passed explicitly in kwargs.
        2. If not in kwargs, use the value read from the YAML file.
        3. If not in the YAML file, use the default value from NONRFLOW_OPTIONAL_SETTINGS.

        Args:
            **kwargs (Any): Keyword arguments containing optional settings.
        """
        for setting, default_value in NONRFLOW_SETTINGS_OPTIONAL.items():
            self.loaded_settings[setting] = kwargs.get(
                setting, self.loaded_settings.get(setting, default_value)
            )

    def __getattr__(self, name: str) -> Any:
        return self.loaded_settings[name]

    def __str__(self) -> str:
        """
        Return a string representation of the NornFlowSettings instance,
        excluding the 'loaded_settings' attribute.
        """
        return str(dict(self.loaded_settings))
