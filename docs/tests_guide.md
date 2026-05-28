# Containerlab integration tests (maintainer guide)

NornFlow has three test tiers. Most contributors and CI only need the first two.

| Tier | Location | When it runs | Needs live lab |
|------|----------|--------------|----------------|
| Unit | `tests/unit/` | Default `pytest`, CI | No |
| Layer 1 integration | `tests/integration/catalog_namespaces/` | Default `pytest`, CI | No (mocked Nornir) |
| Layer 2 integration | `tests/integration/containerlab/` | Opt-in, maintainer only | Yes (cEOS via OrbStack) |

Design reference: `architectural_docs/_architecture_containerlab_integration_tests.md` (local, not published).

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

## Layer 2: maintainer lab run

### Prerequisites

1. **OrbStack** with Debian VM `clab` running Containerlab cEOS (spine1/2, leaf1/2).
2. **macOS route** to the lab mgmt subnet (often lost after reboot):

   ```bash
   # Confirm VM IP with: orb list
   sudo route -n add 172.29.163.0/24 192.168.139.193
   ```

3. **eAPI reachable** on HTTP port 80 from your Mac (see Phase A preflight below).
4. **Environment variables** (never commit real values):

   ```bash
   export NORNFLOW_LAB=1
   export NORNFLOW_LAB_USER=your_user
   export NORNFLOW_LAB_PASSWORD=your_password
   ```

### Run the full Layer 2 suite

```bash
export NORNFLOW_LAB=1
export NORNFLOW_LAB_USER=your_user
export NORNFLOW_LAB_PASSWORD=your_password

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
2. Installs **editable nornflow** from your checkout and **pinned `nornflow-arista==0.1.0`** from PyPI.
3. Writes a minimal temp project with static Nornir inventory (four hosts, HTTP eAPI).
4. **Phase B** — in-process catalog validation plus `nornflow show` for tasks, filters, workflows, blueprints, j2-filters, and hooks (no device I/O).
5. **Phase C** — runs `nornflow run lab_integration.yaml`: plain workflow vars, package j2 filters in task args, builtin hooks (`if`, `single`, `set_to`), local blueprint with read-only package getters, and a final `get_facts` on all hosts.
6. Deletes the temp tree when finished (pass or fail).

---

## Phase A — manual preflight (optional)

Before pytest, confirm routing and eAPI from your Mac:

```bash
ping -c 2 172.29.163.103

curl -s -u "$NORNFLOW_LAB_USER:$NORNFLOW_LAB_PASSWORD" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"runCmds","id":1,"params":{"version":1,"format":"json","cmds":["show version"]}}' \
  http://172.29.163.103/command-api | head
```

Inventory template (no secrets): `tests/integration/containerlab/inventory/hosts.yaml.example`.

---

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `NORNFLOW_LAB` | Yes | Must be `1` to run Layer 2 tests |
| `NORNFLOW_LAB_USER` | Yes when `NORNFLOW_LAB=1` | eAPI username (injected into generated inventory) |
| `NORNFLOW_LAB_PASSWORD` | Yes when `NORNFLOW_LAB=1` | eAPI password (never commit) |

If `NORNFLOW_LAB` is unset or not `1`, containerlab tests **skip** (they do not fail).

If `NORNFLOW_LAB=1` but credentials are missing, tests **fail** immediately.

---

## Troubleshooting

### Tests skipped

- `NORNFLOW_LAB` is not `1` — expected for normal `pytest` / CI.
- You ran without `--override-ini addopts=` and `-m containerlab` — default pytest excludes the `containerlab` marker.

### Timeouts / connection failures (Phase C)

- Missing macOS route to `172.29.163.0/24` — re-add via OrbStack VM IP.
- Lab not deployed inside OrbStack — check `orb -m clab bash -c 'docker ps'`.
- Wrong credentials — verify with curl preflight (Phase A).
- Stale VM IP after OrbStack restart — run `orb list` and update the route gateway.

### Phase B fails

- PyPI or network issue installing `nornflow-arista==0.1.0`.
- Package load error — run with `-v` and inspect stderr from the lab venv subprocess.

---

## Out of scope (V1)

- Deploying/destroying Containerlab inside pytest
- Public CI with cEOS images (licensing — see architecture doc)
- Workflow dry-run tests (Phase D)
- Live config mutation tests (Phase E)
- Nautobot / dynamic inventory
- SSH / Netmiko checks

---

## Lab device reference

| Host | Mgmt IP | Role |
|------|---------|------|
| spine1 | 172.29.163.101 | Spine |
| spine2 | 172.29.163.102 | Spine |
| leaf1 | 172.29.163.103 | Leaf |
| leaf2 | 172.29.163.104 | Leaf |

eAPI: `http://<ip>/command-api` (port 80, not HTTPS).
