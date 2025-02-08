TRUTHY = ("true", "1", "t", "y", "yes")
FALSY = ("false", "0", "f", "n", "no")

# used to track the mandatory kwargs for a NornFlowSettings object
NONRFLOW_SETTINGS_MANDATORY = ("nornir_config_file",)

# used to track the optional kwargs for a NornFlowSettings object
NONRFLOW_SETTINGS_OPTIONAL = {
    "dry_run": False,
    "parallel_exec": True,
    "ignore_missing_tasks": False,
    "local_tasks_dirs": [],
    "imported_tasks_packages": [],
}

# used to check if the CLI kwargs passed to a NornFlow initializer are valid
NORNFLOW_INVALID_INIT_KWARGS = ("nornir_config_file", "local_tasks_dirs", "imported_tasks_packages")
