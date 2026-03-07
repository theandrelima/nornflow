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
  - [Hook Override Behavior](#hook-override-behavior)
- [Error Reference](#error-reference)
- [Limitations](#limitations)

## Overview

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

If `include` is omitted, NornFlow tries to imports **all seven** resource types from that package. If the package provides all seven asset types in their subdirectories, then all is imported. If the package provides only a subset of those, the all provided is also imported. If `include` key is present, however, NornFlow will only attempt to import the listed types under it.

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

#### Catalog-Based Resources (Tasks, Filters, Workflows, Blueprints, J2 Filters)

Resources are loaded in strict order — **last write wins** since catalogs are dictionaries:

```
┌─────────────────────────────────┐
│ 1. Built-in resources           │  ← Loaded first, marked is_builtin=True
│    └── nornflow.builtins.*      │     PROTECTED — cannot be overridden
├─────────────────────────────────┤
│ 2. Package resources            │  ← Loaded in order listed in `packages`
│    ├── packages[0]              │     CatalogError if name clashes with builtin
│    ├── packages[1]              │     Later packages override earlier ones
│    └── packages[N]              │
├─────────────────────────────────┤
│ 3. Local directory resources    │  ← Loaded last
│    └── local_* settings dirs    │     CatalogError if name clashes with builtin
│                                 │     Overrides package resources (WARNING logged)
└─────────────────────────────────┘
```

- Built-in resources are **protected** — any attempt to register a name that clashes with a built-in, whether from a package or a local directory, raises `CatalogError` and halts initialization.
- Package resources can be **overridden by local resources** — later write wins, and a `WARNING` is logged.
- Between packages, **later entries in the `packages` list override earlier ones** for the same name.
- Between local directories (e.g., multiple `local_tasks` entries), later entries override earlier ones — this is existing behavior, unchanged.

#### Hooks (Different Architecture)

Hooks use a completely different precedence model because they register via `__init_subclass__` into a global `HOOK_REGISTRY` dict at import time — not via catalog dict writes. See [Hook Override Behavior](#hook-override-behavior).

### Name Conflict Resolution

NornFlow uses **flat names** across all resources. There is no namespace isolation — all tasks share one namespace, all filters share one, and so on. Resources are registered by their simple name: function name for tasks/filters/j2_filters, filename stem for YAML files, `hook_name` for hooks.

**Non-builtin conflict (package vs local) — WARNING, local wins:**
```
nornflow_acme_toolkit/tasks/backup.py → registers "backup_config"
local tasks/backup.py                 → registers "backup_config"

Result: local version wins, WARNING logged:
  "Task 'backup_config' from local directory 'tasks/' overrides
   'backup_config' from package 'nornflow_acme_toolkit'"
```

**Builtin conflict — hard error:**
```
nornflow_acme_toolkit/tasks/echo.py → tries to register "echo"

Result: CatalogError raised, initialization halts:
  "Cannot override built-in 'echo' with a custom implementation"
  Fix: rename the resource in your package or local directory
```

There are no fully qualified names. If you need both the package version and a local version of a resource with the same name, rename one of them.

### The Built-in Protection Mechanism

`CallableCatalog.register()` contains unconditional protection against overriding built-in items:

```python
if name in self and self.sources.get(name, {}).get("is_builtin", False):
    raise CatalogError(
        f"Cannot override built-in '{name}' with a custom implementation",
        catalog_name=self.name,
    )
```

This applies to **all** sources — packages and local directories alike. There are no exceptions.

**Why this is intentional and permanent:** Built-in tasks (`echo`, `set`, `write_file`) and built-in filters (`hosts`, `groups`) are integral to NornFlow's core runtime. The `set` task powers the runtime variable system. `hosts` and `groups` are referenced implicitly by Nornir's inventory filtering pipeline. Silently replacing any of these would create subtle, hard-to-diagnose failures in fundamental NornFlow operations.

The hard error makes the problem immediately obvious. The fix is always the same: rename the offending resource.

```
Built-in protection flow:
    Step 1: Built-in "echo" registered, is_builtin=True
    ─────────────────────────────────────────────────────
    Step 2: Package tries to register "echo"
            → CatalogError raised
            → NornFlow initialization HALTS
            → Fix: rename the package resource
    ─────────────────────────────────────────────────────
    Step 3: (never reached if step 2 fails)
            Local tries to register "echo"
            → Same CatalogError, same halt
            → Fix: rename the local resource
```

### Hook Override Behavior

Hooks enforce strict name uniqueness through a fundamentally different mechanism than catalog-based resources. **Duplicate `hook_name` values raise `HookRegistrationError` at import time**, regardless of source — built-in, package, or local.

```
Hook registration flow (at import time via __init_subclass__):
    ┌────────────────────────────────────────────────────────────┐
    │ 1. Built-in hooks imported                                 │
    │    HOOK_REGISTRY["set_to"] = SetToHook          ✅         │
    │    HOOK_REGISTRY["if"]     = IfHook             ✅         │
    │    HOOK_REGISTRY["shush"]  = ShushHook          ✅         │
    ├────────────────────────────────────────────────────────────┤
    │ 2. Package hooks imported                                  │
    │    hook_name = "audit"  → PkgAuditHook          ✅         │
    │    hook_name = "set_to" → HookRegistrationError ❌         │
    ├────────────────────────────────────────────────────────────┤
    │ 3. Local hooks imported                                    │
    │    hook_name = "notify" → MyNotifyHook          ✅         │
    │    hook_name = "audit"  → HookRegistrationError ❌         │
    └────────────────────────────────────────────────────────────┘
```

Unlike catalog-based resources, there is **no "local overrides package" precedence for hooks**. Every `hook_name` must be globally unique across built-ins, packages, and local modules. If a package hook and a local hook both define `hook_name = "audit"`, the second one to be imported raises `HookRegistrationError` and initialization fails.

**Why:** Hooks are behavioral extensions injected into the task execution lifecycle via YAML keys (`if:`, `set_to:`, `shush:`). A silent replacement would mean a workflow referencing `set_to:` could get a completely different implementation depending on what packages are installed — that class of bug is extremely difficult to diagnose. Strict uniqueness ensures every `hook_name` maps to exactly one implementation, always.

**Practical impact:** Package and local hook authors must choose unique `hook_name` values. If you want enhanced conditional execution, use `hook_name = "when"` — not `hook_name = "if"`. The `HookRegistrationError` message will clearly identify the conflicting name.

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
| Package or local task/filter name clashes with builtin | `CatalogError` | NornFlow initialization |
| Package or local hook name clashes with any existing hook | `HookRegistrationError` | At import time |

**Fail-fast on missing packages:** If a declared package cannot be imported, NornFlow raises `ResourceError` immediately. The user explicitly asked for that package — not having it installed is a hard failure, not a warning.

## Limitations

1. **NornFlow-native packages only.** Packages must follow the directory layout convention described above. Generic Nornir ecosystem packages with arbitrary internal structures are not supported — wrap their resources in local tasks, filters, or hooks instead.

2. **No package installation.** NornFlow does not install packages. You manage your own environment.

3. **No version management.** NornFlow uses whatever version is currently installed. Version pinning is your responsibility (e.g., via `requirements.txt`, `pyproject.toml`).

4. **No namespace isolation.** All resources share flat namespaces within their catalogs. Non-builtin conflicts are resolved by load order; builtin and hook conflicts are hard errors.

5. **No environment variable override.** The `packages` setting is YAML-only.

6. **No namespace packages.** Python namespace packages (without `__init__.py` / without `__file__`) are not supported and will be skipped with a warning.

7. **No lazy loading.** All declared packages are fully discovered during NornFlow initialization.

8. **Built-in names are reserved.** No package or local resource may use the same name as a built-in task, filter, or hook. Attempts to do so are hard errors.

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