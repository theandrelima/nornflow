# API Reference

## Table of Contents
- [Overview](#overview)
- [NornFlow Class](#nornflow-class)
- [NornFlowBuilder Class](#nornflowbuilder-class)
- [NornFlowSettings Class](#nornflowsettings-class)
- [NornirManager Class](#nornirmanager-class)
- [Model Classes](#model-classes)
- [Hook Classes](#hook-classes)
- [Variable System Classes](#variable-system-classes)
- [Built-in Tasks](#built-in-tasks)
- [Built-in Filters](#built-in-filters)
- [Built-in Processors](#built-in-processors)

## Overview

This reference documents the Python API for NornFlow. While most users interact with NornFlow through YAML workflows and the CLI, understanding the API is useful for:

- Writing custom tasks
- Creating custom processors
- Creating custom hooks
- Extending NornFlow functionality
- Debugging complex workflows

## NornFlow Class

The central orchestrator for the entire system. NornFlow manages all aspects of workflow execution, from initialization and asset discovery to task execution and result processing. It serves as the main entry point for users, providing a unified interface for running workflows.

### Responsibilities:
- Loads and validates settings (via NornFlowSettings)
- Discovers and catalogs tasks, workflows, filters, and blueprints from directories
- Manages vars and filters with precedence rules
- Directly orchestrates workflow execution
- Handles inventory filtering and variable resolution
- Manages processor loading and application
- Interfaces with NornirManager to handle the main Nornir object 

```python
from nornflow.nornflow import NornFlow
```

### Constructor

```python
def __init__(
    self,
    nornflow_settings: NornFlowSettings | None = None,
    workflow: WorkflowModel | str | None = None,
    processors: list[dict[str, Any]] | None = None,
    vars: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
    failure_strategy: FailureStrategy | None = None,
    dry_run: bool | None = None,
    **kwargs: Any,
)
```

**Parameters:**
- `nornflow_settings`: NornFlow configuration settings object
- `workflow`: WorkflowModel instance or workflow name string (optional - not required for informational commands)
- `processors`: List of processor configurations to override default processors
- `vars`: Variables with highest precedence in the resolution chain
- `filters`: Inventory filters with highest precedence that override workflow filters
- `failure_strategy`: Failure handling strategy (skip-failed, fail-fast, or run-all)
- `dry_run`: Dry run mode with highest precedence. Overrides workflow and settings values
- `**kwargs`: Additional keyword arguments passed to NornFlowSettings

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `tasks_catalog` | `CallableCatalog` | Registry of available tasks |
| `workflows_catalog` | `FileCatalog` | Registry of workflow files |
| `filters_catalog` | `CallableCatalog` | Registry of inventory filters |
| `blueprints_catalog` | `FileCatalog` | Registry of blueprint files |
| `workflow` | `WorkflowModel \| None` | Current workflow model or None |
| `workflow_path` | `Path \| None` | Path to workflow file if loaded from file |
| `processors` | `list` | List of processor instances |
| `settings` | `NornFlowSettings` | NornFlow configuration settings |
| `vars` | `dict[str, Any]` | Variables with highest precedence |
| `filters` | `dict[str, Any]` | Inventory filters with highest precedence |
| `failure_strategy` | `FailureStrategy` | Current failure handling strategy |
| `dry_run` | `bool` | Current dry run mode (resolved via precedence chain) |
| `nornir_configs` | `dict[str, Any]` | Nornir configuration (read-only) |
| `nornir_manager` | `NornirManager` | NornirManager instance (read-only) |

### Methods

#### `run() -> int`
Execute the configured workflow.

```python
# dry_run is now set via constructor, workflow, or settings
nornflow = NornFlow(workflow=my_workflow, dry_run=True)
exit_code = nornflow.run()  # Uses the dry_run set during initialization
```

**Returns:**
- `int`: Exit code representing execution status
  - 0: Success (all tasks passed)
  - 1-100: Failure with percentage information (% of failed task executions)
  - 101: Failure without percentage information
  - 102+: Reserved for exceptions/internal errors

**Exceptions:**
- `WorkflowError`: If no workflow is configured
- `TaskError`: If tasks in workflow are not found in catalog
- May raise other NornFlowError subclasses

## NornFlowBuilder Class

Builder pattern implementation for constructing NornFlow instances with a fluent interface.

```python
from nornflow.builder import NornFlowBuilder

builder = NornFlowBuilder()
nornflow = (builder
    .with_settings_path("nornflow.yaml")
    .with_workflow_path("backup.yaml")
    .with_kwargs(dry_run=True)  # Pass dry_run via kwargs
    .build())
```

### Methods

#### `with_settings_object(settings_object: NornFlowSettings) -> NornFlowBuilder`
Set the NornFlowSettings object for the builder.

#### `with_settings_path(settings_path: str | Path) -> NornFlowBuilder`
Create a NornFlowSettings from a file path (only if settings object not already set).

#### `with_workflow_model(workflow_model: WorkflowModel) -> NornFlowBuilder`
Set a fully formed WorkflowModel object.

#### `with_workflow_name(workflow_name: str) -> NornFlowBuilder`
Set the workflow by name (must exist in workflows catalog).

#### `with_workflow_path(workflow_path: str | Path) -> NornFlowBuilder`
Set the workflow by file path.

#### `with_workflow_dict(workflow_dict: dict[str, Any]) -> NornFlowBuilder`
Set the workflow from a dictionary definition.

#### `with_processors(processors: list[dict[str, Any]]) -> NornFlowBuilder`
Set processor configurations.

#### `with_vars(vars: dict[str, Any]) -> NornFlowBuilder`
Set vars with highest precedence in variable resolution.

#### `with_filters(filters: dict[str, Any]) -> NornFlowBuilder`
Set inventory filters with highest precedence.

#### `with_failure_strategy(failure_strategy: FailureStrategy) -> NornFlowBuilder`
Set the failure handling strategy.

#### `with_kwargs(**kwargs: Any) -> NornFlowBuilder`
Set additional keyword arguments (including `dry_run`).

#### `build() -> NornFlow`
Build and return the NornFlow instance.

## NornFlowSettings Class

Configuration settings for NornFlow using Pydantic for validation and type safety.

```python
from nornflow.settings import NornFlowSettings

# Load from YAML file
settings = NornFlowSettings.load("nornflow.yaml")

# Create directly with values
settings = NornFlowSettings(
    nornir_config_file="nornir.yaml",
    dry_run=True
)
```

### Class Methods

#### `load(settings_file: str | None = None, base_dir: Path | None = None, **overrides: Any) -> NornFlowSettings`
Load settings from a YAML file with automatic resolution and overrides. This call resolves relative paths by combining either the discovered settings directory or the explicit `base_dir` with the configured entries.

**Parameters:**
- `settings_file`: Path to settings YAML file. If None, checks NORNFLOW_SETTINGS env var, then defaults to "nornflow.yaml"
- `base_dir`: Base directory for resolving relative paths. If None, uses the directory containing the settings file. Providing a value overrides the discovery location used by `resolve_relative_paths`.
- `**overrides`: Additional settings to override YAML values

**Returns:**
- `NornFlowSettings` instance with path fields rewritten relative to the resolved base directory. Constructing `NornFlowSettings` directly (without `load`) skips this step and leaves the incoming values untouched.

### Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `nornir_config_file` | `str` | Path to Nornir configuration file (required) |
| `local_tasks` | `list[str]` | Directories containing custom tasks |
| `local_workflows` | `list[str]` | Directories containing workflow files |
| `local_filters` | `list[str]` | Directories containing custom filters |
| `local_hooks` | `list[str]` | Directories containing custom hooks |
| `local_blueprints` | `list[str]` | Directories containing blueprint files |
| `processors` | `list[dict[str, Any]]` | Nornir processor configurations |
| `vars_dir` | `str` | Directory for variable files |
| `failure_strategy` | `FailureStrategy` | Task failure handling strategy |
| `dry_run` | `bool` | Default dry run mode |
| `as_dict` | `dict[str, Any]` | Settings as a dictionary |
| `base_dir` | `Path` | Base directory for resolving relative paths |

## NornirManager Class

A wrapper/adapter around Nornir, handling the low-level Nornir instance lifecycle and integration.

```python
from nornflow.nornir_manager import NornirManager
```

### Responsibilities:
- Initializes and manages the Nornir object (inventory, connections, etc.)
- Provides context management for connections (via `__enter__`/`__exit__`)
- Abstracts Nornir's configuration and execution details
- Applies inventory filters and processors

### Constructor

```python
def __init__(self, nornir_settings: str | Path, **kwargs: Any)
```

**Parameters:**
- `nornir_settings`: Path to Nornir configuration file
- `**kwargs`: Additional keyword arguments for Nornir initialization

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `nornir` | `Nornir` | The underlying Nornir instance |

### Methods

#### `__enter__() -> NornirManager`
Enter context manager, opening connections.

#### `__exit__(exc_type, exc_val, exc_tb) -> None`
Exit context manager, closing connections.

#### `apply_filters(**kwargs: Any) -> None`
Apply filters to the Nornir inventory.

#### `apply_processors(processors: list[Processor]) -> None`
Apply processors to the Nornir instance.

#### `set_dry_run(dry_run: bool) -> None`
Set dry-run mode for the Nornir instance.

## Model Classes

NornFlow uses Pydantic-Serdes models for data validation and serialization. These models represent the structure of workflows and tasks.

### NornFlowBaseModel

Base model for all NornFlow models with strict field validation and universal field validation.

```python
from nornflow.models import NornFlowBaseModel
```

**Key Features:**
- `extra="forbid"`: Prevents any extra fields not defined in the model
- Universal field validation: Applies automated validation rules across all fields
- The `create` class method handles model instantiation with validation

**Universal Field Validation:**

NornFlow implements a powerful validation system that automatically applies validators to all fields in model instances. This system:

1. Discovers and applies validation functions with the naming pattern `universal_{name}_validator` in the validators module
2. Runs these validators against all fields in the model unless excluded
3. Allows models to exclude specific fields from universal validation using the `_exclude_from_universal_validations` class attribute

For example, the built-in `universal_jinja2_validator` checks all fields to prevent Jinja2 templating code in places where it shouldn't be. Fields that are meant to contain Jinja2 templates (like task arguments and hook configurations) can exclude themselves from this validation:

```python
class TaskModel(NornFlowBaseModel):
    # Exclude 'args' and 'hooks' from universal Jinja2 validation since templates are allowed there
    _exclude_from_universal_validations: ClassVar[tuple[str, ...]] = ("args", "hooks")
```

Universal validators must return a tuple of `(bool, str)` where:
- First element is whether validation passed (True) or failed (False)
- Second element is the error message if validation failed

**Model Creation Flow:**

When models are created, the validation process follows this sequence:
1. Pydantic performs basic type validation
2. Field validators run for specific fields
3. Model validators run for cross-field validation
4. Universal validators run for all non-excluded fields
5. Final model instance is returned or validation error is raised

### WorkflowModel

Represents a complete workflow definition.

```python
from nornflow.models import WorkflowModel

workflow = WorkflowModel.create({
    "workflow": {
        "name": "My Workflow",
        "tasks": [...],
        "dry_run": True
    }
})
```

**Key Fields:**
- `name`: Workflow name (required)
- `description`: Workflow description (optional)
- `tasks`: List of TaskModel instances (required, non-empty)
- `dry_run`: Override dry run mode (optional, can be `None`)
- `failure_strategy`: Override failure strategy (optional, can be `None`)
- `vars`: Workflow-level variables (optional)
- `inventory_filters`: Inventory filtering configuration (optional)
- `processors`: Processor configurations (optional)

**Create Method:**

The `create` class method handles workflow creation with blueprint expansion:

```python
@classmethod
def create(cls, dict_args: dict[str, Any], *args: Any, **kwargs: Any) -> "WorkflowModel"
```

**Args:**
- `dict_args`: Dictionary containing the full workflow data, must include 'workflow' key
- `*args`: Additional positional arguments passed to parent create method
- `**kwargs`: Additional keyword arguments:
  - `blueprints_catalog` (dict[str, Path] | None): Catalog mapping blueprint names to file paths
  - `vars_dir` (str | None): Directory containing variable files
  - `workflow_path` (Path | None): Path to the workflow file
  - `workflow_roots` (list[str] | None): List of workflow root directories
  - `cli_vars` (dict[str, Any] | None): CLI variables with highest precedence

**Returns:**
- `WorkflowModel`: The created WorkflowModel instance with expanded blueprints

**Raises:**
- `WorkflowError`: If 'workflow' key is not present in dict_args
- `BlueprintError`: If blueprint expansion fails
- `BlueprintCircularDependencyError`: If circular dependencies detected in blueprint references

### TaskModel

Represents a single task in a workflow.

```python
from nornflow.models import TaskModel

task = TaskModel(
    name="netmiko_send_command",
    args={"command_string": "show version"},
    set_to="version_output"
)
```

**Key Fields:**
- `name`: Task name from catalog (required)
- `args`: Task arguments (optional)
- `set_to`: Variable storage configuration (optional hook)
- `if`: Conditional execution hook (optional hook)
- `shush`: Output suppression hook (optional hook)
- Other hook configurations as needed

## Hook Classes

Hooks extend task behavior without modifying task code. They implement the Nornir Processor protocol and are automatically registered when imported.

### BaseHook

Base class for all hooks, implementing the Nornir Processor protocol.

```python
from nornflow.hooks import BaseHook
from nornir.core.task import Task
from typing import Any

class MyCustomHook(BaseHook):
    """Custom hook implementation."""
    
    def __init__(self, value: Any):
        self.value = value
    
    def task_started(self, task: Task) -> None:
        """Called when task starts."""
        pass
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        """Called when task starts on a specific host."""
        pass
    
    def task_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        """Called when task completes on a specific host."""
        pass
```

### Hook Registration

Hooks are automatically registered when their class is defined:

```python
# hooks/my_hook.py
from nornflow.hooks import BaseHook

class MyHook(BaseHook):
    """Automatically registered when this file is imported."""
    pass
```

NornFlow discovers hooks by importing all Python files in configured hook directories.

## Variable System Classes

### NornFlowVariablesManager

Manages variable contexts and resolution for all devices during workflow execution.

```python
from nornflow.vars.manager import NornFlowVariablesManager
```

**Key Methods:**
- `get_vars(host: Host) -> dict`: Get variables for a specific host
- `set_var(host: Host, key: str, value: Any) -> None`: Set a runtime variable
- `render_template(template: str, host: Host) -> str`: Render Jinja2 template

### NornirHostProxy

Provides read-only access to Nornir inventory data within Jinja2 templates.

```python
# Automatically available in templates as 'host'
# Example: {{ host.name }}, {{ host.platform }}, {{ host.data.site }}
```

## Built-in Tasks

NornFlow includes several built-in tasks for common operations:

### `echo`

Print a message for debugging or logging.

```yaml
tasks:
  - name: echo
    args:
      msg: "Processing {{ host.name }}"
```

### `set`

Set runtime variables dynamically.

```yaml
tasks:
  - name: set
    args:
      timestamp: "{{ now() }}"
      counter: 0
```

### `write_file`

Write content to a file.

```yaml
tasks:
  - name: write_file
    args:
      filename: "configs/{{ host.name }}.txt"
      content: "{{ config_data }}"
```

### `read_file`

Read content from a file.

```yaml
tasks:
  - name: read_file
    args:
      filename: "templates/config.j2"
    set_to: "template_content"
```

### `template_file`

Render a Jinja2 template file.

```yaml
tasks:
  - name: template_file
    args:
      template: "templates/config.j2"
      dest: "configs/{{ host.name }}.conf"
```

## Built-in Filters

NornFlow includes built-in Nornir inventory filters:

### `filter_by_hosts`

Filter inventory to specific hosts.

```yaml
inventory_filters:
  filter_by_hosts: ["host1", "host2"]
```

### `filter_by_groups`

Filter inventory to hosts in specific groups.

```yaml
inventory_filters:
  filter_by_groups: ["routers", "switches"]
```

## Built-in Processors

### DefaultNornFlowProcessor

The default processor that provides standard output formatting.

```yaml
processors:
  - class: "nornflow.builtins.DefaultNornFlowProcessor"
```

Features:
- Formatted task output
- Progress indicators
- Result summaries
- Support for the `shush` hook

### NornFlowFailureStrategyProcessor

Internally used processor that implements failure handling strategies.

### NornFlowHookProcessor

Internally used processor that manages hook execution for tasks.

### NornFlowVariableProcessor

Internally used processor that handles variable resolution and template rendering.

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
