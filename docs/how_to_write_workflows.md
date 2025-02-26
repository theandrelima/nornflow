# Writing Workflows

Workflows in NornFlow are defined using YAML files. These files contain the configuration needed to execute sequences of tasks on network devices. This document explains how to write these workflow YAML files correctly.  

## Basic Structure
A workflow YAML file must have a top-level workflow key, which contains all the workflow configuration:

```yaml
workflow:
  name: "My Workflow"
  description: "Description of what this workflow does"
  inventory_filters:
    hosts: []
    groups: []
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
| workflow.tasks                   | Yes       | List of dictionaries | List of tasks to execute      |
| workflow.tasks[].name            | Yes       | String             | The name of the task            |
| workflow.tasks[].args            | No        | Dictionary         | Arguments to pass to the task   |

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

<table width="100%">
<tr>
<td width="33%" align="left">
<a href="./nornflow_and_workflows.md">← Previous: NornFlow & Workflows</a>
</td>
<td width="33%" align="center">
</td>
<td width="33%" align="right">
<a href="./feature_roadmap.md">Next: Feature Roadmap →</a>
</td>
</tr>
</table>

</div>