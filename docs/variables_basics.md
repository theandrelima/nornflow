# NornFlow Variables Basics

## Table of Contents
- [Quick Overview](#quick-overview)
- [Variable Sources](#variable-sources-top-down-priority-order)
- [Basic Usage](#basic-usage)
  - [Environment Variables](#1-environment-variables)
  - [Global Variables](#2-global-variables)
  - [Domain Variables](#3-domain-variables)
  - [Workflow Variables](#4-workflow-variables)
  - [CLI Variables](#5-cli-variables)
  - [Runtime Variables](#6-runtime-variables)
- [Accessing Nornir's Inventory Variables](#accessing-nornirs-inventory-variables)
  - [Basic Host Attributes](#basic-host-attributes)
  - [Accessing Host Data](#accessing-host-data)
  - [Important Notes](#important-notes)
- [Variable Isolation](#variable-isolation)
- [Best Practices](#best-practices)
- [Quick Reference](#quick-reference)

This guide covers the essential concepts for using variables in NornFlow workflows.

## Quick Overview

NornFlow provides a powerful variable system with two namespaces:

1. **Default namespace** - Your workflow variables (direct access: `{{ variable_name }}`)
2. **Host namespace** - Nornir inventory data (prefixed access: `{{ host.variable_name }}`)

## Variable Sources (Top-Down Priority Order)

Variables come from multiple sources. When the same variable exists in multiple places, the highest priority wins:

1. **Runtime variables** (highest) - Set during workflow execution
2. **CLI variables** - Passed via command line
3. **Workflow variables** - Defined in workflow YAML
4. **Domain variables** - Specific to workflow 'domain' (the concept of domain will be explained in this document)
5. **Global variables** - Project-wide defaults
6. **Environment variables** (lowest) - System environment with `NORNFLOW_VAR_` prefix

## Basic Usage
In the sections below, we'll walk through each type of variable in NornFlow's default namespace, from lowest to highest priority, showing how they work and how they interact within workflows.

### 1. Environment Variables

Set environment variables with `NORNFLOW_VAR_` prefix:

```bash
export NORNFLOW_VAR_api_token="secret123"
nornflow run workflow.yaml
```

Access it in your workflow without the 'NORNFLOW_VAR_' prefix:
```yaml
tasks:
  - name: api_call
    args:
      token: "{{ api_token }}"  # Note: no prefix needed
```

Environment variables are the lowest priority and can be overridden by any other variable source.

---

### 2. Global Variables

By default, NornFlow looks for global variables in the vars directory, specifically in defaults.yaml.  

> **Note:** The vars directory location is set by the `vars_dir` setting in your nornflow.yaml file. NornFlow always looks for global variables in `<vars_dir>/defaults.yaml`. If this file is missing, global variable resolution is skipped.

```yaml
# vars/defaults.yaml
site_contact: "network-team@company.com"
backup_server: "10.0.0.100"
```

Use in any workflow:
```yaml
workflow:
    # ...
    tasks:
    - name: echo
      args:
        message: "Backing up to {{ backup_server }}"
```

Global variables override `environment` variables with the same name.

---

### 3. Domain Variables

Domain = first-level subdirectory under your workflow directory.

For a workflow at `workflows/backup/daily.yaml`:
- Domain is `backup`
- Domain variables go in `vars/backup/defaults.yaml`

> **Note:** Like Global Variables, Domain Variables are loaded from a file named `defaults.yaml` within a subdirectory matching the domain name in your configured `vars_dir` (e.g., `vars/backup/defaults.yaml`). If this file doesn't exist, NornFlow simply skips domain variables resolution.

```yaml
# vars/backup/defaults.yaml
retention_days: 30
compression: true
backup_path: "/backups/network"
```

Domain variables override `global` and `environment` variables with the same name.

---

### 4. Workflow Variables

Define variables directly in your workflow:

```yaml
workflow:
  name: "Configure VLANs"
  vars:
    vlan_list: [100, 200, 300]
    trunk_ports: ["Gi0/1", "Gi0/2"]
  
  tasks:
    - name: configure_vlans
      args:
        vlans: "{{ vlan_list }}"
```

Workflow variables override `domain`, `global`, and `environment` variables with the same name.

---

### 5. CLI Variables

Pass variables from command line:

```bash
nornflow run backup.yaml --vars "dry_run=true,region=west"
```

Use in workflow:
```yaml
tasks:
  - name: echo
    args:
      message: "Region: {{ region }}, Dry run: {{ dry_run }}"
```

CLI variables override `workflow`, `domain`, `global`, and `environment` variables with the same name.

---

### 6. Runtime Variables

Runtime variables can be created or updated in two ways:

1. **Directly using NornFlow's built-in `set` task:**

```yaml
tasks:
  - name: set
    args:
      timestamp: "Started workflow execution"
      device_type: "{{ host.platform }}"
      
  - name: echo
    args:
      message: "Working on {{ device_type }} at {{ timestamp }}"
```

2. **Using the `set_to` attribute to capture a task's results:**

```yaml
tasks:
  - name: get_version
    set_to: version_output

  - name: echo
    args:
      message: "Version: {{ version_output }}"
```

> **IMPORTANT:**
> - When you use the `set` task, NornFlow creates or updates variables with the names and values you specify in `args`.
> - When you use `set_to`, NornFlow creates or updates a variable with the given name and stores the entire result object returned by the task (including fields like `result`, `changed`, `failed`, etc.).
> - In both cases, if the variable does not exist, it will be created; if it already exists, it will be updated with the new value.

Runtime variables override `CLI`, `workflow`, `domain`, `global`, and `environment` variables with the same name.

---

## Accessing Nornir's Inventory Variables

NornFlow provides seamless access to your Nornir inventory data through the `host.` namespace. This gives you ***read-only access*** to all host-specific information defined in your Nornir inventory files.

### Basic Host Attributes

The most commonly used host attributes are directly accessible:

```yaml
tasks:
  - name: echo
    args:
      message: |
        Hostname: {{ host.name }}
        Platform: {{ host.platform }}
        Port: {{ host.port }}
        Username: {{ host.username }}
```

### Accessing Host Data

Custom data defined in your inventory's `data` section is accessible via `host.data`:

```yaml
# Example inventory host definition:
# hosts.yaml:
# router1:
#   hostname: 192.168.1.1
#   platform: ios
#   data:
#     site_code: NYC01
#     rack_number: 42
#     model: ISR4451

tasks:
  - name: echo
    args:
      message: |
        Site: {{ host.data.site_code }}
        Rack: {{ host.data.rack_number }}
        Model: {{ host.data.model }}
```

### Important Notes

- **Read-only access**: The `host.` namespace provides read-only access. You cannot modify inventory data during workflow execution.
- **Nested data**: Access nested inventory data using dot notation: `{{ host.data.location.building }}`
- **Missing attributes**: If an attribute doesn't exist, Jinja2 will raise an error. Use the `default` filter to handle optional attributes:
  ```yaml
  message: "VLAN: {{ host.data.management_vlan | default('1') }}"
  ```

## Variable Isolation

Each device maintains its own variable context during workflow execution:

- Variables set for one device don't affect others
- Safe for parallel execution
- No cross-contamination between devices

## Best Practices

1. **Use descriptive names**: *`backup_retention_days`* is a lot better than just *`days`*
2. **Set defaults**: Use `| default()` filter for optional variables
3. **Group related variables**: Use domain variables for workflow-specific settings
4. **Document variables**: Add comments in your variable files (`<vars_dir>/defaults.yaml` and `<vars_dir>/<domain>/default.yaml`)
5. **Avoid name conflicts**: Don't start variable names with *`host`* to avoid confusion with the `host.` namespace

## Quick Reference

| Variable Type      | Location                        | Example                        | Usage                        |
|--------------------|---------------------------------|--------------------------------|------------------------------|
| Environment        | System env                      | `token=abc`                    | `{{ token }}`                |
| Global             | defaults.yaml                   | `timeout: 30`                  | `{{ timeout }}`              |
| Domain             | vars/{domain}/defaults.yaml     | `retries: 3`                   | `{{ retries }}`              |
| Workflow           | In workflow YAML                | `vars: {vlan: 100}`            | `{{ vlan }}`                 |
| CLI                | Command line                    | `--vars "x=1"`                 | `{{ x }}`                    |
| Runtime            | Set with `set` task             | `status: "done"`               | `{{ status }}`               |
|                    | Set with `set_to`               | `set_to: version_output`       | `{{ version_output.result }}`|
| Host data          | Nornir Inventory                | `data: {site_code: NYC01}`     | `{{ host.data.site_code }}`  |


<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./core_concepts.md">← Previous: Core Concepts</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./nornflow_settings.md">Next: NornFlow Settings →</a>
</td>
</tr>
</table>

</div>