# NornFlow Core Concepts

## Table of Contents
- [Introduction](#introduction)
- [Architecture Overview](#architecture-overview)
  - [Component Relationships](#component-relationships)
  - [Execution Flow](#execution-flow)
- [Project Structure](#project-structure)
- [Settings & Configuration](#settings--configuration)
  - [Configuration Files](#configuration-files)
  - [Multi-Environment Configuration](#multi-environment-configuration)
- [Catalogs](#catalogs)
  - [Task Catalog](#task-catalog)
  - [Workflow Catalog](#workflow-catalog)
  - [Filter Catalog](#filter-catalog)
  - [Blueprint Catalog](#blueprint-catalog)
  - [Catalog Discovery](#catalog-discovery)
- [Domains](#domains)
  - [What is a Domain?](#what-is-a-domain)
  - [Domain Variables](#domain-variables)
  - [Multiple Workflow Roots](#multiple-workflow-roots)
- [Blueprints](#blueprints)
- [Writing Workflows](#writing-workflows)
  - [Workflow Structure](#workflow-structure)
  - [Task Definition](#task-definition)
  - [Task Arguments & Results](#task-arguments--results)
- [Inventory Filtering](#inventory-filtering)
  - [Types of Filters](#types-of-filters)
  - [Filter Behavior](#filter-behavior)
  - [Ways to Define Filter Parameters](#ways-to-define-filter-parameters)
  - [Creating Custom Filters](#creating-custom-filters)
- [Hooks System](#hooks-system)
  - [What are Hooks?](#what-are-hooks)
  - [Built-in Hooks](#built-in-hooks)
- [Processors](#processors)
  - [What Processors Do](#what-processors-do)
  - [Processor Precedence](#processor-precedence)
- [Execution Model](#execution-model)
- [Failure Strategies (Summary)](#failure-strategies-summary)
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
    return Result(host=task.host, result=f"Created VLAN {vlan_id}")

# DECLARATIVE task - tells the system WHAT the end state should be
def ensure_vlan(task: Task, vlan_id: int, vlan_name: str) -> Result:
    """Ensures a VLAN exists with the specified configuration."""
    # Logic to check if VLAN exists and create if needed
    return Result(host=task.host, result=f"VLAN {vlan_id} is present")
```

Both tasks can be used identically in NornFlow workflows:

```yaml
workflow:
  name: "VLAN Management"
  tasks:
    - name: create_vlan    # Imperative approach
      args:
        vlan_id: 100
        vlan_name: "Users"
    
    # OR
    
    - name: ensure_vlan    # Declarative approach
      args:
        vlan_id: 100
        vlan_name: "Users"
```

The choice between imperative and declarative task implementation is up to the task developer, not NornFlow itself.

## Architecture Overview

NornFlow's architecture consists of several components working together in a layered design:

```
┌─────────────────────────────────────────────────────────┐
│                    NornFlow                             │ ← Main Orchestrator
└──┬──────────────────┬──────────────────┬────────────────┘    - Controls the entire workflow execution
   │                  │                  │                     - Discovers and catalogs tasks/workflows/filter
   ▼                  ▼                  ▼                     - Manages configuration
┌─────────────┐  ┌─────────────┐     ┌────────────┐
│WorkflowModel│  │NornirManager│ ◄───│NornFlowVars│        ← Supporting Components
└──┬──────────┘  └───┬─────┬───┘     │ Manager    │           - Data modeling
   │               ▲ |     │         └────────────┘           - Nornir integration
   ▼               │ |     ▼               ▲                  - Variable management
┌─────────┐        │ |  ┌───────┐          │                  - Processors management
│TaskModel│───┐────┘ |  │Nornir │          │
└─────────┘   │      |  └───────┘          │
              │      |      ▲              │
              │      ▼      |              │
              │    ┌─────────────┐         │
              │    │ Processors  │         │             ← Processors are applied to the Nonrnir object
              │    │  - Vars     |         |               by NornirManager, as part of the processing
              |    |  - Hooks    │         │               orchestrated by the NornFlow object.
              │    │  - Failure  │         │
              │    │  - Default  │         │
              │    └─────────────┘         │
              └────────────────────────────┘
```
Notice how `Nornir` is the fundamental block where all paths lead to in the above diagram.

### Component Relationships

**NornFlow (Central Orchestrator)**
- Serves as the main entry point and controller for the entire system
- Creates and manages the primary components (WorkflowModel, NornirManager, NornFlowVarsManager)
- Coordinates the execution flow between components
- Provides discovery and cataloging of tasks, workflows, filters, and blueprints
- Handles configuration management and variable resolution logic

**WorkflowModel (Pure Data Structure)**
- Contains the workflow definition as pure data (no execution logic)
- Holds tasks, variables, inventory filters, and failure strategy configurations
- Created by NornFlow from YAML files or dictionaries
- Contains TaskModel instances representing individual operations

**TaskModel (Execution Unit)**
- Represents a single task to be executed
- Inherits from `HookableModel` to support hook configurations
- Contains task name, arguments, and variable storage instructions
- Uses both `NornirManager` and `NornFlowVarsManager` during execution
- Validates task definition structure and hook compatibility

**NornirManager (Integration Bridge)**
- Provides an abstraction layer over Nornir
- Creates and configures the Nornir instance
- Manages inventory filtering and device connections
- Handles processor attachment to Nornir
- Receives execution results from TaskModel instances

**NornFlowVarsManager (Variable System)**
- Manages variable contexts for all devices
- Handles variable resolution and Jinja2 template rendering
- Maintains isolation between device contexts
- Provides variable lookup and storage throughout execution
- Interfaces with Nornir for host-specific data

**Nornir (Execution Engine)**
- The underlying engine where execution actually happens
- Manages device connections and parallel execution
- Provides the core task execution framework
- Maintains inventory and execution results
- Used by both NornirManager and TaskModel

### Execution Flow

1. **Initialization**: NornFlow loads settings and builds catalogs of tasks, workflows, filters, and blueprints
2. **Workflow Loading**: A YAML workflow is parsed into a WorkflowModel with nested TaskModel instances
3. **Component Creation**: NornFlow creates the NornirManager and NornFlowVarsManager
4. **Inventory Filtering**: NornFlow applies filters through NornirManager to select target devices
5. **Task Execution Loop**: For each TaskModel in the workflow:
   - TaskModel uses NornirManager to execute on target devices
   - TaskModel uses NornFlowVarsManager to resolve variables and store results
6. **Result Processing**: NornFlow interfaces with Processors to format and display results

This architecture ensures clear separation between:
- Orchestration logic (NornFlow)
- Data structures (pydantic-serdes models: WorkflowModel, TaskModel)
- Execution mechanisms (NornirManager, Nornir)
- Variable management (NornFlowVarsManager)

All components ultimately interact with Nornir, which serves as the foundation for actual task execution.

## Project Structure

A typical NornFlow project follows this structure:

```
my_project/
├── nornflow.yaml           # NornFlow configuration
├── nornir_config.yaml      # Nornir configuration
├── inventory.yaml          # Device inventory
├── blueprints/             # Reusable task collections
│   ├── backup_tasks.yaml
│   └── validation_tasks.yaml
├── workflows/              # Workflow definitions
│   ├── backup/             # Domain: "backup"
│   │   └── daily_backup.yaml
│   └── provision/          # Domain: "provision"
│       └── new_site.yaml
├── tasks/                  # Custom Nornir tasks
│   └── my_tasks.py
├── filters/                # Custom filter functions
│   └── site_filters.py
├── hooks/                  # Custom hooks
│   └── custom_hook.py
└── vars/                   # Variable files
    ├── defaults.yaml       # Global variables
    ├── backup/             # Domain variables
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
3. **Default**: nornflow.yaml in current directory

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
local_workflows: ["workflows", "dev_workflows"]

# nornflow-prod.yaml
nornir_config_file: "configs/nornir-prod.yaml"
dry_run: false
local_workflows: ["workflows"]
local_tasks: ["tasks"]
local_filters: ["filters"]
local_hooks: ["hooks"]
local_blueprints: ["blueprints"]
```

## Catalogs

NornFlow automatically discovers and builds catalogs of available tasks, workflows, filters, and blueprints based on your configuration. These catalogs are central to NornFlow's operation, allowing you to reference these NornFlow assets with ease throughout workflows.

### Task Catalog

The task catalog contains all available Nornir tasks that can be used in workflows. Tasks are discovered from:

1. **Built-in tasks** - Always available (e.g., `echo` & `set`)
2. **Local directories** - Specified in `local_tasks` setting
3. **Imported packages** - *(Planned feature, not yet implemented)*

```yaml
# nornflow.yaml
local_tasks:
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

The workflow catalog contains all discovered workflow YAML files. Workflows are discovered from directories specified in `local_workflows`:

```yaml
# nornflow.yaml
local_workflows:
  - "workflows"
  - "../shared_workflows"
```

All files with `.yaml` or `.yml` extensions in these directories (including subdirectories) are considered workflows.

### Filter Catalog

The filter catalog contains inventory filter functions that can be used in workflow definitions. Filters are discovered from:

1. **Built-in filters** - currently `hosts` and `groups` filters
2. **Local directories** - Specified in `local_filters` setting

```yaml
# nornflow.yaml
local_filters:
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

### Blueprint Catalog

The blueprint catalog contains all discovered blueprint YAML files. Blueprints are discovered from directories specified in `local_blueprints`:

```yaml
# nornflow.yaml
local_blueprints:
  - "blueprints"
  - "../shared_blueprints"
```

All files with `.yaml` or `.yml` extensions in these directories (including subdirectories) are considered blueprints.

### Catalog Discovery

NornFlow performs recursive searches in all configured directories:

- **Automatic discovery** happens during NornFlow initialization
- **Name conflicts** - NornFlow prevents custom or imported tasks/filters to override built-in ones. However later custom or imported discoveries will override earlier ones. 
- **View catalogs** - Use `nornflow show --catalogs` to see all discovered items, or specific `--tasks`, `--filters`, `--workflows`, and `--blueprints` options.

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
local_workflows:
  - "core_workflows"
  - "customer_workflows"
```

Domain resolution:
- `core_workflows/backup/daily.yaml` → Domain: "backup"
- `customer_workflows/backup/custom.yaml` → Domain: "backup" (same domain!)
- Both share variables from `vars/backup/defaults.yaml`

## Blueprints

Blueprints are reusable collections of tasks that can be referenced within workflows. They enable code reuse, modularity, and maintainability by defining common task sequences once and using them across multiple workflows.

**Key characteristics:**
- Contain **only** a tasks list (no workflow metadata)
- Referenced by name or path in workflows
- Support nesting (blueprints can reference other blueprints)
- Expanded during workflow loading (assembly-time)

**Basic example:**

```yaml
# blueprints/pre_checks.yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show version"
  - name: netmiko_send_command
    args:
      command_string: "show interfaces status"

# workflows/deploy.yaml
workflow:
  name: "Deploy Configuration"
  tasks:
    - blueprint: pre_checks.yaml
    - name: apply_config
```

For comprehensive coverage including conditional inclusion, nested blueprints, dynamic selection, variable resolution, and composition strategies, see the [Blueprints Guide](./blueprints_guide.md).

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
        vlan_ids: "{{ vlan_range }}"
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
      msg: "Device version is {{ version_info }}"
```

## Inventory Filtering

NornFlow provides powerful and flexible inventory filtering capabilities that determine which devices your workflow will target.

### Types of Filters

#### 1. Built-in NornFlow Filters
- **hosts** - List of host names to include (matches any in list)
- **groups** - List of group names to include (matches any in list)

#### 2. Custom Filter Functions
NornFlow can use custom filter functions defined by your `local_filters` setting (configured in nornflow.yaml). These functions provide advanced filtering logic beyond simple attribute matching.

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
  site_filter:  # passing 2 keyword args to a 'site_filter' in the Filters Catalog
    region: "west"
    criticality: "high"
```

#### List Parameters
```yaml
inventory_filters:
  complex_filter: ["arg1", "arg2", "arg3"]  # passing 3 positional args to 'complex_filter'
```

#### Single Value Parameter
```yaml
inventory_filters:
  in_region: "east"  # passing a single value to 'in_region' filter
```

### Creating Custom Filters

Custom filters MUST:
1. Be defined in python modules within directories specified by `local_filters`
2. Contain a `host` keyword as the first parameter
3. Return a boolean value
4. Include proper type annotations (for automatic discovery)

**Example custom filter:**

```python
from nornir.core.inventory import Host

def in_region(host: Host, region: str) -> bool:
    """Filter hosts by region.
    
    Args:
        host: The Nornir host object to check
        region: Region name to match
        
    Returns:
        bool: True if host's region matches
    """
    return host.data.get("region") == region

def has_capability(host: Host, capability: str, min_version: str = "1.0") -> bool:
    """Filter hosts by capability and minimum version.
    
    Args:
        host: The Nornir host object to check
        capability: Capability name
        min_version: Minimum version required (default: "1.0")
        
    Returns:
        bool: True if host has capability with sufficient version
    """
    caps = host.data.get("capabilities", {})
    if capability not in caps:
        return False
    
    return caps[capability] >= min_version
```

Use in a workflow:
```yaml
workflow:
  name: "Regional Update"
  inventory_filters:
    in_region: "east"
    has_capability:
      capability: "bgp"
      min_version: "4.0"
  # ...
```

## Hooks System

### What are Hooks?

Hooks are a task extension mechanism in NornFlow that allow you to modify task behavior without changing the task implementation itself. Hooks are configured at the task level in workflows and are completely optional.

Hooks enable:
- Conditional execution of tasks on specific hosts
- Suppression of task output
- Storage of task results as runtime variables
- Extension of task behavior through custom implementations

Under the hood, hooks are implemented as Nornir Processors and are orchestrated by the `NornFlowHookProcessor`, which manages hook registration and execution throughout the task lifecycle.

### Built-in Hooks

NornFlow provides three built-in hooks:

**`if` Hook - Conditional Execution**

Controls whether a task executes on specific hosts based on filter functions or Jinja2 expressions.

```yaml
tasks:
  # Using filter function
  - name: ios_specific_task
    if:
      platform: "ios"
  
  # Using Jinja2 expression
  - name: conditional_backup
    if: "{{ host.data.backup_enabled and environment == 'prod' }}"
```

**`set_to` Hook - Result Storage**

Captures task execution results and stores them as runtime variables for use in subsequent tasks.

```yaml
tasks:
  # Store complete result
  - name: get_facts
    set_to: device_facts
  
  # Extract specific data from result
  - name: get_environment
    set_to:
      cpu_usage: "environment.cpu.0.%usage"
      serial: "serial_number"
  
  # Use stored data in later tasks
  - name: echo
    args:
      msg: "CPU: {{ cpu_usage }}%, Serial: {{ serial }}"
```

**`shush` Hook - Output Suppression**

Suppresses task output printing while preserving result data for other hooks and processors.

```yaml
tasks:
  # Static suppression
  - name: noisy_task
    shush: true
    set_to: task_result  # Result still available
  
  # Dynamic suppression based on variables
  - name: conditional_quiet
    shush: "{{ debug_mode == false }}"
```

For comprehensive documentation on hooks, including creating custom hooks, see the Hooks Guide.

## Processors

Processors are middleware components that extend Nornir's task execution to provide features like:
- Variable substitution
- Result formatting
- Progress tracking
- Logging and reporting
- Failure handling
- Hook orchestration

### What Processors Do

Processors can hook into different task execution events:

- `task_started` - Called when a task begins globally
- `task_completed` - Called when a task completes globally
- `task_instance_started` - Called before a task runs on a specific host
- `task_instance_completed` - Called after a task completes on a specific host
- `subtask_instance_started` - Called before a subtask on a specific host
- `subtask_instance_completed` - Called after a subtask on a specific host

NornFlow provides built-in processors and allows custom ones:

```yaml
# nornflow.yaml
processors:
  - class: "nornflow.builtins.DefaultNornFlowProcessor"
    args: {}
  - class: "my_package.CustomProcessor"
    args:
      option: "value"
```

**Built-in Processors:**
- `DefaultNornFlowProcessor`: Formats task output and tracks execution statistics
- `NornFlowVariableProcessor`: Handles variable resolution (always applied first)
- `NornFlowFailureStrategyProcessor`: Implements failure handling (always applied last)
- `NornFlowHookProcessor`: Orchestrates hook execution (automatically added when hooks are present)

The `NornFlowHookProcessor` manages a two-tier context system:
- **Workflow context**: Set once during initialization (vars_manager, filters_catalog, etc.)
- **Task-specific context**: Updated for each task (task_model, hooks for that task)

This processor is responsible for registering hooks and delegating lifecycle events to the appropriate hook instances.

### Processor Precedence

Processors are applied with this precedence (highest to lowest):

1. **CLI arguments** - Provided with `--processors` option
2. **Workflow-specific** - Defined in the workflow YAML
3. **Global settings** - Defined in nornflow.yaml
4. **Default processor** - Used if none specified

NornFlow includes two special processors that will ALWAYS be applied in this order:
1. `NornFlowVariableProcessor` (always first)
2. User-defined processors (in the exact order they are informed)
3. `NornFlowFailureStrategyProcessor` (always last)

> NOTE: The '*User-defined processors*' above may contain any number of processors, including (or not) the builtin `DefaultNornFlowProcessor`

## Execution Model

NornFlow's execution model follows these principles:

1. **Task Sequencing**
   - Tasks run in the order defined in the workflow
   - Each task completes on all hosts before the next begins
   - Variables set by tasks are available to subsequent tasks

2. **Parallel Host Execution**
   - Within each task, execution happens in parallel across hosts
   - Default concurrency is controlled by Nornir's `num_workers` setting

3. **Variable Isolation**
   - Each host has its own isolated variable context
   - Variables from one host can't affect others
   - Enables safe parallel execution

4. **Failure Handling**
   - Controlled by the configured failure strategy
   - See the Failure Strategies guide for details

## Failure Strategies (Summary)

NornFlow supports three failure handling strategies:

1. **skip-failed** (default)
   - Failed hosts are removed from subsequent tasks
   - Other hosts continue execution

2. **fail-fast**
   - Stops execution on first failure
   - Prevents further changes when issues are detected

3. **run-all**
   - All tasks run on all hosts regardless of failures
   - Useful for diagnostic or audit workflows

See the full Failure Strategies guide for details.

## Best Practices

1. **Structure workflows by domain**
   - Organize related workflows into domain folders
   - Use domain variables for shared settings

2. **Validate workflows before deployment**
   - Use dry-run mode: `nornflow run workflow.yaml --dry-run`
   - Review what NornFlow will do before making changes

3. **Follow consistent naming conventions**
   - Use descriptive names for tasks and workflows
   - Group related variables with common prefixes

4. **Use filtering effectively**
   - Apply precise inventory filters
   - Create custom filters for complex criteria

5. **Document your workflows**
   - Add descriptions to workflows
   - Include comments for complex task sequences

6. **Plan for failure**
   - Choose appropriate failure strategies
   - Implement verification tasks after changes

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./quick_start.md">← Previous: Quick Start</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./blueprints_guide.md">Next: Blueprints Guide →</a>
</td>
</tr>
</table>

</div>
