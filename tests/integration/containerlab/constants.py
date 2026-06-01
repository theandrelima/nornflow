"""Single customization point for live cEOS / containerlab integration tests.

Edit values here to match your lab topology, pinned package version, or generated
asset names. Other modules under this directory import from this file only.

Keep ``inventory/hosts.yaml.example`` aligned when you change ``LAB_HOSTS`` —
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

# Generated local workflow and blueprint filenames (under temp project).
LAB_INTEGRATION_WORKFLOW = "lab_integration.yaml"
LAB_STORE_AS_FAILURE_WORKFLOW = "lab_store_as_failure.yaml"
LAB_STORE_AS_FAILURE_MARKER = "NORNFLOW_LAB_STORE_AS_FAILURE_OK"
LAB_READONLY_BLUEPRINT = "lab_readonly_snapshot.yaml"

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
