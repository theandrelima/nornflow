"""Single customization point for live cEOS / containerlab integration tests.

Edit values here to match your lab topology, pinned package version, or generated
asset names. Other modules under this directory import from this file only.

Keep 'inventory/hosts.yaml.example' aligned when you change 'LAB_HOSTS' —
that file is reference documentation for manual preflight, not read at runtime.
"""

from typing import TypedDict


class LabHostSpec(TypedDict):
    """Nornir inventory entry for one lab device."""

    hostname: str
    groups: list[str]


# PyPI package installed in the lab venv (editable nornflow + pinned arista).
NORNFLOW_ARISTA_PACKAGE = "nornflow_arista"
NORNFLOW_ARISTA_VERSION = "0.1.0"

# Static fixture asset filenames (under tests/integration/containerlab/fixtures/overlay/).
LAB_INTEGRATION_WORKFLOW = "lab_integration.yaml"
LAB_STORE_AS_FAILURE_WORKFLOW = "lab_store_as_failure.yaml"
LAB_STORE_AS_FAILURE_MARKER = "NORNFLOW_LAB_STORE_AS_FAILURE_OK"
LAB_READONLY_BLUEPRINT = "lab_readonly_snapshot.yaml"
# File lives under workflows/lab/ for domain vars; catalog key is the filename only.
LAB_VARS_ALL_LEVELS_WORKFLOW = "vars_all_levels.yaml"
LAB_OUTPUT_MASKING_WORKFLOW = "lab_output_masking.yaml"

# User-declared sensitive name exercised by lab_output_masking.yaml and host data.
LAB_MASKING_SENSITIVE_NAME = "credential_x"
LAB_MASKING_CREDENTIAL_SECRET = "CLAB_CREDENTIAL_X_SECRET_VALUE"
LAB_MASKING_VISIBLE_LABEL = "visible-lab-marker"

LAB_VALIDATE_OK_WORKFLOW = "lab_validate_ok.yaml"
LAB_VALIDATE_BAD_TASK_WORKFLOW = "lab_validate_bad_task.yaml"
LAB_VALIDATE_BAD_ARGS_WORKFLOW = "lab_validate_bad_args.yaml"
LAB_VALIDATE_BLUEPRINT_LOOP_WORKFLOW = "lab_validate_blueprint_loop.yaml"

# Env var name set at test runtime for vars-all-levels workflow (NORNFLOW_VAR_env_marker).
LAB_VARS_ENV_VAR = "env_marker"
LAB_VARS_ENV_VALUE = "ENV_OK"

# Default four-node spine–leaf topology (management IPs or DNS names).
LAB_HOSTS: dict[str, LabHostSpec] = {
    "spine1": {"hostname": "172.29.163.101", "groups": ["eos", "spines"]},
    "spine2": {"hostname": "172.29.163.102", "groups": ["eos", "spines"]},
    "leaf1": {"hostname": "172.29.163.103", "groups": ["eos", "leafs"]},
    "leaf2": {"hostname": "172.29.163.104", "groups": ["eos", "leafs"]},
}

# eAPI connection defaults written into generated Nornir inventory.
LAB_EAPI_TRANSPORT = "http"
LAB_EAPI_PORT = 80

# Optional: first leaf host used in README preflight examples (must exist in LAB_HOSTS).
LAB_PREFLIGHT_HOST = "leaf1"
