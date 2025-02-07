NORNIR_DEFAULT_CONFIG_DIR = "nornir_configs"
NORNIR_DEFAULT_CONFIG_FILES = ["config.yaml", "hosts.yaml", "groups.yaml", "defaults.yaml"]
NONRFLOW_INIT_SETTINGS = {
    "nornir_config_file": "nornir_configs/config.yaml",
    "local_tasks_dirs": ["tasks"],
    "imported_tasks_packages": [],
    "dry_run": False,
    "parallel_exec": True,
    "ignore_missing_tasks": True,
}
