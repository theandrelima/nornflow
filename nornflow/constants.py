TRUTHY = ("true", "1", "t", "y", "yes")
FALSY = ("false", "0", "f", "n", "no")

# used to track the mandatory kwargs for a NornFlowSettings object
NONRFLOW_SETTINGS_MANDATORY = ("nornir_config_file",)

# used to track the optional kwargs for a NornFlowSettings object
NONRFLOW_SETTINGS_OPTIONAL = {
    "dry_run": False,
    "local_tasks_dirs": [],
    "imported_packages": [],
}

# Used to check if the kwargs passed to a NornFlow initializer are valid.
# The args listed here are can only be passed through a nornflow settings YAML file
# that will be used to initialize a NornFlowSettings object
NORNFLOW_INVALID_INIT_KWARGS = ("nornir_config_file", "local_tasks_dirs", "imported_packages")

NORNFLOW_SUPPORTED_WORKFLOW_EXTENSIONS = (".yaml", ".yml")
