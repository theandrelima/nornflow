# Live cEOS lab integration tests (maintainer guide)

NornFlow has three test tiers. Most contributors and CI only need the first two.

| Tier | Location | When it runs | Needs live lab |
|------|----------|--------------|----------------|
| Unit | `tests/unit/` | Default `pytest`, CI | No |
| Layer 1 integration | `tests/integration/catalog_namespaces/` | Default `pytest`, CI | No (mocked Nornir) |
| Layer 2 integration | `tests/integration/containerlab/` | Opt-in; maintainers run before merging your PR | Yes (reachable cEOS lab) |

---

## Default development and CI

```bash
pytest
# or
pytest tests/
```

This runs unit tests and Layer 1 integration tests. **Containerlab tests are excluded** by default (`addopts = "-m 'not containerlab'"` in `pyproject.toml`).

GitHub Actions uses the same default — no lab, credentials, or Arista images required.

---

## Layer 2: live lab requirements

Layer 2 tests talk to **real Arista cEOS devices** over eAPI. The lab can be **physical or virtual** — what matters is that your environment matches the **expected topology** below and that management IPs are reachable from the machine running pytest.

### Expected topology

The suite assumes a **four-node spine–leaf** lab with these hostnames and management addresses (defaults):

| Host | Mgmt IP (default) | Role | Nornir groups |
|------|-------------------|------|---------------|
| spine1 | 172.29.163.101 | Spine | `eos`, `spines` |
| spine2 | 172.29.163.102 | Spine | `eos`, `spines` |
| leaf1 | 172.29.163.103 | Leaf | `eos`, `leafs` |
| leaf2 | 172.29.163.104 | Leaf | `eos`, `leafs` |

Additional expectations:

- **eAPI** enabled on each node: `http://<mgmt-ip>/command-api` on **port 80** (HTTP, not HTTPS).
- **Credentials** shared across all four hosts (injected at test runtime via env vars).
- **Data-plane links** between nodes are not asserted, but the local blueprint runs `get_lldp_neighbors`; a cabled spine–leaf topology will exercise that task meaningfully.

### Suggested lab environment

A common setup is a **containerized Containerlab deployment** with **virtual cEOS** images (spine1/2, leaf1/2). Any other lab that reproduces the same hostnames, reachability, and eAPI settings works equally well — bare metal, VM, cloud, or a different container runtime.

You are responsible for:

1. Deploying and keeping the lab running.
2. Ensuring the pytest host has **L3 reachability** to each management IP.
3. Providing valid eAPI credentials via environment variables (never commit secrets).

---

## Customizing the lab

All tunable defaults for Layer 2 tests live in **`tests/integration/containerlab/constants.py`**. Edit that file to match your environment — do not scatter changes across `lab_project.py` or test modules.

| Constant | Purpose |
|----------|---------|
| `NORNFLOW_ARISTA_VERSION` | PyPI pin for `nornflow-arista` installed in the lab venv |
| `NORNFLOW_ARISTA_PACKAGE` | Package namespace used in catalog assertions |
| `LAB_HOSTS` | Hostnames, management IPs (or DNS), and Nornir groups |
| `LAB_EAPI_TRANSPORT` / `LAB_EAPI_PORT` | eAPI settings written into generated inventory |
| `LAB_INTEGRATION_WORKFLOW` / `LAB_READONLY_BLUEPRINT` | Generated asset filenames |
| `LAB_PREFLIGHT_HOST` | Which `LAB_HOSTS` key README preflight examples use |

Example — point tests at your management subnet and bump the package pin:

```python
NORNFLOW_ARISTA_VERSION = "0.1.0"

LAB_HOSTS: dict[str, LabHostSpec] = {
    "spine1": {"hostname": "10.0.0.11", "groups": ["eos", "spines"]},
    "spine2": {"hostname": "10.0.0.12", "groups": ["eos", "spines"]},
    "leaf1": {"hostname": "10.0.0.13", "groups": ["eos", "leafs"]},
    "leaf2": {"hostname": "10.0.0.14", "groups": ["eos", "leafs"]},
}
```

**To point tests at your lab:**

1. Edit **`hostname`** values in `LAB_HOSTS` to match your management IPs or DNS names.
2. Optionally rename keys (e.g. `spine1` → `my-spine-a`) — workflows use `host.name` from Nornir, so renames are fine as long as all four roles exist and eAPI works. Update `LAB_PREFLIGHT_HOST` if you rename the default preflight leaf.
3. Adjust **`groups`** only if you change inventory structure; the generated project expects `eos`, `spines`, and `leafs`.
4. Keep **`tests/integration/containerlab/inventory/hosts.yaml.example`** in sync for manual preflight reference.

