TRUTHY = ("true", "1", "t", "y", "yes")
FALSY = ("false", "0", "f", "n", "no")
NONRFLOW_MANDATORY_SETTINGS = ("nornir_config_file",)
NONRFLOW_OPTIONAL_SETTINGS = {
    "dry_run": False,
    "parallel_exec": True,
    "ignore_missing_tasks": False,
    "local_tasks_dirs": [],
    "imported_tasks_packages": [],
}
