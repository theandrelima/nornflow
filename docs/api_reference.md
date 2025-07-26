# API Reference

## Table of Contents
- [Overview](#overview)
- [NornFlow Class](#nornflow-class)
- [NornFlowBuilder Class](#nornflowbuilder-class)
- [Workflow Class](#workflow-class)
- [WorkflowFactory Class](#workflowfactory-class)
- [Built-in Tasks](#built-in-tasks)
- [Built-in Filters](#built-in-filters)
- [Built-in Processors](#built-in-processors)

## Overview

This reference documents the Python API for NornFlow. While most users interact with NornFlow through YAML workflows and the CLI, understanding the API is useful for:

- Writing custom tasks
- Creating custom processors
- Extending NornFlow functionality
- Debugging complex workflows

## NornFlow Class

The main orchestrator class that manages workflow execution.

```python
from nornflow import NornFlow
```

### Constructor

```python
def __init__(
    self,
    nornflow_settings: NornFlowSettings | None = None,
    workflow: Workflow | None = None,
    processors: list[dict[str, Any]] | None = None,
    cli_vars: dict[str, Any] | None = None,
    **kwargs: Any,
)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `tasks_catalog` | `dict[str, Callable]` | Registry of available tasks |
| `workflows_catalog` | `dict[str, Path]` | Registry of workflow files |
| `filters_catalog` | `dict[str, Callable]` | Registry of inventory filters |
| `workflow` | `Workflow` | Current workflow instance |
| `processors` | `list` | List of result processors |
| `settings` | `NornFlowSettings` | NornFlow configuration settings |
| `cli_vars` | `dict[str, Any]` | Variables passed from CLI |
| nornir_configs | `dict[str, Any]` | Nornir configuration |

### Methods

#### `run()`
Execute the loaded workflow.

```python
nornflow.run()
```

## NornFlowBuilder Class

Builder pattern implementation for constructing NornFlow instances.

```python
from nornflow import NornFlowBuilder

builder = NornFlowBuilder()
nornflow = builder.build()
```

### Methods

#### `with_settings_path(path: str)`
Set the path to the NornFlow settings file.

#### `with_workflow(workflow: str | Path | dict | Workflow)`
Set the workflow to execute.

#### `with_processors(processors: list[dict[str, Any]])`
Add result processors.

#### `with_inventory_filters(filters: dict[str, Any])`
Apply inventory filters.

#### `with_vars(vars: dict[str, Any])`
Set workflow variables.

#### `build() -> NornFlow`
Build and return the NornFlow instance.

## Workflow Class

Represents a workflow definition.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Workflow name |
| `description` | `str | None` | Workflow description |
| `inventory_filters` | `dict[str, Any] | None` | Workflow-level inventory filters |
| vars | `dict[str, Any] | None` | Workflow-level variables |
| `processors_config` | `list[dict[str, Any]] | None` | Workflow-level processors |
| `domains` | `list[str]` | List of workflow domains |

### Methods

#### `run(nornir_manager, tasks_catalog, filters_catalog, workflow_roots, processors, cli_vars)`
Execute the workflow.

## WorkflowFactory Class

Factory for creating Workflow instances.

```python
from nornflow.workflow import WorkflowFactory

workflow = WorkflowFactory.create_from_file("path/to/workflow.yaml")
```

### Static Methods

#### `create_from_file(file_path: Path) -> Workflow`
Create a workflow from a YAML file.

#### `create_from_dict(workflow_data: dict[str, Any]) -> Workflow`
Create a workflow from a dictionary.

## Built-in Tasks

NornFlow includes these built-in tasks:

### echo

Print a message to stdout.

**Arguments:**
- `message` (str): Message to print

**Example:**
```yaml
- name: echo
  args:
    message: "Hello from {{ host.name }}"
```

### set

Set variables in the workflow context.

**Arguments:**
- Any key-value pairs to set as variables

**Example:**
```yaml
- name: set
  args:
    vlan_id: 100
    interface: "Gi0/1"
```

## Built-in Filters

NornFlow includes basic inventory filters:

- `platform` - Filter by device platform
- `groups` - Filter by device groups
- Custom filters can be added via the filters directory

## Built-in Processors

### DefaultNornFlowProcessor

The default processor that prints task results.

```python
from nornflow.builtins import DefaultNornFlowProcessor
```

Configuration in nornflow.yaml:
```yaml
processors:
  - class: "nornflow.builtins.DefaultNornFlowProcessor"
    args: {}
```

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./jinja2_filters.md">← Previous: Jinja2 Filters Reference</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
</td>
</tr>
</table>

</div>