Tests **do not** read `hosts.yaml.example` at runtime.

---

## Running the Layer 2 suite

### Environment variables

```bash
export NORNFLOW_LAB=1
export NORNFLOW_LAB_USER=your_user
export NORNFLOW_LAB_PASSWORD=your_password
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `NORNFLOW_LAB` | Yes | Must be `1` to run Layer 2 tests |
| `NORNFLOW_LAB_USER` | Yes when `NORNFLOW_LAB=1` | eAPI username (injected into generated inventory) |
| `NORNFLOW_LAB_PASSWORD` | Yes when `NORNFLOW_LAB=1` | eAPI password (never commit) |

If `NORNFLOW_LAB` is unset or not `1`, containerlab tests **skip** (they do not fail).

If `NORNFLOW_LAB=1` but credentials are missing, tests **fail** immediately.

### Command

```bash
pytest tests/integration/containerlab \
  --override-ini addopts= \
  -m containerlab \
  -s \
  -v
```

`-s` disables pytest output capture so NornFlow CLI output (workflow overview, per-host task results) prints live.

`--override-ini addopts=` clears the default `-m 'not containerlab'` filter so the lab tests are collected.

### What the suite does

1. Creates a temp directory with its own virtualenv.
2. Installs **editable nornflow** from your checkout and **pinned `nornflow-arista`** from PyPI (version from `constants.py`).
3. Writes a minimal temp project with static Nornir inventory (four hosts, HTTP eAPI) from `LAB_HOSTS` in `constants.py`.
4. **Phase B** — in-process catalog validation plus `nornflow show` for tasks, filters, workflows, blueprints, j2-filters, and hooks (no device I/O).
5. **Phase C** — runs `nornflow run lab_integration.yaml`: plain workflow vars, package j2 filters in task args, builtin hooks (`if`, `single`, `set_to`), local blueprint with read-only package getters, and a final `get_facts` on all hosts.
6. Deletes the temp tree when finished (pass or fail).

---

## Preflight (optional)

Before pytest, confirm reachability and eAPI from the **same machine** that will run the tests. Replace the IP with one of your leaf management addresses (default: `leaf1`):

```bash
ping -c 2 172.29.163.103

curl -s -u "$NORNFLOW_LAB_USER:$NORNFLOW_LAB_PASSWORD" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"runCmds","id":1,"params":{"version":1,"format":"json","cmds":["show version"]}}' \
  http://172.29.163.103/command-api | head
```

Reference inventory (no secrets): `tests/integration/containerlab/inventory/hosts.yaml.example`.

---

## Troubleshooting

### Tests skipped

- `NORNFLOW_LAB` is not `1` — expected for normal `pytest` / CI.
- You ran without `--override-ini addopts=` and `-m containerlab` — default pytest excludes the `containerlab` marker.

### Timeouts / connection failures (Phase C)

- No route to the lab management subnet from the pytest host — fix routing, VPN, or port forwarding for your environment.
- Lab not running or nodes still booting — confirm containers/VMs are up and eAPI is enabled.
- Wrong credentials — verify with the curl preflight above.
- **IP mismatch** — if your lab uses different addresses, update `LAB_HOSTS` in `constants.py` (see [Customizing the lab](#customizing-the-lab)).

### Phase B fails

- PyPI or network issue installing `nornflow-arista` at the version pinned in `constants.py`.
- Package load error — run with `-v` and inspect stderr from the lab venv subprocess.

---

## Out of scope (V1)

- Deploying or destroying Containerlab (or any lab) inside pytest
- Public CI with cEOS images (licensing)
- Workflow dry-run tests (Phase D)
- Live config mutation tests (Phase E)
- Nautobot / dynamic inventory
- SSH / Netmiko checks

---

## Default lab device reference

Values below match `LAB_HOSTS` in `tests/integration/containerlab/constants.py`.

| Host | Mgmt IP | Role |
|------|---------|------|
| spine1 | 172.29.163.101 | Spine |
| spine2 | 172.29.163.102 | Spine |
| leaf1 | 172.29.163.103 | Leaf |
| leaf2 | 172.29.163.104 | Leaf |

eAPI: `http://<ip>/command-api` (port 80, not HTTPS).
