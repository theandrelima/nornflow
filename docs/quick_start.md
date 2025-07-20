# Quick Start Guide

## Table of Contents
- [Installation](#installation)
- [Your First NornFlow Project](#your-first-nornflow-project)
- [Running Tasks](#running-tasks)
- [Running Workflows](#running-workflows)
- [Working with Real Devices](#working-with-real-devices)
- [Using Variables](#using-variables)
- [Filtering Inventory](#filtering-inventory)
- [Common Patterns](#common-patterns)
- [Useful Commands](#useful-commands)

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

Before running any workflows, you **must initialize a NornFlow project** inside a folder.  
This folder becomes your NornFlow workspace, and all NornFlow commands should be run from within it.

```bash
mkdir my_nornflow_project
cd my_nornflow_project
nornflow init
```

This creates:
- 📁 tasks - Where your Nornir tasks should live
- 📁 workflows - Holds YAML workflow definitions  
- 📁 nornir_configs - Nornir configuration
- 📄 nornflow.yaml - NornFlow settings

### 2. Check What's Available

```bash
nornflow show --catalog
```

You'll see three catalogs:
- **Tasks**: Individual automation actions
- **Workflows**: Sequences of tasks
- **Nonrnir Filters**: Ways to select specific devices

Run it:
```bash
nornflow run hello.yaml
```

## Running Tasks

### Simple Task Execution

# if you ran 'nornflow init' then a sample 'hello_world' task should have been created along with a 'tasks' folder in your project's root.

```bash
# The 'hello_world' and 'greet_user' tasks below are sample tasks automatically created by the 'nornflow init' command.
# You can manually delete them from the 'tasks' folder if you wish.

# Run a task on all devices (note: no file extension needed for tasks)
nornflow run hello_world

# Run with arguments
nornflow run greet_user --args "greeting='Hello', user='Network Team'"
```

## Running Workflows

Workflows combine multiple tasks. After running `nornflow init`, a sample workflow file will be created for you: `workflows/hello_world.yaml`.

Here is what the sample workflow looks like:

```yaml
workflow: 
  name: Hello World Playbook
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
# Note: include the .yaml/.yml extension for workflows
nornflow run hello_world.yaml
```

> **Important:** The `nornflow run` command handles both tasks and workflows:
> - Tasks: Use just the name without extension (`nornflow run task_name`)
> - Workflows: Include the .yaml/.yml extension (`nornflow run workflow_name.yaml`)
> 
> This distinction helps NornFlow determine whether to run a single task or a multi-task workflow.

## Working with Real Devices

### 1. Example Nornir inventory (`nornir_configs/inventory.yaml`):

```yaml
simple_inventory:
  hosts:
    router1:
      hostname: 192.168.1.1
      platform: ios
      groups:
        - routers
    switch1:
      hostname: 192.168.1.10
      platform: nxos_ssh
      groups:
        - switches
  groups:
    routers:
      username: admin
    switches:
      username: admin
```

### 2. Configure Nornir (`nornir_configs/config.yaml`):

```yaml
inventory:
  plugin: SimpleInventory
  options:
    host_file: inventory.yaml
```

### 3. Verify NornFlow settings (`nornflow.yaml`):

```yaml
# Path for Nornir's config file
nornir_config_file: "nornir_configs/config.yaml"

# Task directories to scan
local_tasks_dirs:
  - "tasks"

# Workflow directories to scan  
local_workflows_dirs:
  - "workflows"

# Filter directories to scan
local_filters_dirs:
  - "filters"

# Variables directory
vars_dir: "vars"
```

### 4. Create a network workflow (`workflows/backup_configs.yaml`):

```yaml
workflow:
  name: "Backup Device Configs"
  tasks:
    - name: netmiko_send_command
      args:
        command_string: "show running-config"
      set_to: config_output
    
    - name: write_file
      args:
        filename: "backups/{{ host.name }}_config.txt"
        content: "{{ config_output.result }}"
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
workflow:
  name: "Dynamic Device Configuration"
  tasks:
    - name: set
      args:
        device_type: "{% if host.platform == 'ios' %}Cisco IOS{% else %}Other Platform{% endif %}"
        config_mode: "{% if host.groups[0] == 'routers' %}router{% else %}switch{% endif %}"

    - name: echo
      args:
        message: "Configuring {{ device_type }} in {{ config_mode }} mode for {{ host.name }}"
```

### Override Variables from CLI

```bash
nornflow run vlan_config.yaml --vars "vlan_id=200,vlan_name='WORKSTATIONS'"
```

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
        message: "Updating router: {{ host.name }}"
```

### Quick Custom Filter

Create `filters/service_filter.py`:

```python
from nornir.core.inventory import Host

def filter_by_service(host: Host, service: str) -> bool:
    """Filter hosts by active service.
    
    Checks if a service is in the host's active_services list.
    """
    services = host.data.get("active_services", [])
    return service in services
```

Use it:

```bash
nornflow run service_check --inventory-filters "filter_by_service='bgp'"
```

## Useful Commands

```bash
# Show available tasks, workflows, and filters (catalog)
nornflow show --catalog

# Show current NornFlow settings
nornflow show --settings

# Show current Nornir configs
nornflow show --nornir-configs

# Show all information (catalog, settings, configs)
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