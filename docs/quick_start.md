# Quick Start Guide

## Table of Contents
- [Installation](#installation)
- [Initialize Your Project](#your-first-nornflow-project)
- [Running Tasks](#running-tasks)
- [Running Workflows](#running-workflows)
- [Working with Real-World Use Case](#working-with-real-world-use-case)
- [Using Variables](#using-variables)
- [Using Blueprints](#using-blueprints)
- [Filtering Inventory](#filtering-inventory)
- [Useful Commands](#useful-commands)

> **Notes:** 
> 1. This document is intentionally light on each subject. Much of what's mentioned here (and more) is expanded in the [Core Concepts](./core_concepts.md) documentation.
> 2. Throughout the whole documentation, we won't go into the details about Nornir's configs and concepts (tasks, inventory, filters, etc). Those are pre-requisites to use NornFlow. You may want to check [Nornir's docs](https://github.com/nornir-automation/nornir).

## Installation

```bash
# Using pip
pip install nornflow

# Using poetry
poetry add nornflow

# Using uv
uv pip install nornflow
```

## Your First NornFlow Project

### 1. Initialize NornFlow

Before using NornFlow, you **must initialize a NornFlow project** inside a folder.  
This folder becomes your workspace, and all NornFlow commands should be run from within it.

```bash
mkdir my_nornflow_project
cd my_nornflow_project
nornflow init
```

This creates:
- 📁 tasks - Where your Nornir tasks should live
- 📁 workflows - Holds YAML workflow definitions
- 📁 filters - Custom Nornir inventory filters
- 📁 hooks - Custom hook implementations for extending task behavior
- 📁 blueprints - Reusable task collections
- 📁 vars - Will contain Global and Domain-specific default variables
- 📁 nornir_configs - Nornir configuration
- 📑 nornflow.yaml - NornFlow settings

### 2. Check What's Available

```bash
nornflow show --catalogs
```

You'll see four catalogs:
- **Tasks**: Individual Nornir tasks, that represent a single automation action.
- **Workflows**: Sequences of tasks defined in YAML files that describe operations to be executed together.
- **Filters**: Nornir filters that allow you to select specific devices from the inventory.
- **Blueprints**: Reusable task collections that can be referenced across workflows.

## Running Tasks

### Simple Task Execution

```bash
# The 'hello_world' and 'greet_user' tasks below are sample tasks automatically created by the 'nornflow init' command.
# You can manually delete them from the 'tasks' folder after initialization if you wish.

# Run a task on all devices (note: no file extension needed for tasks)
nornflow run hello_world

# Run with arguments
nornflow run greet_user --args "greeting='Hello', user='Network Team'"
```

## Running Workflows

Workflows combine multiple tasks into a sequence. As an example, let's look at the sample hello_world.yaml that was created by `nornflow init`.

```yaml
workflow: 
  name: Hello World Workflow
  description: "A simple workflow that just works"
  tasks:
    - name: hello_world
    - name: greet_user
      args:
        greeting: "Hello"
        user: "you beautiful person"
```

Run it:

```bash
# Note: include the .yaml/.yml extension when running workflows
nornflow run hello_world.yaml
```

> **Important:** The `nornflow run` command handles both tasks and workflows:
> - Tasks: Use just the name without extension (`nornflow run task_name`)
> - Workflows: Include the .yaml/.yml extension (`nornflow run workflow_name.yaml`)
> 
> This distinction helps NornFlow determine whether to run a single task or a multi-task workflow.

## Working with Real-World Use Case

This section walks through a **hypothetical scenario** that represents a typical real-world use case. You can adapt these steps to your own environment and requirements.

### 1. Example Nornir inventory (`nornir_configs/inventory.yaml`):

```yaml
simple_inventory:
  hosts:
    router1:
      hostname: 192.168.1.1
      platform: ios
      username: admin
      password: secret
    switch1:
      hostname: 192.168.1.2
      platform: nxos
      username: admin
      password: secret
```

### 2. Configure Nornir (config.yaml):

```yaml
inventory:
  plugin: SimpleInventory
  options:
    host_file: "nornir_configs/inventory.yaml"

runner:
  plugin: threaded
  options:
    num_workers: 10
```

### 3. Verify NornFlow settings (nornflow.yaml):

NornFlow's settings file is created with sensible defaults by running `nornflow init`. You are encouraged to use these defaults, but feel free to modify the settings to best fit your scenario or use case.

**The following is the sample nornflow.yaml created:**

```yaml
nornir_config_file: "nornir_configs/config.yaml"
local_tasks:
  - "tasks"
local_workflows:
  - "workflows"
local_filters:
  - "filters"
local_hooks:
  - "hooks"
local_blueprints:
  - "blueprints"
imported_packages: []
dry_run: False
failure_strategy: "skip-failed"
processors:
  - class: "nornflow.builtins.DefaultNornFlowProcessor"
vars_dir: "vars"
```

### 4. Create a network automation workflow (`workflows/backup_configs.yaml`):

```yaml
workflow:
  name: "Backup Device Configs"
  description: "Backup configurations from all network devices"
  tasks:
    - name: netmiko_send_command
      args:
        command_string: "show running-config"
      set_to: "running_config"
    
    - name: write_file
      args:
        filename: "backups/{{ host.name }}_config.txt"
        content: "{{ running_config }}"
```

Run it:
```bash
nornflow run backup_configs.yaml
```

## Using Variables

### Workflow-Level Variables

Create `workflows/vlan_config.yaml`:

```yaml
workflow:
  name: "Configure VLANs"
  vars:
    vlan_id: 100
    vlan_name: "SERVERS"
  tasks:
    - name: configure_vlan
      args:
        id: "{{ vlan_id }}"
        name: "{{ vlan_name }}"
```

### Dynamic Variables with Jinja2

Set variables dynamically during workflow execution:

```yaml
# vlan_config.yaml
workflow:
  name: "Dynamic Device Configuration"
  tasks:
    - name: set
      args:
        device_type: "{% if host.platform == 'ios' %}Cisco IOS{% else %}Other Platform{% endif %}"
        config_mode: "{% if host.groups[0] == 'routers' %}router{% else %}switch{% endif %}"

    - name: echo
      args:
        msg: "Configuring {{ device_type }} in {{ config_mode }} mode for {{ host.name }}"
```

### Override Variables from CLI

```bash
nornflow run vlan_config.yaml --vars "vlan_id=200,vlan_name='WORKSTATIONS'"
```

## Using Blueprints

Blueprints are reusable collections of tasks that you can reference across workflows.

### Create a Blueprint

Create `blueprints/network_checks.yaml`:

```yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show version"
    set_to: version_output
  
  - name: netmiko_send_command
    args:
      command_string: "show interfaces status"
    set_to: interfaces_output
```

### Use in Workflow

Reference the blueprint in your workflow:

```yaml
workflow:
  name: "Device Health Check"
  tasks:
    - blueprint: network_checks.yaml
    - name: write_file
      args:
        filename: "reports/{{ host.name }}_health.txt"
        content: "{{ version_output }}\n{{ interfaces_output }}"
```

> **Note:** Blueprint references require the file extension (`.yaml` or `.yml`). See the [Blueprints Guide](blueprints_guide.md) for advanced features like conditional inclusion, nesting, and dynamic selection.

## Filtering Inventory

### Built-in Filters

```bash
# Filter by platform
nornflow run show_version --inventory-filters "platform='ios'"

# Combine filters
nornflow run backup_config --inventory-filters "platform='ios', groups=['core', 'dist']"
```

### Workflow-Level Filters

Target specific devices in your workflow:

```yaml
workflow:
  name: "Update Routers Only"
  inventory_filters:
    groups: ["routers"]
  tasks:
    - name: echo
      args:
        msg: "Updating router: {{ host.name }}"
```

### Quick Custom Filter

You can create and use your own custom python filters for trimming down the inventory that a workflow/task should run against. For example, here is a `filters/service_filter.py`:

```python
from nornir.core.inventory import Host

def filter_by_service(host: Host, service: str) -> bool:
    """Filter hosts by active service.
    
    Checks if a service is in the host's active_services list.
    """
    services = host.data.get("active_services", [])
    return service in services
```

Using it:

```bash
nornflow run service_check --inventory-filters "filter_by_service={'service': 'bgp'}"
```

## Useful Commands

```bash
# Show available tasks, workflows, filters, and blueprints (catalog)
nornflow show --catalogs

# Show specific catalogs
nornflow show --tasks
nornflow show --filters
nornflow show --workflows
nornflow show --blueprints

# Show current NornFlow settings
nornflow show --settings

# Show current Nornir configs
nornflow show --nornir-configs

# Show all information (catalogs, settings, configs)
nornflow show --all

# Dry run (see what would happen)
nornflow run my_workflow.yaml --dry-run
```

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
</td>
<td width="33%" align="center" style="border: none;">
<a href="./core_concepts.md">Next: Core Concepts →</a>
</td>
<td width="33%" align="right" style="border: none;">
</td>
</tr>
</table>

</div>