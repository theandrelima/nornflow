# Writing Workflows

Workflows in NornFlow are defined using YAML files. Such files contain the configuration needed to execute sequences of tasks on network devices. Here we explain how to write workflow YAML files correctly.  

## Table of Contents
- [Basic Structure](#basic-structure)
- [Required and Optional Fields](#required-and-optional-fields)
  - [Required Fields](#required-fields)
  - [Optional Fields](#optional-fields)
- [Summary of Fields & Types](#summary-of-fields--types)
- [Inventory Filtering](#inventory-filtering)
  - [Types of Filters](#types-of-filters)
  - [Filter Behavior](#filter-behavior)
  - [Ways to Define Filter Parameters](#ways-to-define-filter-parameters)
  - [Creating Custom Filters](#creating-custom-filters)
  - [Example: Combined Filtering Strategy](#example-combined-filtering-strategy)
- [Workflow Processors](#workflow-processors)
  - [Processor Configuration](#processor-configuration)
  - [Processor Precedence](#processor-precedence)
  - [Example](#example)
- [Examples](#examples)
  - [Minimal Valid Workflow](#minimal-valid-workflow)
  - [Complete Workflow Example](#complete-workflow-example)

## Basic Structure
A workflow YAML file must have a top-level workflow key, which contains all the workflow configuration:

```yaml
workflow:
  name: "My Workflow"
  description: "Description of what this workflow does"
  inventory_filters:
    platform: "ios"  # Direct attribute filter example
  tasks:
    - name: "task_name"
    - name: "another_task"
      args:
        param1: "value1"
        param2: "value2"
```

## Required and Optional Fields
> NOTE: Mind the indentation below. It indicates what fields are expected to be nested under what other fields.

### Required Fields

- **workflow**: Must exist as the top-level key that indicates this is a workflow definition  
  - **tasks**: A list of tasks to be executed in sequence  
    - **name**: The name of the task (required for each task)


### Optional Fields
- **workflow**:
  - **name**: A descriptive name for the workflow (optional, string)
  - **description**: A detailed description of what the workflow does (optional, string)
  - **inventory_filters**: Filters to determine which devices the tasks will run on (optional)
    - **hosts**: List of hostnames to include (built-in filter, list of strings)
    - **groups**: List of group names to include (built-in filter, list of strings)
    - **<custom_filter>**: A filter function from your filters catalog
      - Can be defined with no parameters, a dictionary of parameters, a single value, or a list
    - **<attribute_name>**: Any attribute from your host data for direct filtering (value must match the attribute type)
  - **processors**: List of processor configurations to use for this workflow (optional)
    - **class**: Full Python import path to the processor class
    - **args**: Dictionary of keyword arguments passed to the processor constructor
  - **tasks**:
    - **args**: Arguments to pass to the task function when it is called (optional, dictionary)


## Summary of Fields & Types

| Field                                   | Mandatory | Type                       | Description                                   |
|----------------------------------------|-----------|----------------------------|-----------------------------------------------|
| workflow                                | Yes       | Object                     | Top-level workflow definition                 |
| workflow.name                           | No        | String                     | The name of the workflow                      |
| workflow.description                    | No        | String                     | Description of the workflow                   |
| workflow.inventory_filters              | No        | Object                     | Filters for device selection                  |
| workflow.inventory_filters.hosts        | No        | List of strings            | Host names to include  (built-in filter)      |
| workflow.inventory_filters.groups       | No        | List of strings            | Group names to include  (built-in filter)     |
| workflow.inventory_filters.<custom_filter> | No    | Boolean/Dict/List/Value    | Custom filter with optional parameters         |
| workflow.inventory_filters.<attribute>  | No        | Any                        | Direct attribute filter for host selection    |
| workflow.processors                     | No        | List of objects            | List of processor configurations              |
| workflow.processors[].class             | Yes       | String                     | Python import path to processor class         |
| workflow.processors[].args              | No        | Dictionary                 | Arguments to pass to processor constructor    |
| workflow.tasks                          | Yes       | List of dictionaries       | List of tasks to execute                      |
| workflow.tasks[].name                   | Yes       | String                     | The name of the task                          |
| workflow.tasks[].args                   | No        | Dictionary                 | Arguments to pass to the task                 |

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

## Workflow Processors

You can define custom processors for a specific workflow to control task output formatting, execution tracking, and more.

### Processor Configuration

Processors are configured using these fields:
- **class**: The full Python import path to the processor class
- **args**: Optional dictionary of keyword arguments for the processor's constructor

### Processor Precedence

When using processors in workflows:
1. Workflow-specific processors override global processors defined in nornflow.yaml
2. CLI processors (specified with `--processors`) override workflow-specific processors
3. If no processors are defined, the DefaultNornFlowProcessor is used

### Example

```yaml
workflow:
  name: "My Workflow"
  processors:
    - class: "nornflow.builtins.DefaultNornFlowProcessor"
      args: {}
    - class: "mypackage.CustomLogProcessor"
      args:
        log_file: "workflow-output.log"
        verbose: true
  tasks:
    - name: my_task
```

For more details on processors, see the Processors section in the settings documentation.

## Examples

## Minimal Valid Workflow
```yaml
workflow:
  tasks:
    - name: my_task
```

## Complete Workflow Example

> NOTE: tasks need to exist in the TASKS CATALOG, otherwise an error would occur. The example below is hypothetical, in the sense that it just assumes the Nornir Tasks listed exist.

```yaml
workflow:
  name: "Configure Interfaces"
  description: "Configures interfaces on network devices"
  inventory_filters:
    groups:
      - igp-routers
    platform: "ios"
    vendor: "cisco"
    site_code: "hq"
  processors:
    #since 'processors' is defined, to still avail of DefaultNornFlowProcessor, it needs to be explicitly included in the list
    - class: "nornflow.builtins.DefaultNornFlowProcessor"
    - class: "mypackage.CustomProcessor"
      args:
        verbose: true
        log_level: "INFO"
  tasks:
    - name: gather_facts

    - name: configure_interface
      args:
        interface: "GigabitEthernet0/1"
        description: "Uplink to Core"
        ip_address: "192.168.1.1"
        subnet_mask: "255.255.255.0"

    - name: save_config
```

<div align="center">
  
## Navigation

<a href="./nornflow_and_workflows.md">← Previous: NornFlow & Workflows</a>

</div>