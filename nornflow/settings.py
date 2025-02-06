import os
from collections import defaultdict
from typing import Any

from nornflow.utils import read_yaml_file
from nornflow.exceptions import MissingMandatorySettingException, EmptyMandatorySettingException


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
           `nornir_config_file` setting in the NornFlow YAML settings file (see '2' below).

        2 - a minimal set of REQUIRED settings:
            - `nornir_config_file`
            - `tasks`

        3 - a minimal set of OPTIONAL settings that can also be passed explicitly to the Class
            initializer as keyword arguments.
            - `dry_run`: defaults to False
            - `parallel_execution` defaults to True

        4 - there's no fixed set of "acceptable settings". Users can add more settings if
            they want to extend NornFlow to support custom use-cases.

        5 - settings can be accessed as attributes of a NornFlowSettings object:
            NornFlowSettings().tasks # returns the 'tasks' setting

        6 - trying to access settings that were not informe in the YAMLS nor passed as a keyword
            args will simply return None:
            NornFlowSettings().non_existing_setting  # returns None
    """

    MANDATORY_SETTINGS = ("nornir_config_file", "tasks")
    OPTIONAL_SETTINGS = ("dry_run", "parallel_execution")

    def __init__(self, config_file: str = "nornflow.yaml", **kwargs):
        # Use environment variable to override config file path if set
        self.config_file = os.getenv("NORNFLOW_CONFIG_FILE", config_file)
        self._load_config()
        self._check_mandatory_settings()
        self._set_optional_settings(**kwargs)

    def _load_config(self) -> None:
        config_data = read_yaml_file(self.config_file)
        self.loaded_settings = defaultdict(lambda: None, config_data)

    def _check_mandatory_settings(self) -> None:
        """
        Check if all mandatory settings are present and not empty in the configuration.

        Raises:
            ValueError: If a mandatory setting is missing or empty.
        """
        for setting in self.MANDATORY_SETTINGS:
            if setting not in self.loaded_settings:
                raise MissingMandatorySettingException(setting)
            if not self.loaded_settings[setting]:
                raise EmptyMandatorySettingException(setting)

    def _set_optional_settings(self, **kwargs: Any) -> None:
        """
        Set optional settings from kwargs or default to existing attributes.
        This enforces preference for optional settings passed as keyword arguments.

        Args:
            **kwargs (Any): Keyword arguments containing optional settings.
        """
        for setting in self.OPTIONAL_SETTINGS:
            setattr(self, setting, kwargs.get(setting, getattr(self, setting)))

    @property
    def nornir_configs(self) -> dict[str, Any]:
        return read_yaml_file(self.loaded_settings["nornir_config_file"])

    def __getattr__(self, name: str) -> Any:
        return self.loaded_settings[name]
