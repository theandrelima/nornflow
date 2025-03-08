# Writing Workflows

Workflows in NornFlow are defined using YAML files. Such files contain the configuration needed to execute sequences of tasks on network devices. Here we explain how to write workflow YAML files correctly.  

## Table of Contents
- [Basic Structure](#basic-structure)
- [Required and Optional Fields](#required-and-optional-fields)
  - [Required Fields](#required-fields)
  - [Optional Fields](#optional-fields)
- [Summary of Fields & Types](#summary-of-fields--types)
- [Inventory Filtering](#inventory-filtering)
  - [Special NornFlow Filters](#special-nornflow-filters)
  - [Direct Attribute Filtering](#direct-attribute-filtering)
  - [Filter Behavior](#filter-behavior)
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
    hosts: [] # Included for completeness – can be omitted if not used
    groups: []  # Included for completeness – can be omitted if not used
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
    - **hosts**: List of hostnames to include (optional, list of strings)
    - **groups**: List of group names to include (optional, list of strings)
    - **Any attribute name**: Any attribute from your host data (optional, value of appropriate type)
  - **tasks**:
    - **args**: Arguments to pass to the task function when it is called (optional, dictionary)


## Summary of Fields & Types

| Field                            | Mandatory | Type               | Description                     |
|----------------------------------|-----------|--------------------|---------------------------------|
| workflow                         | Yes       | Object             | Top-level workflow definition   |
| workflow.name                    | No        | String             | The name of the workflow        |
| workflow.description             | No        | String             | Description of the workflow     |
| workflow.inventory_filters       | No        | Object             | Filters for device selection    |
| workflow.inventory_filters.hosts | No        | List of strings    | Host names to include           |
| workflow.inventory_filters.groups| No        | List of strings    | Group names to include          |
| workflow.inventory_filters.*     | No        | Any                | Any host attribute to filter on |
| workflow.tasks                   | Yes       | List of dictionaries | List of tasks to execute      |
| workflow.tasks[].name            | Yes       | String             | The name of the task            |
| workflow.tasks[].args            | No        | Dictionary         | Arguments to pass to the task   |

## Inventory Filtering
NornFlow provides flexible inventory filtering capabilities:

### Special NornFlow Filters
- **hosts** - List of host names to include (matches any in list)
- **groups** - List of group names to include (matches any in list)

### Direct Attribute Filtering
Besides the special filter types, you can use any host attribute as a filter key. For example:
```yaml
inventory_filters:
  platform: "ios"        # Filter devices with platform="ios"
  vendor: "cisco"        # Filter devices with vendor="cisco"
  site_code: "nyc"       # Filter devices with site_code="nyc"
```

### Filter Behavior
1. Special filters (`hosts` & `groups`) are applied first, in the order they appear
2. Direct attribute filters are applied afterward
3. Multiple filters are combined with AND logic - only hosts matching ALL criteria are included

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
    hosts:
      - router1
      - router2
    groups:
      - cisco_routers
    platform: "ios"
    vendor: "cisco"
    site_code: "hq"

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

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./nornflow_and_workflows.md">← Previous: NornFlow & Workflows</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./feature_roadmap.md">Next: Feature Roadmap →</a>
</td>
</tr>
</table>

</div>