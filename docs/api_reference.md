# API Reference

## Table of Contents
- [Overview](#overview)
- [NornFlow Class](#nornflow-class)
- [NornFlowBuilder Class](#nornflowbuilder-class)
- [NornFlowSettings Class](#nornflowsettings-class)
- [NornirManager Class](#nornirmanager-class)
- [Model Classes](#model-classes)
- [Variable System Classes](#variable-system-classes)
- [Built-in Tasks](#built-in-tasks)
- [Built-in Filters](#built-in-filters)
- [Built-in Processors](#built-in-processors)
- [Design Patterns](#design-patterns)

## Overview

This reference documents the Python API for NornFlow. While most users interact with NornFlow through YAML workflows and the CLI, understanding the API is useful for:

- Writing custom tasks
- Creating custom processors
- Extending NornFlow functionality
- Debugging complex workflows

## NornFlow Class

The central orchestrator for the entire system. NornFlow manages all aspects of workflow execution, from initialization and asset discovery to task execution and result processing. It serves as the main entry point for users, providing a unified interface for running workflows.

### Responsibilities:
- Loads and validates settings (via NornFlowSettings)
- Discovers and catalogs tasks, workflows, and filters from directories
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
- `**kwargs`: Additional keyword arguments passed to NornFlowSettings

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `tasks_catalog` | `CallableCatalog` | Registry of available tasks |
| `workflows_catalog` | `FileCatalog` | Registry of workflow files |
| `filters_catalog` | `CallableCatalog` | Registry of inventory filters |
| `workflow` | `WorkflowModel \| None` | Current workflow model or None |
| `workflow_path` | `Path \| None` | Path to workflow file if loaded from file |
| `processors` | `list` | List of processor instances |
| `settings` | `NornFlowSettings` | NornFlow configuration settings |
| `vars` | `dict[str, Any]` | Variables with highest precedence |
| `filters` | `dict[str, Any]` | Inventory filters with highest precedence |
| `failure_strategy` | `FailureStrategy` | Current failure handling strategy |
| `nornir_configs` | `dict[str, Any]` | Nornir configuration (read-only) |
| `nornir_manager` | `NornirManager` | NornirManager instance (read-only) |

### Methods

#### `run(dry_run: bool = False) -> int`
Execute the configured workflow.

```python
exit_code = nornflow.run(dry_run=True)  # Run in dry-run mode
exit_code = nornflow.run()              # Run normally
```

**Parameters:**
- `dry_run`: Whether to run the workflow in dry-run mode

**Returns:**
- `int`: Exit code representing execution status
  - 0: Success (all tasks passed)
  - 1-100: Failure percentage (% of failed task executions, rounded down)
  - 101: Failure without percentage information

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
    .with_workflow_name("backup")
    .with_vars({"env": "prod"})
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
Set additional keyword arguments.

#### `build() -> NornFlow`
Build and return the NornFlow instance.

## NornFlowSettings Class

Configuration settings for NornFlow.

```python
from nornflow.settings import NornFlowSettings

settings = NornFlowSettings(settings_file="nornflow.yaml")
```

### Constructor

```python
def __init__(
    self,
    settings_file: str = "nornflow.yaml",
    **kwargs: Any
)
```

### Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `nornir_config_file` | `str` | Path to Nornir configuration file |
| `local_tasks_dirs` | `list[str]` | Directories containing custom tasks |
| `local_workflows_dirs` | `list[str]` | Directories containing workflow files |
| `local_filters_dirs` | `list[str]` | Directories containing custom filters |
| `processors` | `list[dict[str, Any]] \| None` | Nornir processor configurations |
| `vars_dir` | `str` | Directory for variable files |
| `failure_strategy` | `FailureStrategy` | Task failure handling strategy |

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

For example, the built-in `universal_jinja2_validator` checks all fields to prevent Jinja2 templating code in places where it shouldn't be. Fields that are meant to contain Jinja2 templates (like task arguments) can exclude themselves from this validation:

```python
class TaskModel(NornFlowBaseModel):
    # Exclude 'args' from universal Jinja2 validation since templates are allowed there
    _exclude_from_universal_validations: ClassVar[tuple[str, ...]] = ("args", "set_to")
```

Universal validators must return a tuple of `(bool, str)` where:
- First element is whether validation passed (True) or failed (False)
- Second element is the error message if validation failed

**Model Creation Flow:**

When models are created, the validation process follows this sequence:
1. Pydantic performs basic type validation
2. `create()` method is called, which runs universal field validation via `run_universal_field_validation()`
3. For specific models (like TaskModel), additional post-creation validation may run via `run_post_creation_task_validation()`

This multi-layered approach ensures models are validated consistently across the application while allowing flexibility where needed.

### TaskModel

Represents individual tasks within a workflow.

```python
from nornflow.models import TaskModel
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `id` | `int \| None` | Auto-incrementing task ID |
| `name` | `str` | Task name (must exist in tasks catalog) |
| `args` | `HashableDict[str, Any] \| None` | Task arguments (supports Jinja2) |
| `set_to` | `str \| None` | Variable name to store task result |

**Methods:**

#### `run(nornir_manager: NornirManager, vars_manager: NornFlowVariablesManager, tasks_catalog: dict[str, Callable]) -> AggregatedResult`
Execute the task using the provided NornirManager and tasks catalog.

### WorkflowModel

Represents a complete workflow definition. This is a data model that defines the structure of a workflow but does not contain execution logic.

```python
from nornflow.models import WorkflowModel
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Workflow name |
| `description` | `str \| None` | Workflow description |
| `inventory_filters` | `HashableDict[str, Any] \| None` | Workflow-level inventory filters |
| `processors` | `tuple[HashableDict[str, Any]] \| None` | Workflow-level processors |
| tasks | `OneToMany[TaskModel, ...]` | List of tasks in the workflow |
| `dry_run` | `bool` | Whether to run in dry-run mode |
| vars | `HashableDict[str, Any] \| None` | Workflow-level variables |
| `failure_strategy` | `FailureStrategy` | Failure handling strategy |

**Class Methods:**

#### `create(dict_args: dict[str, Any]) -> WorkflowModel`
Create a new WorkflowModel from a workflow dictionary.

## Variable System Classes

NornFlow's variable system provides multi-level precedence resolution with device-specific contexts.

### NornFlowVariablesManager

Manages the loading, accessing, and resolution of variables from multiple sources.

```python
from nornflow.vars.manager import NornFlowVariablesManager
```

#### Constructor

```python
def __init__(
    self,
    vars_dir: str,
    cli_vars: dict[str, Any] | None = None,
    inline_workflow_vars: dict[str, Any] | None = None,
    workflow_path: Path | None = None,
    workflow_roots: list[str] | None = None,
) -> None
```

#### Methods

- `get_device_context(host_name: str) -> NornFlowDeviceContext`: Get or create device context
- `set_runtime_variable(name: str, value: Any, host_name: str) -> None`: Set runtime variable
- `get_nornflow_variable(var_name: str, host_name: str) -> Any`: Get variable following precedence
- `resolve_string(template_str: str, host_name: str, additional_vars: dict[str, Any] | None = None) -> str`: Resolve Jinja2 templates
- `resolve_data(data: Any, host_name: str, additional_vars: dict[str, Any] | None = None) -> Any`: Recursively resolve templates

### NornFlowDeviceContext

Maintains an isolated variable context for a specific device.

```python
from nornflow.vars.context import NornFlowDeviceContext
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `cli_vars` | `dict[str, Any]` | CLI variables |
| `workflow_inline_vars` | `dict[str, Any]` | Inline workflow variables |
| `domain_vars` | `dict[str, Any]` | Domain-specific variables |
| `default_vars` | `dict[str, Any]` | Default variables |
| `env_vars` | `dict[str, Any]` | Environment variables |
| `runtime_vars` | `dict[str, Any]` | Runtime variables (device-specific) |

**Methods:**

- `get_flat_context() -> dict[str, Any]`: Get flattened variables respecting precedence

### NornirHostProxy

Read-only proxy for accessing Nornir inventory variables via the `host.` namespace.

```python
from nornflow.vars.proxy import NornirHostProxy
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `current_host` | `Host \| None` | Current Nornir Host object |
| `nornir` | `Nornir \| None` | Nornir instance |
| `current_host_name` | `str \| None` | Name of current host |

### NornFlowVariableProcessor

Processor for variable substitution and management during task execution.

```python
from nornflow.vars.processors import NornFlowVariableProcessor
```

#### Constructor

```python
def __init__(self, vars_manager: NornFlowVariablesManager)
```

#### Methods

- `task_instance_started(task: Task, host: Host) -> None`: Set host context and process templates
- `task_instance_completed(task: Task, host: Host, result: MultiResult) -> None`: Clear host context

## Built-in Tasks

### echo

Print a message with variable interpolation.

```yaml
- name: echo
  args:
    msg: "Processing {{ host.name }}"
```

### set

Set runtime variables for use in subsequent tasks.

```yaml
- name: set
  args:
    vlan_id: 100
    backup_path: "/tmp/{{ host.name }}.cfg"
```

### write_file

Write content to a file.

```yaml
- name: write_file
  args:
    filename: "/tmp/config.txt"
    content: "{{ config_data }}"
    append: false
    mkdir: true
```

## Built-in Filters

### hosts

Filter inventory by hostname list.

```yaml
inventory_filters:
  hosts: ["router1", "router2"]
```

### groups

Filter inventory by group membership.

```yaml
inventory_filters:
  groups: ["core", "distribution"]
```

## Built-in Processors

### DefaultNornFlowProcessor

The default processor that formats and displays task results.

```yaml
processors:
  - class: "nornflow.builtins.DefaultNornFlowProcessor"
```

**Features:**
- Colored output for success/failure
- Execution timing tracking
- Progress indicators
- Final workflow summary

### NornFlowFailureStrategyProcessor

Implements failure handling strategies during execution.

```python
from nornflow.builtins.processors import NornFlowFailureStrategyProcessor
```

**Strategies:**
- `SKIP_FAILED`: Remove failed hosts from subsequent tasks (default)
- `FAIL_FAST`: Stop all execution on first failure
- `RUN_ALL`: Continue all tasks regardless of failures

## Design Patterns

NornFlow employs several design patterns for clean, maintainable architecture:

### Facade Pattern (NornFlow Class)
The `NornFlow` class provides a simplified interface to the complex subsystem of catalogs, workflows, Nornir integration, and variable management. It coordinates multiple components while exposing a clean API.

**Key Benefits:**
- Unified entry point
- Encapsulated subsystem interactions
- Simplified client code

### Builder Pattern (NornFlowBuilder Class)
The `NornFlowBuilder` provides a fluent interface for constructing `NornFlow` instances, allowing step-by-step configuration while maintaining readability.

**Key Benefits:**
- Fluent API for construction
- Optional configuration parameters
- Method chaining
- Separated construction logic

### Proxy Pattern (NornirHostProxy Class)
The `NornirHostProxy` provides controlled read-only access to Nornir inventory data with additional functionality like variable resolution.

**Key Benefits:**
- Controlled access to underlying objects
- Additional functionality (caching, validation)
- Interface compatibility
- Lazy initialization

### Context Object Pattern (NornFlowDeviceContext Class)
The `NornFlowDeviceContext` encapsulates device-specific state and configuration, providing clean separation of concerns for variable management.

**Key Benefits:**
- Encapsulated device state
- Clean separation of concerns
- Efficient variable lookups
- Per-device customization

### Template Method Pattern (Catalog Classes)
The abstract `Catalog` base class defines the skeleton of the discovery algorithm, with concrete implementations in `CallableCatalog` and `FileCatalog`.

**Key Benefits:**
- Reusable algorithm structure
- Customizable specific steps
- Consistent interface
- Code reuse

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