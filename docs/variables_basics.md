# NornFlow Variables Basics

## Table of Contents
- [Quick Overview](#quick-overview)
- [Variable Sources (Top-Down Priority Order)](#variable-sources-top-down-priority-order)
- [Basic Usage](#basic-usage)
  - [1. Environment Variables](#1-environment-variables)
  - [2. Global Variables](#2-global-variables)
  - [3. Domain Variables](#3-domain-variables)
  - [4. Workflow Variables](#4-workflow-variables)
  - [5. CLI Variables](#5-cli-variables)
  - [6. Runtime Variables](#6-runtime-variables)
- [Accessing Nornir's Inventory Variables](#accessing-nornirs-inventory-variables)
  - [Basic Host Attributes](#basic-host-attributes)
  - [Accessing Host Data](#accessing-host-data)
  - [Important Notes](#important-notes)
- [Variable Isolation](#variable-isolation)
- [Assembly-Time vs Runtime](#assembly-time-vs-runtime)
- [Advanced: Hook-Driven Template Resolution](#advanced-hook-driven-template-resolution)
- [Best Practices](#best-practices)
- [Quick Reference](#quick-reference)

This guide covers the essential concepts for using variables in NornFlow workflows.

## Quick Overview

NornFlow provides a powerful variable system with two namespaces:

1. **Default namespace** - Your workflow variables (direct access: `{{ variable_name }}`)
2. **Host namespace** - Nornir inventory data (prefixed access: `{{ host.variable_name }}`)

Additionally, NornFlow resolves variables in two distinct phases:

- **Assembly-Time** - During workflow loading (used by blueprints for expansion)
- **Runtime** - During task execution (full variable access)

> NOTE: More on it in [Assembly-Time vs Runtime](#assembly-time-vs-runtime)

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
      token: "{{ api_token }}"
```

Environment variables are the lowest priority and can be overridden by any other variable source.

---

### 2. Global Variables

By default, NornFlow looks for global variables in the vars directory, specifically in `defaults.yaml`.  

> **Note:** The vars directory location is set by the `vars_dir` setting in your `nornflow.yaml` file. NornFlow always looks for global variables in `<vars_dir>/defaults.yaml`. If this file is missing, global variable resolution is skipped.

```yaml
# defaults.yaml
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
        msg: "Backing up to {{ backup_server }}"
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
nornflow run backup.yaml --vars "region=west"
```

Use in workflow:
```yaml
tasks:
  - name: echo
    args:
      msg: "Region: {{ region }}"
```

CLI variables override `workflow`, `domain`, `global`, and `environment` variables with the same name.

---

### 6. Runtime Variables

Runtime variables are the highest priority variables in NornFlow's variable system. They can be created or updated in two ways:

1. **Using NornFlow's built-in `set` task**
2. **Using NornFlow's built-in `set_to` hook to capture task results**

#### Using the `set` Task

The `set` task allows you to create or update runtime variables with any values you specify:

```yaml
tasks:
  - name: set
    args:
      timestamp: "Started workflow execution"
      device_type: "{{ host.platform }}"
      
  - name: echo
    args:
      msg: "Working on {{ device_type }} at {{ timestamp }}"
```

When this task runs:
- NornFlow creates new runtime variables (`timestamp`, `device_type`)
- If variables with these names already exist, they are updated with the new values
- Variables are isolated per device - each host has its own `timestamp`, `device_type`, etc.

#### Using the `set_to` Hook

The `set_to` hook captures task execution results and stores them as runtime variables. It supports two modes:

##### Simple Storage Mode

Store the complete Nornir `Result` object from a task:

```yaml
tasks:
  - name: get_version
    set_to: version_output

  - name: echo
    args:
      msg: "Version: {{ version_output.result }}"
```

In simple mode, `set_to: "variable_name"` stores the entire Nornir `Result` object, which includes:
- `result`: The actual data returned by the task
- `failed`: Boolean indicating if the task failed
- `changed`: Boolean indicating if the task made changes
- Other Result object attributes

##### Extraction Mode

Extract specific data from the result and store it in named variables:

```yaml
tasks:
  - name: get_environment
    set_to:
      cpu_usage: "environment.cpu.0.%usage"
      device_serial: "serial_number"
      uptime_seconds: "environment.uptime"
```

**Extraction Path Syntax:**

The extraction paths directly reference keys in the result data. **No `result.` prefix is needed** - NornFlow automatically looks in the result data:

```yaml
# Direct key access
set_to:
  vendor: "vendor"              # Gets Result.result["vendor"] and sets it to a 'vendor' var
  hostname: "hostname"          # Gets Result.result["hostname"] and sets it to a 'hostname' var

# Nested dictionary access (dot notation)
set_to:
  cpu: "environment.cpu.usage"  # Gets Result.result["environment"]["cpu"]["usage"] and sets it to a 'cpu' var
  
# List indexing (bracket notation)
set_to:
  first_cpu: "environment.cpu[0].usage"    # Gets Result.result["environment"]["cpu"][0]["usage"] and sets it to a 'first_cpu' var  
# Complex nested structures
set_to:
  value: "dict.nested_list[1].another_dict.list[10]"  # Any combination of nested access
```

**Special Extraction Prefixes:**

Three special prefixes extract metadata from the `Result` object itself:

```yaml
set_to:
  task_failed: "_failed"        # Gets result.failed (boolean)
  task_changed: "_changed"      # Gets result.changed (boolean)
  complete_data: "_result"      # Gets the entire result.result dictionary
```

**Real-World Example:**

```yaml
workflow:
  name: "Device Information Collection"
  tasks:
    # Collect facts and extract specific data
    - name: napalm_get
      args:
        getters: ["facts", "environment", "interfaces"]
      set_to:
        device_model: "facts.model"
        device_serial: "facts.serial_number"
        device_vendor: "facts.vendor"
        cpu_usage: "environment.cpu.0.%usage"
        memory_used: "environment.memory.used_ram"
        interface_count: "interfaces"  # Will store the entire interfaces dict
        task_succeeded: "_failed"  # Store if collection failed
    
    # Use extracted data in subsequent tasks
    - name: set
      args:
        backup_filename: "{{ device_vendor }}_{{ device_model }}_{{ device_serial }}.cfg"
        high_cpu_alert: "{{ cpu_usage | int > 80 }}"
    
    # Conditional action based on extracted data
    - name: send_alert
      if: "{{ high_cpu_alert }}"
      args:
        message: "High CPU usage detected: {{ cpu_usage }}%"
```

#### Key Differences Between `set` Task and `set_to` Hook

| Aspect | `set` Task | `set_to` Hook |
|--------|------------|---------------|
| **Purpose** | Create/update variables with specified values | Create/update variables with task execution results |
| **What's stored** | Values you explicitly provide in `args` | Task's `Result` object or extracted data |
| **When to use** | Setting calculated/templated values | Capturing output from tasks |
| **Data format** | Any data type (strings, numbers, lists, dicts) | `Result` object or extracted values |
| **Typical use** | Setting timestamps, counters, filenames | Storing device facts, command output, API responses |

#### Variable Creation and Updates

**Important behavior for both approaches:**

- If a runtime variable **does not exist**, it will be **created**
- If a runtime variable **already exists**, it will be **updated** with the new value
- All runtime variables are **isolated per device** - each host maintains its own set
- Runtime variables have the **highest precedence** and override all other variable sources

```yaml
tasks:
  # Create initial counter
  - name: set
    args:
      attempt_count: 1
  
  # Later, update the counter
  - name: set
    args:
      attempt_count: "{{ attempt_count | int + 1 }}"  # Updates existing variable
  
  # Capture task result
  - name: get_version
    set_to: version_data  # Creates 'version_data' variable
  
  # Update with new data
  - name: get_config
    set_to: version_data  # Updates 'version_data' with new result
```

Runtime variables override `CLI`, `workflow`, `domain`, `global`, and `environment` variables with the same name.

---

## Accessing Nornir's Inventory Variables

NornFlow provides seamless access to your Nornir inventory data through the `host.` namespace. This gives you ***read-only access*** to all host-specific information defined in your Nornir inventory files.

> **Implementation Note:** This read-only access is provided by the `NornirHostProxy` class, which is managed by the `NornFlowVariableProcessor`. The processor ensures that the proxy always has the correct host context when variables are being resolved, allowing safe concurrent access to inventory data across multiple devices running in parallel.

### Basic Host Attributes

The most commonly used host attributes are directly accessible:

```yaml
tasks:
  - name: echo
    args:
      msg: |
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
      msg: |
        Site: {{ host.data.site_code }}
        Rack: {{ host.data.rack_number }}
        Model: {{ host.data.model }}
```

### Important Notes

- **Read-only access**: The `host.` namespace provides read-only access. You cannot modify Nornir's inventory data during a NornFlow's Workflow execution.
- **Nested data**: Access nested inventory data using dot notation: `{{ host.data.location.building }}`
- **Missing attributes**: If an attribute doesn't exist, Jinja2 will raise an error. Use the `default` filter to handle optional attributes:
  ```yaml
  message: "VLAN: {{ host.data.management_vlan | default('1') }}"
  ```
- **Checking variable existence**: Use the `is_set` filter to check if a variable exists before using it:
  ```yaml
  # Check if variable exists
  - name: conditional_task
    if: "{{ 'backup_path' | is_set }}"
    args:
      path: "{{ backup_path }}"
  
  # Check if host data exists
  - name: site_specific_task
    if: "{{ 'host.data.site_code' | is_set }}"
    args:
      site: "{{ host.data.site_code }}"
  
  # Combine with default for fallback values
  - name: echo
    args:
      msg: "Site: {{ host.data.site_code if 'host.data.site_code' | is_set else 'UNKNOWN' }}"
  ```

## Variable Isolation

Each device maintains its own variable context during workflow execution:

- Variables set for one device don't affect others
- Safe for parallel execution
- No cross-contamination between devices

This isolation is managed by NornFlow's `NornFlowDeviceContext` class, which creates separate variable contexts for each device. This ensures that tasks running in parallel don't interfere with each other's variables, even when they're modifying variables with the same names.

## Assembly-Time vs Runtime

NornFlow resolves variables in two distinct phases:

### Assembly-Time (Blueprints)

During workflow loading, blueprints are expanded using a **limited subset** of variables:

**Available:**
- Environment Variables
- Global Variables
- Domain Variables  
- Workflow Variables
- CLI Variables

**NOT Available:**
- Runtime Variables (don't exist yet)
- Host inventory data (`host.*` namespace)

This allows blueprints to use variables for conditional inclusion and dynamic selection, but cannot access runtime data that only exists during execution.

### Runtime (Tasks)

During task execution, **all variables** are available including runtime variables and full host inventory access via the `host.*` namespace.

> **Note:** For comprehensive coverage of blueprint variable resolution including examples and best practices, see the [Blueprints Guide](./blueprints_guide.md).

## Advanced: Hook-Driven Template Resolution

For information on Hook-Driven Template Resolution, which allows deferring variable resolution in task parameters when hooks need to evaluate conditions first, see the [Hooks Guide](hooks_guide.md#hook-driven-template-resolution).

## Best Practices

1. **Use descriptive names**: *`backup_retention_days`* is a lot better than just *`days`*
2. **Set defaults**: Use `| default()` filter for optional variables
3. **Check variable existence**: Use `| is_set` filter to safely check if variables exist before using them
4. **Group related variables**: Use domain variables for domain-specific settings
5. **Document variables**: Add comments in your variable files (`<vars_dir>/defaults.yaml` and `<vars_dir>/<domain>/default.yaml`)
6. **Avoid name conflicts**: Don't start variable names with *`host`* to avoid confusion with the `host.` namespace
7. **Use `set_to` extraction for cleaner code**: Extract only the data you need upfront instead of storing complete results
8. **Leverage Jinja2 filters**: Use filters to transform data, especially when working with complex structures

## Quick Reference

| Variable Type      | Location                        | Example                        | Usage                        |
|--------------------|---------------------------------|--------------------------------|------------------------------|
| Environment        | System env                      | `token=abc`                    | `{{ token }}`                |
| Global             | `defaults.yaml`                 | `timeout: 30`                  | `{{ timeout }}`              |
| Domain             | `vars/{domain}/defaults.yaml`   | `retries: 3`                   | `{{ retries }}`              |
| Workflow           | In workflow YAML                | `vars: {vlan: 100}`            | `{{ vlan }}`                 |
| CLI                | Command line                    | `--vars "x=1"`                 | `{{ x }}`                    |
| Runtime            | Set with `set` task             | `status: "done"`               | `{{ status }}`               |
|                    | Set with `set_to` (simple)      | `set_to: version_output`       | `{{ version_output.result }}`|
|                    | Set with `set_to` (extraction)  | `set_to: {vendor: "vendor"}`   | `{{ vendor }}`               |
| Host data          | Nornir Inventory                | `data: {site_code: NYC01}`     | `{{ host.data.site_code }}`  |

**Checking Variable Existence:**

| Check Type         | Syntax                          | Returns                        |
|--------------------|---------------------------------|--------------------------------|
| Default namespace  | `{{ 'var_name' \| is_set }}`    | `true` if variable exists      |
| Host namespace     | `{{ 'host.var_name' \| is_set }}`| `true` if host attribute exists|
| Host data          | `{{ 'host.data.key' \| is_set }}`| `true` if host data key exists |

**Variable Context Availability:**

| Context        | Available Variables |
|----------------|---------------------|
| Assembly-Time  | Environment, Global, Domain, Workflow, CLI |
| Runtime        | All the above, plus runtime and `host.*` namespace |


<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./failure_strategies.md">← Previous: Failure Strategies</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./hooks_guide.md">Next: Hooks Guide →</a>
</td>
</tr>
</table>

</div>
