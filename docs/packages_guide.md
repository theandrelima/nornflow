# Packages Guide

## Table of Contents
- [Overview](#overview)
- [Configuration](#configuration)
  - [The `packages` Setting](#the-packages-setting)
  - [Package Descriptor Fields](#package-descriptor-fields)
  - [Validation Rules](#validation-rules)
  - [Environment Variable Support](#environment-variable-support)
- [Package Structure Convention](#package-structure-convention)
- [Discovery and Loading](#discovery-and-loading)
  - [Package Path Resolution](#package-path-resolution)
  - [Loading Order and Precedence](#loading-order-and-precedence)
  - [Name Conflict Resolution](#name-conflict-resolution)
  - [The Built-in Protection Mechanism](#the-built-in-protection-mechanism)
  - [Hook Registration Note](#hook-registration-note)
- [Error Reference](#error-reference)
- [Limitations](#limitations)

## Overview

> **Reference package:** [nornflow-arista](https://github.com/NornFlow/nornflow_arista) is the first NornFlow-compatible companion package. Use it as a practical example when learning the feature or authoring your own package — it demonstrates the directory layout, eAPI connection wiring, and how tasks, workflows, blueprints, filters, hooks, Jinja2 filters, and processors plug into NornFlow.

The `packages` setting lets you pull NornFlow resources — tasks, workflows, blueprints, filters, hooks, Jinja2 filters, and processors — from external Python packages installed in your environment.

The workflow is simple: install a NornFlow-compatible package, declare it in `nornflow.yaml`, and NornFlow discovers and catalogs its resources using the exact same mechanisms it uses for your local directories.

```bash
pip install nornflow_acme_toolkit
```

```yaml
# nornflow.yaml
packages:
  - name: nornflow_acme_toolkit
```

That's it. NornFlow does **not** install packages itself — it only imports from packages that are already available in the Python environment.

> **Naming convention:** We strongly recommend that NornFlow-compatible packages use a `nornflow_` prefix in their name (e.g., `nornflow_acme_toolkit`, `nornflow_net_hooks`). This is not enforced — NornFlow will accept any valid Python package name — but the prefix immediately signals to users that a package is designed to work with NornFlow, and makes packages easier to find and identify in the ecosystem.

> **Scope limitation:** This feature is exclusively for **NornFlow-compatible packages** — packages that follow NornFlow's own directory layout convention (described below). Generic Nornir ecosystem packages like `nornir_napalm` or `nornir_netmiko` do not follow this convention and are not compatible with this feature. To use resources from arbitrarily-structured packages, wrap them in local tasks, filters, etc.

## Configuration

### The `packages` Setting

Configured in `nornflow.yaml` as a list of package descriptors. Each entry names an installed Python package and optionally restricts which resource types to import from it:

```yaml
packages:
  - name: nornflow_acme_toolkit        # import all resource types
  - name: nornflow_acme_hooks
    include:                           # import only these resource types
      - hooks
      - j2_filters
  - name: nornflow_acme_workflows
    include:
      - workflows
      - blueprints
```

If `include` is omitted, NornFlow tries to import **all seven** resource types from that package. If the package provides all seven asset types in their subdirectories, then all is imported. If the package provides only a subset of those, all provided is also imported. If `include` key is present, however, NornFlow will only attempt to import the listed types under it.

### Package Descriptor Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Python package import name (e.g., `"nornflow_acme_toolkit"`) |
| `include` | `list[str]` | No | `None` (all types) | Resource types to import. Omit to import everything the package provides. |

Valid resource type identifiers for `include`:

```
tasks, workflows, blueprints, filters, hooks, j2_filters, processors
```

### Validation Rules

| Rule | Behavior |
|------|----------|
| `name` is empty or whitespace | `SettingsError` at settings load time |
| `include` is present but empty (`[]`) | `SettingsError` — if you specify `include`, it must contain at least one item |
| `include` contains an invalid resource type string | `SettingsError` — only the seven valid identifiers are accepted |
| `include` is omitted entirely | All resource types are imported from that package |
| Duplicate package names in the list | `SettingsError` — each package may only appear once |

If you have nothing to import, you could do:
```yaml
packages: []
```

Or simply omit the `packages` key entirely — the default is an empty list.

### Environment Variable Support

**The `packages` setting does not support environment variable override.** This is intentional.

Package declarations are structural project decisions made at design time, not deployment-time overrides. The `packages` key also cannot be passed via `NornFlow.__init__()` kwargs for the same reason.

> NOTE: this may be reviewed in the future if enough community feedback exists.

## Package Structure Convention

NornFlow-compatible packages **must** follow NornFlow's own directory layout convention. Packages that do not follow this structure will not have their resources discovered.

The convention mirrors the `local_*` settings structure: resource subdirectories sit at the package root, named exactly after the resource type they contain:

```
nornflow_acme_toolkit/                 # Installed Python package root
├── __init__.py
│
├── tasks/                             # Nornir task functions
│   ├── __init__.py
│   ├── backup.py                      #   def backup_config(task: Task) -> Result: ...
│   └── provisioning.py               #   def provision_device(task: Task) -> Result: ...
│
├── workflows/                         # Workflow YAML definitions
│   ├── backup_workflow.yaml
│   └── full_deploy.yaml
│
├── blueprints/                        # Blueprint YAML definitions
│   └── common_checks.yaml
│
├── filters/                           # Nornir inventory filter functions
│   ├── __init__.py
│   └── site_filters.py               #   def by_region(host: Host, ...) -> bool: ...
│
├── hooks/                             # Hook subclasses
│   ├── __init__.py
│   └── custom_hooks.py               #   class MyHook(Hook): ...
│
├── j2_filters/                        # Jinja2 filter functions
│   ├── __init__.py
│   └── net_filters.py                #   def mask_to_prefix(value): ...
│
└── processors/                        # Processor subclasses
    ├── __init__.py
    └── custom_processor.py            #   class MyProcessor(Processor): ...
```

**Key rules:**

- **All seven subdirectories are optional.** A package may provide any combination — all seven, just one, or anything in between. If a package provides none of them, NornFlow logs a warning during initialization (a package with zero discoverable resources is likely a misconfiguration).
- **Python resource directories** (`tasks/`, `filters/`, `hooks/`, `j2_filters/`, `processors/`) must be proper Python packages — they must contain `__init__.py`.
- **File-based resource directories** (`workflows/`, `blueprints/`) contain YAML files directly (`.yaml` / `.yml`). No `__init__.py` required.
- **Missing subdirectory logging is context-aware:** If your `include` list explicitly names a resource type but the package has no corresponding subdirectory, NornFlow logs a `WARNING` — you asked for something the package doesn't have, which likely indicates a misconfiguration. If `include` is omitted (scan-everything mode), a missing subdirectory is logged at `DEBUG` — the package simply doesn't provide that type, and that's normal.

## Discovery and Loading

### Package Path Resolution

NornFlow resolves a package's resource directories by importing the package and locating its installation root via `__file__` attribute:

```
Input: package_name="nornflow_acme_toolkit", resource_type="tasks"
    │
    ├── importlib.import_module("nornflow_acme_toolkit")
    │
    ├── module.__file__
    │       → "/path/to/site-packages/nornflow_acme_toolkit/__init__.py"
    │
    ├── Path(module.__file__).parent
    │       → "/path/to/site-packages/nornflow_acme_toolkit/"
    │
    ├── package_root / "tasks"
    │       → "/path/to/site-packages/nornflow_acme_toolkit/tasks/"
    │
    └── .is_dir()?
            ├── Yes → use this directory
            └── No  → skip (caller decides log level)
```

This works for regular `pip install`, editable installs (`pip install -e .`), and packages installed via `uv`, `poetry`, `pdm`, etc.

This does **not** work for Python namespace packages (no `__init__.py`, no `__file__` attribute) — those are skipped with a warning.

Once a resource directory is resolved, NornFlow uses **the exact same discovery mechanisms** as for local directories — the same predicates, the same catalog methods, the same registration logic. There is no special package-discovery code path.

### Loading Order and Precedence

The following loading order applies uniformly to **all asset types** — tasks, filters, workflows, blueprints, hooks, J2 filters, and processors:

```
┌─────────────────────────────────┐
│ 1. Built-in resources           │  ← namespace: nornflow, tier: builtin
│    └── nornflow.builtins.*      │     claims bare names unconditionally
├─────────────────────────────────┤
│ 2. Local directory resources    │  ← namespace: local, tier: local
│    └── local_* settings dirs    │     claims bare when builtin does not
├─────────────────────────────────┤
│ 3. Package resources            │  ← namespace: <package_name>, tier: package
│    ├── packages[0]              │     qualified-only until all packages load
│    ├── packages[1]              │     bare assigned when exactly one package owns it
│    └── packages[N]              │
└─────────────────────────────────┘
```

- **Registration never fails** because two namespaces share a bare name. Collisions are tracked for `nornflow show`.
- **Bare resolution priority:** built-in > local > package (single package owner only).
- **Qualified references** (`namespace.name`) always target the exact namespace — never ambiguous.
- **Package vs package** with the same bare name: both register successfully; bare usage raises `AssetAmbiguityError` at resolve time; qualified refs always work.

### Name Conflict Resolution

Assets are stored under qualified keys (`namespace.name`). Bare references resolve by tier priority when unambiguous.

**Cross-tier reuse (allowed — use qualified to pick a specific namespace):**
```
Built-in:  nornflow.echo
Local:     local.echo
Package:   nornflow_acme.echo

Bare "echo"           → nornflow.echo (built-in wins)
Qualified "local.echo" → local task
```

**Package vs package (latent collision — show warns, qualified refs work):**
```
nornflow_arista.get_facts
nornflow_cisco.get_facts

Bare "get_facts" at runtime → AssetAmbiguityError
"nornflow_arista.get_facts" → always works
```

**Local vs package (local wins bare when no built-in):**
```
local.backup
nornflow_acme.backup

Bare "backup" → local.backup
"nornflow_acme.backup" → package task
```

There is no strict mode and no init-time failure for collisions. Inspect conflicts with `nornflow show --tasks` (and other catalog flags) — the **Collision** column lists co-holders and whether bare resolution is `(bare → winner)` or `(bare ambiguous)`.

### Hook Registration Note

Hooks follow the same namespace model as all other asset types. Built-in hooks live under the `nornflow` namespace; local and package hooks use `local` and `<package_name>` respectively.

The only hook-specific behavior is in `Hook.__init_subclass__`: any `Hook` subclass that does not define `hook_name` as a non-empty string raises `HookRegistrationError` at class definition time.

Bare `store_as` resolves to the built-in hook. A package hook named `store_as` is reachable as `my_pkg.store_as`. Reusing a built-in hook name in a package no longer halts initialization.

## Error Reference

| Scenario | Exception | When |
|----------|-----------|------|
| Empty `name` | `SettingsError` | Settings validation |
| Empty `include` list | `SettingsError` | Settings validation |
| Invalid `include` entry | `SettingsError` | Settings validation |
| Duplicate package names | `SettingsError` | Settings validation |
| Package not installed / import fails | `ResourceError` | NornFlow initialization |
| Namespace package (no `__file__`) | Warning logged, package skipped | NornFlow initialization |
| Resource subdir missing, explicitly in `include` | WARNING logged, resource type skipped | NornFlow initialization |
| Resource subdir missing, `include` omitted | DEBUG logged, resource type skipped | NornFlow initialization |
| Bare name ambiguous at same tier | `AssetAmbiguityError` | Catalog resolve at runtime |
| Qualified or missing reference | `AssetNotFoundError` | Catalog resolve at runtime |
| Hook subclass missing or invalid `hook_name` | `HookRegistrationError` | At import time (class definition) |

**Fail-fast on missing packages:** If a declared package cannot be imported, NornFlow raises `ResourceError` immediately. The user explicitly asked for that package — not having it installed is a hard failure, not a warning.

## Limitations

1. **NornFlow-native packages only.** Packages must follow the directory layout convention described above. Generic Nornir ecosystem packages with arbitrary internal structures are not supported — wrap their resources in local tasks, filters, or hooks instead.

2. **No package installation.** NornFlow does not install packages. You manage your own environment.

3. **No version management.** NornFlow uses whatever version is currently installed. Version pinning is your responsibility (e.g., via `requirements.txt`, `pyproject.toml`).

4. **Qualified references for disambiguation.** Package assets share bare names safely when workflows use qualified references. Bare names that collide at the same tier fail only when actually resolved at runtime.

5. **No environment variable override.** The `packages` setting is YAML-only.

6. **No namespace packages.** Python namespace packages (without `__init__.py` / without `__file__`) are not supported and will be skipped with a warning.

7. **No lazy loading.** All declared packages are fully discovered during NornFlow initialization.

8. **Built-in bare names are owned by `nornflow`.** Packages and local assets may reuse built-in names via qualified keys; bare resolution still prefers built-ins.

---

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./hooks_guide.md">← Previous: Hooks Guide</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./jinja2_filters.md">Next: Jinja2 Filters Reference →</a>
</td>
</tr>
</table>

</div>