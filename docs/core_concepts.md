# NornFlow Core Concepts

## Table of Contents
- [Introduction](#introduction)
- [Architecture Overview](#architecture-overview)
  - [Component Relationships](#component-relationships)
  - [Execution Flow](#execution-flow)
- [Project Structure](#project-structure)
- [Settings & Configuration](#settings--configuration)
  - [Configuration Files](#configuration-files)
  - [Settings Resolution](#settings-resolution)
  - [Multi-Environment Configuration](#multi-environment-configuration)
- [Catalogs](#catalogs)
  - [Task Catalog](#task-catalog)
  - [Workflow Catalog](#workflow-catalog)
  - [Filter Catalog](#filter-catalog)
  - [Catalog Discovery](#catalog-discovery)
- [Domains](#domains)
  - [What is a Domain?](#what-is-a-domain)
  - [Domain Variables](#domain-variables)
  - [Multiple Workflow Roots](#multiple-workflow-roots)
- [Writing Workflows](#writing-workflows)
  - [Workflow Structure](#workflow-structure)
  - [Task Definition](#task-definition)
  - [Task Arguments & Results](#task-arguments--results)
- [Inventory Filtering](#inventory-filtering)
  - [Filter Types](#filter-types)
  - [Filter Application Order](#filter-application-order)
  - [Creating Custom Filters](#creating-custom-filters)
- [Processors](#processors)
  - [What Processors Do](#what-processors-do)
  - [Processor Configuration](#processor-configuration)
  - [Processor Precedence](#processor-precedence)
- [Execution Model](#execution-model)
- [Best Practices](#best-practices)

## Introduction

NornFlow is a workflow orchestration framework built on top of Nornir. It provides a declarative way to define and execute complex network automation workflows using YAML files, while leveraging Nornir's powerful inventory management and task execution capabilities.

This guide covers the fundamental concepts you need to understand to effectively use NornFlow.

## Declarative vs. Imperative


Before we go any further, there's an **important clarification** to be made about a rather 'hot topic' within the network-automation community:  
When we say NornFlow provides a *"declarative way to define workflows"* we're referring to the workflow structure and orchestration itself, not the individual tasks within those workflows. The declarative vs. imperative nature of each task depends entirely on how the task developer chose to implement it. NornFlow simply provides the framework to organize and execute these tasks in a predictable, YAML-defined manner.

**Example - Task Implementation Approaches**:

```python
# IMPERATIVE task - tells the system HOW to do something
def create_vlan(task: Task, vlan_id: int, vlan_name: str) -> Result:
    """Creates a VLAN by sending configuration commands."""
    commands = [
        f"vlan {vlan_id}",
        f"name {vlan_name}",
        "exit"
    ]
    # Sends commands regardless of current state
    result = task.run(netmiko_send_config, config_commands=commands)
    return Result(host=task.host, result=f"Created VLAN {vlan_id}")

# DECLARATIVE task - tells the system WHAT the end state should be
def ensure_vlan(task: Task, vlan_id: int, vlan_name: str) -> Result:
    """Ensures a VLAN exists with the specified configuration."""
    # First, check current state
    existing_vlans = task.run(get_vlans)
    
    if vlan_id in existing_vlans:
        if existing_vlans[vlan_id]['name'] == vlan_name:
            return Result(host=task.host, result=f"VLAN {vlan_id} already exists with correct name")
        else:
            # Update name if different
            task.run(netmiko_send_config, config_commands=[
                f"vlan {vlan_id}",
                f"name {vlan_name}"
            ])
            return Result(host=task.host, result=f"Updated VLAN {vlan_id} name to {vlan_name}")
    else:
        # Create VLAN if it doesn't exist
        task.run(netmiko_send_config, config_commands=[
            f"vlan {vlan_id}",
            f"name {vlan_name}"
        ])
        return Result(host=task.host, result=f"Created VLAN {vlan_id}")
```

Both tasks can be used identically in NornFlow workflows:

```yaml
workflow:
  name: "VLAN Management"
  tasks:
    - name: create_vlan      # Imperative approach
      args:
        vlan_id: 100
        vlan_name: "SERVERS"
        
    - name: ensure_vlan      # Declarative approach  
      args:
        vlan_id: 100
        vlan_name: "SERVERS"
```

The choice between imperative and declarative task implementation is up to the task developer, not NornFlow itself.

## Architecture Overview

NornFlow's architecture consists of three main components working together:

```
┌─────────────────┐
│    NornFlow     │ ← Orchestrator: Manages settings, catalogs, processors
└────────┬────────┘
         │ creates
┌────────┴────────┐
│ NornirManager   │ ← Bridge: Interfaces with Nornir, manages inventory
└────────┬────────┘
         │ uses
┌────────┴────────┐
│    Workflow     │ ← Executor: Runs tasks, applies filters, handles results
└─────────────────┘
```

### Component Relationships

**NornFlow (Orchestrator)**
- Loads and validates settings from nornflow.yaml
- Builds catalogs of available tasks, workflows, and filters
- Creates and configures NornirManager and Workflow instances
- Manages processor loading and precedence

**NornirManager (Bridge)**
- Creates and configures Nornir instances based on settings
- Provides abstracted access to Nornir's inventory
- Applies inventory filters
- Manages processor attachment to Nornir

**Workflow (Executor)**
- Parses workflow YAML definitions
- Executes tasks in sequence on filtered inventory
- Handles task results and variable management
- Applies workflow-specific processors

### Execution Flow

1. **Initialization**: NornFlow reads settings and builds catalogs
2. **Workflow Loading**: YAML workflow is parsed and validated
3. **Inventory Filtering**: Filters are applied to select target devices
4. **Task Execution**: Tasks run sequentially on each device
5. **Result Processing**: Processors format and display results

## Project Structure

A typical NornFlow project follows this structure:

```
my_project/
├── nornflow.yaml           # NornFlow configuration
├── nornir_config.yaml      # Nornir configuration
├── inventory.yaml          # Device inventory
├── workflows/              # Workflow definitions
│   ├── backup/             # Domain: "backup"
│   │   └── daily_backup.yaml
│   └── provision/          # Domain: "provision"
│       └── new_site.yaml
├── tasks/                  # Custom Nornir tasks
│   └── my_tasks.py
├── filters/                # Custom filter functions
│   └── site_filters.py
└── vars/                   # Variable files
    ├── defaults.yaml       # Global variables
    ├── backup/             # Domain-specific variables
    │   └── defaults.yaml
    └── provision/
        └── defaults.yaml
```

## Settings & Configuration

### Configuration Files

NornFlow uses two separate configuration files:

1. **nornflow.yaml** - NornFlow-specific settings
2. **nornir_config.yaml** - Standard Nornir configuration

This separation allows you to change NornFlow behavior without affecting Nornir configuration and vice versa.

### Settings Resolution

NornFlow finds its settings file in this order:

1. **Environment variable**: `NORNFLOW_SETTINGS=/path/to/config.yaml`
2. **CLI option**: `nornflow run --settings /path/to/config.yaml workflow.yaml`
3. **Default**: `./nornflow.yaml` in current directory

### Multi-Environment Configuration

To support multiple environments, create separate settings files:

```bash
my_project/
├── nornflow-dev.yaml
├── nornflow-prod.yaml
└── nornflow-staging.yaml
```

Select the appropriate file at runtime:

```bash
# Using environment variable
export NORNFLOW_SETTINGS=nornflow-prod.yaml
nornflow run backup.yaml

# Using CLI option
nornflow run --settings nornflow-dev.yaml test_workflow.yaml
```

**Example configurations:**

```yaml
# nornflow-dev.yaml
nornir_config_file: "configs/nornir-dev.yaml"
dry_run: true
local_workflows_dirs: ["workflows", "dev_workflows"]

# nornflow-prod.yaml
nornir_config_file: "configs/nornir-prod.yaml"
dry_run: false
local_workflows_dirs: ["workflows"]
```

## Catalogs

NornFlow automatically discovers and builds catalogs of available tasks, workflows, and filters based on your configuration. These catalogs are central to NornFlow's operation, allowing you to reference tasks and filters by name in your workflows.

### Task Catalog

The task catalog contains all available Nornir tasks that can be used in workflows. Tasks are discovered from:

1. **Built-in tasks** - Always available (e.g., `echo` & `set`)
2. **Local directories** - Specified in `local_tasks_dirs` setting
3. **Imported packages** - *(Planned feature, not yet implemented)*

```yaml
# nornflow.yaml
local_tasks_dirs:
  - "tasks"
  - "/shared/network_tasks"
```

Tasks must follow Nornir's task signature to be discovered and used in NornFlow.  
Your task function **must be properly type-annotated**, and the return type should be one of the following Nornir result types: `Result`, `AggregateResult`, or `MultiResult`.

**Example:**
```python
from nornir.core.task import Task, Result

def my_task(task: Task, **kwargs) -> Result:
    """Task description."""
    return Result(host=task.host, result="Success")
```

### Workflow Catalog

The workflow catalog contains all discovered workflow YAML files. Workflows are discovered from directories specified in `local_workflows_dirs`:

```yaml
# nornflow.yaml
local_workflows_dirs:
  - "workflows"
  - "../shared_workflows"
```

All files with `.yaml` or `.yml` extensions in these directories (including subdirectories) are considered workflows.

### Filter Catalog

The filter catalog contains inventory filter functions that can be used in workflow definitions. Filters are discovered from:

1. **Built-in filters** - currently `hosts` and `groups` filters
2. **Local directories** - Specified in `local_filters_dirs` setting

```yaml
# nornflow.yaml
local_filters_dirs:
  - "filters"
  - "../custom_filters"
```

Filter functions must accept a `Host` object as the first parameter and return a boolean. Type annotations are required for discovery - the first parameter must be typed as `Host` and the return type must be `bool`:

```python
from nornir.core.inventory import Host  # Import required

def site_filter(host: Host, region: str) -> bool:
    """Filter hosts by region."""
    return host.data.get("region") == region
```

### Catalog Discovery

NornFlow performs recursive searches in all configured directories:

- **Automatic discovery** happens during NornFlow initialization
- **Name conflicts** - NornFlow prevents custom or imported tasks/filters to override built-in ones. However later custom or imported discoveries will override earlier ones. 
- **View catalogs** - Use `nornflow show --catalogs` to see all discovered items, or specific `--tasks`, `--filters` and `--workflows` options.

**Discovery order:**
1. Built-in items are loaded first
2. Local directories are processed in the order specified
3. Each directory is searched recursively

## Domains

### What is a Domain?

A **domain** in NornFlow is a logical grouping mechanism for workflows and their associated variables. It's determined by the first-level subdirectory under any configured workflow root directory.

- **Domain = First-level subdirectory name** under any workflow root
- **Purpose**: Organize workflows and variables by functional area
- **Benefit**: Scope variables to specific automation areas

### Domain Variables

Domain-specific variables are loaded from `{vars_dir}/{domain}/defaults.yaml`:

```yaml
# vars/backup/defaults.yaml
retention_days: 30
backup_server: "backup.company.com"
compression: true
```

These variables are automatically available to all workflows within that domain.

### Multiple Workflow Roots

When using multiple workflow directories:

```yaml
# nornflow.yaml
local_workflows_dirs:
  - "core_workflows"
  - "customer_workflows"
```

Domain resolution:
- `core_workflows/backup/daily.yaml` → Domain: "backup"
- `customer_workflows/backup/custom.yaml` → Domain: "backup" (same domain!)
- Both share variables from `vars/backup/defaults.yaml`

## Writing Workflows

### Workflow Structure

Every workflow is a YAML file with a mandatory `workflow` top-level key:

```yaml
workflow:
  name: "Configure VLANs"        # Optional - descriptive name
  description: "Adds VLANs..."   # Optional - detailed description
  
  vars:                          # Optional - workflow variables
    vlan_range: [100, 110, 120]
    
  inventory_filters:             # Optional - device selection
    groups: ["switches"]
    
  processors:                    # Optional - custom processors
    - class: "mypackage.AuditProcessor"  # User-defined processor (not included)
    
  tasks:                         # REQUIRED - list of tasks
    - name: configure_vlans
      args:
        vlans: "{{ vlan_range }}"
```

### Task Definition

Tasks are the atomic units of work in a workflow:

```yaml
tasks:
  # Minimal task - just a name
  - name: gather_facts
  
  # Task with arguments
  - name: configure_interface
    args:
      interface: "GigabitEthernet0/1"
      description: "Uplink to {{ host.data.upstream_device }}"
      
  # Task with result capture
  - name: show_version
    set_to: version_info  # Stores result in 'version_info' variable
```

### Task Arguments & Results

**Passing Arguments:**
- Arguments are passed via the `args` dictionary
- Supports Jinja2 templating for dynamic values
- Can reference variables and host data

**Capturing Results:**
- Use `set_to` to store task results in variables
- Results are available to subsequent tasks
- Stored per-device in isolated contexts

**Example:**
```yaml
tasks:
  - name: show_version
    set_to: version_info  # Stores the result in the variable 'version_info'. The var will be either created or updated on a per-device context basis.

  - name: echo
    args:
      message: "Device version is {{ version_info }}"
```

## Inventory Filtering

NornFlow provides powerful and flexible inventory filtering capabilities that determine which devices your workflow will target.

### Types of Filters

#### 1. Built-in NornFlow Filters
- **hosts** - List of host names to include (matches any in list)
- **groups** - List of group names to include (matches any in list)

#### 2. Custom Filter Functions
NornFlow can use custom filter functions defined by your `local_filters_dirs` setting (configured in `nornflow.yaml`). These functions provide advanced filtering logic beyond simple attribute matching.

#### 3. Direct Attribute Filtering
As it is the case with Nornir, any host attribute can be used as a filter key for simple equality matching:
```yaml
inventory_filters:
  platform: "ios"        # Filter devices with platform="ios"
  vendor: "cisco"        # Filter devices with vendor="cisco"
  site_code: "nyc"       # Filter devices with site_code="nyc"
```

### Filter Behavior

1. Filters are applied sequentially in the order they appear in the YAML
2. Each filter further narrows down the inventory selection
3. Multiple filters are combined with AND logic - hosts must match ALL criteria to be included
4. When processing each key under `inventory_filters` in the YAML/dict, NornFlow first checks if it matches a custom filter function name in your filters catalog. If no matching filter function is found, NornFlow treats it as a direct attribute filter, checking for hosts with that attribute matching the specified value.

### Ways to Define Filter Parameters

When using custom filters, parameters can be provided in several ways:

#### Parameter-less Filters
```yaml
inventory_filters:
  is_active:  # a filter named 'is_acive' in the Filters Catalog that doesn't expect any parameters.
```

#### Dictionary Parameters
```yaml
inventory_filters:
  site_filter: # passing 2 keyword args to a 'site_filter' in the Filters Catalog
    region: "east"
    site_type: "campus"
```

#### Single Parameter as List or Value
```yaml
inventory_filters:
  in_subnets: ["10.1.0.0/24", "10.2.0.0/24"]  # List parameter
  exact_model: "C9300-48P"                    # Single value parameter
```

### Creating Custom Filters

Custom filters are Python functions that:
1. Take a `Host` object as their first parameter
2. Return `True` if the host should be included, `False` otherwise
3. Can accept additional parameters as needed

Place these functions in your filters directory (default: filters) for NornFlow to discover them.

### Example: Combined Filtering Strategy

```yaml
workflow:
  name: "Core Switch Upgrade"
  inventory_filters:
    groups: ["core_switches"]  # Applied first - selects only core switches
    platform: "ios-xe"         # Applied second - narrows to IOS-XE devices
    site_filter:               # Applied third - custom filter with parameters
      region: "east"
      priority: "high"
    os_version_lt: "17.3.4"    # Applied fourth - custom filter for version comparison
  tasks:
    - name: backup_configs
    - name: upgrade_os
```

## Processors

### What Processors Do

Processors are hooks into Nornir's task execution lifecycle. They can:
- Format task output
- Log execution details
- Collect metrics
- Handle errors
- Generate reports

### Processor Configuration

```yaml
# Global processors in nornflow.yaml
processors:
  - class: "nornflow.builtins.DefaultNornFlowProcessor"  # Built-in (included)
  - class: "mycompany.processors.AuditLogger"            # User-defined
    args:
      log_file: "/var/log/nornflow/audit.log"
      
# Workflow-specific processors
workflow:
  processors:
    - class: "nornflow.builtins.DefaultNornFlowProcessor"  # Built-in (included)
    - class: "mycompany.processors.SlackNotifier"          # User-defined
      args:
        webhook_url: "{{ SLACK_WEBHOOK_URL }}"
```

**Note:** Processors marked as "User-defined" are there for the sake of example and would have to be implemented by the developer.

### Processor Precedence

1. **CLI processors** (`--processors`) - Highest priority
2. **Workflow processors** - Override global processors
3. **Global processors** - From nornflow.yaml
4. **Default processor** - If nothing else specified

**Important:** When you specify processors at any level, you must explicitly include `DefaultNornFlowProcessor` if you want its functionality.

## Execution Model

Understanding NornFlow's execution model helps predict behavior:

1. **Sequential Task Execution**: Tasks run in order, one at a time
2. **Parallel Host Execution**: Each task runs on all hosts in parallel
3. **Isolated Variable Contexts**: Each host maintains its own variables
4. **Result Aggregation**: Task results are collected before proceeding

```
Task 1 → [Host A, Host B, Host C] (parallel)
         ↓ (wait for all)
Task 2 → [Host A, Host B, Host C] (parallel)
         ↓ (wait for all)
Task 3 → [Host A, Host B, Host C] (parallel)
```

## Best Practices

1. **Keep Workflows Focused**: One workflow should accomplish one logical goal
2. **Use Descriptive Names**: Both workflow and task names should be self-documenting
3. **Leverage Variables**: Use variables for reusable values and templates
4. **Test with Dry Run**: Always test workflows with `--dry-run` first
5. **Version Control**: Keep workflows in version control with meaningful commits
6. **Complex Logic in Python**: Write conditionals, loops, and complex logic in Python Nornir tasks rather than in YAML/Jinja2 to maintain readability and debuggability
7. **Document Complex Logic**: Add comments in YAML for complex filtering or logic
8. **Error Handling**: Use conditional logic to handle expected failures gracefully

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./quick_start.md">← Previous: Quick Start Guide</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./variables_basics.md">Next: Variables Basics →</a>
</td>
</tr>
</table>

</div>