import os
from collections import defaultdict
from utils import read_yaml_file
from constants import TRUTHY

class NornFlowSettings:
    """
    This class is used to store NornFlow settings for access during runtime.
    
    For initialization, it requires the location of a YAML file that holds the settings.
    
    By default, it expects a file named `nornflow.yaml` to be in the same directory
    from where the Python interpreter is run. 
    
    The user can override this default by setting the `NORNFLOW_CONFIG_FILE` environment variable.
    
    To allow for ease of extensibility and customizations, NornFlow was
    designed with the following principles in mind:
        - a minimal amount of required settings, namely:
            - `nornir_config_file`
            - `tasks`
        - users can add more settings according to their needs to the `nornflow.yaml` config file
        - settings can be accessed as attributes of a NornFlowSettings object:
          NornFlowSettings().tasks # returns the 'tasks' setting
        - non-existing settings will return None:
          NornFlowSettings().non_existing_setting  # returns None
    """
    def __init__(self, config_file: str = "nornflow.yaml", dry_run: bool = False):
        # Use environment variable to override config file path if set
        self.config_file = os.getenv("NORNFLOW_CONFIG_FILE", config_file)
        self._load_config()
        
        self.dry_run = self.dry_run or dry_run

    def _load_config(self):
        config_data = read_yaml_file(self.config_file)
        self.config = defaultdict(lambda: None, config_data)
        
    @property
    def nornir_configs(self):
        return read_yaml_file(self.config["nornir_config_file"])

    def __getattr__(self, name):
        return self.config[name]
