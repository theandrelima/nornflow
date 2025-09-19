# API Reference

## Table of Contents
- [Overview](#overview)
- [NornFlow Class](#nornflow-class)
- [NornFlowBuilder Class](#nornflowbuilder-class)
- [NornFlowSettings Class](#nornflowsettings-class)
- [Workflow Class](#workflow-class)
- [WorkflowFactory Class](#workflowfactory-class)
- [NornirManager Class](#nornirmanger-class)
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

The central orchestrator and facade for the entire system. A high-level manager that initializes, configures, and coordinates all subsystems (catalogs, workflows, Nornir integration, etc.). It acts as the main entry point for users, handling initialization, validation, and delegation.

### Responsibilities:
- Loads and validates settings (via NornFlowSettings).  
- Discovers and catalogs tasks, workflows, and filters from directories.  
- Manages CLI variables and filters with precedence rules.  
- Delegates workflow execution to a Workflow instance.  
- Provides a unified interface for running workflows, handling errors, and managing processors.  
- Does not directly execute tasks or manage Nornir connections—that's delegated.  

```python
from nornflow.nornflow import NornFlow
```

### Constructor

```python
def __init__(
    self,
    nornflow_settings: NornFlowSettings | None = None,
    workflow: Workflow | None = None,
    processors: list[dict[str, Any]] | None = None,
    cli_vars: dict[str, Any] | None = None,
    cli_filters: dict[str, Any] | None = None,
    **kwargs: Any,
)
```

**Parameters:**
- `nornflow_settings`: NornFlow configuration settings object
- `workflow`: Pre-configured workflow object (optional)
- `processors`: List of processor configurations to override default processors
- `cli_vars`: Variables with highest precedence in the resolution chain
- `cli_filters`: Inventory filters with highest precedence that override workflow filters
- `**kwargs`: Additional keyword arguments passed to NornFlowSettings

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `tasks_catalog` | `PythonEntityCatalog` | Registry of available tasks |
| `workflows_catalog` | `FileCatalog` | Registry of workflow files |
| `filters_catalog` | `PythonEntityCatalog` | Registry of inventory filters |
| `workflow` | `Workflow \| str` | Current workflow instance or workflow name |
| `processors` | `list` | List of processor instances |
| `settings` | `NornFlowSettings` | NornFlow configuration settings |
| `cli_vars` | `dict[str, Any]` | Variables with highest precedence |
| `cli_filters` | `dict[str, Any]` | Inventory filters with highest precedence |
| nornir_configs | `dict[str, Any]` | Nornir configuration (read-only) |

### Methods

#### `run(dry_run: bool = False)`
Execute the configured workflow.

```python
nornflow.run(dry_run=True)  # Run in dry-run mode
nornflow.run()              # Run normally
```

**Parameters:**
- `dry_run`: Whether to run the workflow in dry-run mode

## NornFlowBuilder Class

Builder pattern implementation for constructing NornFlow instances with a fluent interface.

```python
from nornflow.nornflow import NornFlowBuilder

builder = NornFlowBuilder()
nornflow = builder.build()
```

### Methods

#### `with_settings_object(settings_object: NornFlowSettings) -> NornFlowBuilder`
Set the NornFlowSettings object for the builder.

#### `with_settings_path(settings_path: str | Path) -> NornFlowBuilder`
Create a NornFlowSettings from a file path (only if settings object not already set).

#### `with_workflow_object(workflow_object: Workflow) -> NornFlowBuilder`
Set a fully formed Workflow object.

#### `with_workflow_name(workflow_name: str) -> NornFlowBuilder`
Set the workflow by name (must exist in workflows catalog).

#### `with_workflow_path(workflow_path: str | Path) -> NornFlowBuilder`
Set the workflow by file path.

#### `with_workflow_dict(workflow_dict: dict[str, Any]) -> NornFlowBuilder`
Set the workflow from a dictionary definition.

#### `with_processors(processors: list[dict[str, Any]]) -> NornFlowBuilder`
Set processor configurations.

#### `with_cli_vars(cli_vars: dict[str, Any]) -> NornFlowBuilder`
Set CLI variables with highest precedence in variable resolution.

#### `with_cli_filters(cli_filters: dict[str, Any]) -> NornFlowBuilder`
Set CLI inventory filters with highest precedence.

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
    settings_file: str | Path | None = None,
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
| `processors` | `list[dict[str, Any]] \| None` | Nornir processor's configurations |

## Workflow Class

A runtime representation of a workflow definition. It encapsulates the logic for executing a sequence of tasks against a filtered inventory.

### Responsibilities:
- Holds workflow metadata (name, description, variables, filters, processors).
- Executes tasks in sequence using the provided catalogs and Nornir manager.
- Applies inventory filtering and variable resolution.
- Integrates with processors for result handling.
- Does not manage catalogs or Nornir connections directly—that's handled by NornFlow and NornirManager.

```python
from nornflow.workflow import Workflow
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Workflow name |
| `description` | `str \| None` | Workflow description |
| `inventory_filters` | `dict[str, Any] \| None` | Workflow-level inventory filters |
| vars | `dict[str, Any] \| None` | Workflow-level variables |
| `processors_config` | `list[dict[str, Any]] \| None` | Workflow-level processors |
| `domains` | `list[str]` | List of workflow domains (tasks) |

### Methods

#### `run(nornir_manager, tasks_catalog, filters_catalog, workflow_roots, processors, cli_vars, cli_filters, dry_run)`
Execute the workflow with all necessary catalogs and configurations.

## WorkflowFactory Class

Factory for creating Workflow instances from various sources.

```python
from nornflow.workflow import WorkflowFactory

factory = WorkflowFactory(
    workflow_path="path/to/workflow.yaml",
    settings=settings,
    cli_vars={"env": "prod"},
    cli_filters={"platform": "cisco_ios"}
)
workflow = factory.create()
```

### Constructor

```python
def __init__(
    self,
    workflow_path: str | Path | None = None,
    workflow_dict: dict[str, Any] | None = None,
    settings: NornFlowSettings | None = None,
    cli_vars: dict[str, Any] | None = None,
    cli_filters: dict[str, Any] | None = None,
)
```

### Methods

#### `create() -> Workflow`
Create and return a Workflow instance based on provided configuration.

## NornirManager Class

A wrapper/adapter around Nornir, handling the low-level Nornir instance lifecycle and integration.

```python
from nornflow.nornir_manager import NornirManager
```

### Responsibilities:
- Initializes and manages the Nornir object (inventory, connections, etc.).
- Provides context management for connections (via `__enter__`/`__exit__`).
- Abstracts Nornir's configuration and execution details.
- Does not define workflows or tasks—that's the domain of `Workflow` and catalogs.

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

NornFlow uses Pydantic-Serdes models for data validation and serialization of workflow configurations. Pydantic-Serdes is a library built on top of Pydantic that provides enhanced serialization capabilities, including support for custom data types, advanced validation features, and seamless integration with complex data structures like hashable dictionaries and one-to-many relationships.

### NornFlowBaseModel

Base model for all NornFlow models with strict field validation and universal field validation.

This base class extends Pydantic-Serdes' PydanticSerdesBaseModel and enforces strict configuration:
- `extra="forbid"`: Prevents any extra fields not defined in the model.
- Universal field validation: Applies common validation rules across all fields unless excluded.

The `create` class method handles model instantiation with universal validation applied post-creation.

```python
from nornflow.models import NornFlowBaseModel
```

### TaskModel

Represents individual tasks within a workflow.

Tasks are the atomic units of execution in NornFlow workflows. Each task has a name (referring to a function in the tasks catalog), optional arguments, and an optional `set_to` field for storing results as runtime variables.

**Key Attributes:**
- `id` (int | None): Auto-incrementing unique identifier for the task, assigned during creation.
- `name` (str): The task name, which must match a function in the tasks catalog (e.g., "echo", "set").
- `args` (HashableDict[str, str | tuple | dict | None] | None): Arguments passed to the task function. Supports Jinja2 templating for dynamic values. Converted to a hashable structure for serialization.
- `set_to` (str | None): Variable name to store the task's result as a runtime variable in the NornFlow variable system.

**Validation:**
- Field validator for `args`: Converts nested structures (lists, dicts) to hashable equivalents using `convert_to_hashable`.
- Universal validators: Applied to all fields except `args` and `set_to` (excluded via `_exclude_from_global_validators`).
- Post-creation validation: Calls `run_post_creation_task_validation` for task-specific rules, like preventing `set_to` on built-in tasks that don't support it.

**Execution:**
The `run` method executes the task by looking up the function in the tasks catalog and calling it with the provided arguments via NornirManager.

```python
from nornflow.models import TaskModel
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `int \| None` | Auto-incrementing task ID |
| `name` | `str` | Task name |
| `args` | `HashableDict[str, str \| tuple \| dict \| None] \| None` | Task arguments |
| `set_to` | `str \| None` | Variable name to store task result |

### Methods

#### `run(nornir_manager: NornirManager, tasks_catalog: dict[str, Callable]) -> AggregatedResult`
Execute the task using the provided NornirManager and tasks catalog.

### WorkflowModel

Represents a complete workflow definition.

Workflows are collections of tasks executed in sequence. They include metadata like name and description, inventory filters, processors, and variables.

**Key Attributes:**
- `name` (str): Unique workflow name.
- `description` (str | None): Optional human-readable description.
- `inventory_filters` (HashableDict[str, Any] | None): Filters applied to the Nornir inventory before execution.
- `processors` (tuple[HashableDict[str, Any]] | None): Processors for handling task results.
- `tasks` (OneToMany[TaskModel, ...]): List of tasks in the workflow, managed as a one-to-many relationship.
- `dry_run` (bool): Whether to run in dry-run mode.
- `vars` (HashableDict[str, Any] | None): Workflow-level variables.

**Validation:**
- Field validators for `inventory_filters`, `processors`, and `vars`: Convert nested structures to hashable forms.
- Universal validators: Applied to all fields.
- Creation: Instantiates TaskModel objects from the tasks list and validates the entire structure.

```python
from nornflow.models import WorkflowModel
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Workflow name |
| `description` | `str \| None` | Workflow description |
| `inventory_filters` | `HashableDict[str, Any] \| None` | Workflow-level inventory filters |
| `processors` | `tuple[HashableDict[str, Any]] \| None` | Workflow-level processors |
| tasks | `OneToMany[TaskModel, ...]` | List of tasks in the workflow |
| `dry_run` | `bool` | Whether to run in dry-run mode |
| vars | `HashableDict[str, Any] \| None` | Workflow-level variables |

## Validation System

NornFlow's validation system combines Pydantic's built-in validation with custom field and universal validators.

### Field Validators
Field validators are specific to individual fields and defined using Pydantic's `@field_validator` decorator. They transform or validate field values during model creation. For example:
- `TaskModel.args`: Converts lists to tuples for hashability.
- `WorkflowModel.inventory_filters`: Ensures hashable nested structures.

### Universal Validators
Universal validators are custom functions applied to all fields unless explicitly excluded. They are discovered dynamically by naming convention (`universal_{name}_validator`) and run on every field in the model.

**Implementation:**
- Defined in `validators.py`.
- Called via `run_universal_field_validation` in `NornFlowBaseModel.create`.
- Exclusions: Set via `_exclude_from_global_validators` class attribute (e.g., `TaskModel` excludes `args` and `set_to` to allow Jinja2 templates).

**Example Universal Validator:**
- `universal_jinja2_validator`: Prevents Jinja2 code in fields by checking for patterns and raising errors if found. This ensures security by restricting templating to specific contexts.

**How It Works:**
1. During model creation, `NornFlowBaseModel.create` calls `run_universal_field_validation`.
2. This function iterates over all fields, excluding those in `_exclude_from_global_validators`.
3. For each field, it calls matching universal validators (e.g., `universal_jinja2_validator`).
4. Validators return `(bool, str)`: `True` for pass, `False` with error message for fail.
5. Failures raise `TaskError` with detailed messages.

This system provides consistent, reusable validation across models while allowing flexibility for field-specific rules.

## Variable System Classes

NornFlow's variable system provides multi-level precedence resolution with device-specific contexts.

### NornFlowVariablesManager

Manages the loading, accessing, and resolution of variables from multiple sources, strictly adhering to NornFlow's documented precedence order.

```python
from nornflow.vars.manager import NornFlowVariablesManager
```

### Constructor

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

### Methods

#### `get_device_context(host_name: str) -> NornFlowDeviceContext`
Retrieves or creates a device context for the specified host.

#### `set_runtime_variable(name: str, value: Any, host_name: str) -> None`
Sets a runtime variable for a specific host.

#### `get_nornflow_variable(var_name: str, host_name: str) -> Any`
Retrieves a variable for a specific host following precedence rules.

#### `resolve_string(template_str: str, host_name: str, additional_vars: dict[str, Any] | None = None) -> str`
Resolves Jinja2 templates in strings.

#### `resolve_data(data: Any, host_name: str, additional_vars: dict[str, Any] | None = None) -> Any`
Recursively resolves Jinja2 templates in data structures.

### NornFlowDeviceContext

Maintains an isolated variable context for a specific device's NornFlow Variables.

```python
from nornflow.vars.context import NornFlowDeviceContext
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `cli_vars` | `dict[str, Any]` | CLI variables with overrides |
| `workflow_inline_vars` | `dict[str, Any]` | Inline workflow variables with overrides |
| `domain_vars` | `dict[str, Any]` | Domain variables with overrides |
| `default_vars` | `dict[str, Any]` | Default variables with overrides |
| `env_vars` | `dict[str, Any]` | Environment variables with overrides |
| `runtime_vars` | `dict[str, Any]` | Runtime variables (device-specific) |

### Methods

#### `get_flat_context() -> dict[str, Any]`
Get a flattened view of all variables respecting precedence order.

### HostNamespace

Provides read-only access to Nornir host inventory data via the 'host.' prefix in Jinja2 templates.

```python
from nornflow.vars.manager import HostNamespace
```

### Methods

#### `__getattr__(name: str) -> Any`
Retrieves an attribute from the Nornir host's inventory.

### NornirHostProxy

Read-only proxy object for accessing Nornir inventory variables for the current host via the `host.` namespace in NornFlow templates.

```python
from nornflow.vars.proxy import NornirHostProxy
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `current_host` | `Host \| None` | Current Nornir Host object |
| `nornir` | `Nornir \| None` | Nornir instance |
| `current_host_name` | `str \| None` | Name of current host |

### Methods

#### `__getattr__(name: str) -> Any`
Dynamically retrieves attributes from the current Nornir host.

### NornFlowVariableProcessor

Processor responsible for substituting variables in task arguments and managing NornFlow's variable context during task execution.

```python
from nornflow.vars.processors import NornFlowVariableProcessor
```

### Constructor

```python
def __init__(self, vars_manager: NornFlowVariablesManager)
```

### Methods

#### `task_instance_started(task: Task, host: Host) -> None`
Sets host context and processes Jinja2 templates in task parameters.

#### `task_instance_completed(task: Task, host: Host, result: MultiResult) -> None`
Clears host context after task completion.

## Built-in Tasks

NornFlow includes these built-in tasks accessible in all workflows:

### echo

Print a message to stdout with variable interpolation support.

**Arguments:**
- `message` (str): Message to print (supports Jinja2 templating)

**Example:**
```yaml
- name: echo
  args:
    message: "Processing {{ host.name }} with platform {{ host.platform }}"
```

### set

Set variables in the workflow context for use in subsequent tasks.

**Arguments:**
- Any key-value pairs to set as variables

**Example:**
```yaml
- name: set
  args:
    vlan_id: 100
    interface: "Gi0/1"
    backup_path: "/tmp/{{ host.name }}_backup.txt"
```

### hello_world

Simple demonstration task that prints a greeting.

**Arguments:**
- `name` (str, optional): Name to include in greeting

**Example:**
```yaml
- name: hello_world
  args:
    name: "Network Engineer"
```

## Built-in Filters

NornFlow includes these built-in inventory filters:

### has_groups

Filter hosts that belong to specific groups.

**Arguments:**
- `groups` (list[str]): List of group names

### platform

Filter hosts by platform type.

**Arguments:**
- `platforms` (list[str]): List of platform names

### Custom Filters

Custom filters can be added by placing Python files in the configured `local_filters_dirs`. Filter functions must:
- Accept a `host` parameter
- Return a boolean indicating if the host should be included
- Be decorated with appropriate metadata for discovery

## Built-in Processors

### DefaultNornFlowProcessor

The default processor that formats and displays task results.

```python
from nornflow.builtins.processors import DefaultNornFlowProcessor
```

**Configuration in nornflow.yaml:**
```yaml
processors:
  - class: "nornflow.builtins.DefaultNornFlowProcessor"
    args: {}
```

**Features:**
- Colored output for success/failure states
- Structured display of task results
- Error highlighting and formatting
- Progress indicators for multi-host operations

### Custom Processors

Custom processors can be created by implementing the processor interface and configuring them in settings or workflows. Processors receive task results and can format, store, or forward them as needed.

## Design Patterns

NornFlow employs several design patterns to provide a clean, maintainable, and extensible architecture as a lightweight framework on top of Nornir. Below is a summary of the key patterns implemented by NornFlow.

### Facade Pattern (NornFlow Class)
The `NornFlow` class implements the Facade pattern, providing a simplified interface to the complex subsystem of catalogs, workflows, Nornir integration, and variable management. It hides the complexity of coordinating multiple components while exposing a clean API for workflow execution.

**Key Benefits:**
- Unified entry point for users
- Encapsulates subsystem interactions
- Simplifies client code by hiding implementation details

### Builder Pattern (NornFlowBuilder Class)
Closely related to the Facade pattern, the `NornFlowBuilder` class implements the Builder pattern to construct `NornFlow` instances with a fluent interface. This pattern allows step-by-step configuration of complex objects while maintaining readability and preventing constructor parameter explosion.

**Key Benefits:**
- Fluent API for object construction
- Supports optional configuration parameters
- Enables method chaining for better readability
- Separates construction logic from the final object

**Relationship to Facade:** The Builder creates the Facade object, providing a structured way to configure the complex subsystem that the Facade then manages.

### Factory Pattern (WorkflowFactory Class)
The `WorkflowFactory` class implements the Factory pattern for creating `Workflow` instances from various sources (files, dictionaries, etc.). This pattern centralizes object creation logic and provides a consistent interface regardless of the input format.

**Key Benefits:**
- Encapsulates object creation complexity
- Supports multiple creation methods
- Enables easy extension for new workflow sources
- Provides validation during creation

### Proxy Pattern (NornirHostProxy Class)
The `NornirHostProxy` class implements the Proxy pattern to provide controlled access to Nornir inventory data. It acts as an intermediary for accessing host attributes and data, enabling lazy loading and additional functionality like variable resolution within NornFlow's context.

**Key Benefits:**
- Controlled access to underlying objects
- Enables additional functionality (caching, validation)
- Maintains interface compatibility
- Supports lazy initialization

### Composite Pattern (Workflow and Task Models)
The `WorkflowModel` and `TaskModel` classes implement the Composite pattern, where workflows contain tasks, and tasks can be treated uniformly. This allows workflows to be composed of individual tasks while maintaining a consistent interface for execution.

**Key Benefits:**
- Tree-like structure for complex workflows
- Uniform treatment of individual and composite objects
- Recursive execution capabilities
- Easy addition of new task types

### Context Object Pattern (NornFlowDeviceContext Class)
The `NornFlowDeviceContext` class implements the Context Object pattern to maintain device-specific state and configuration. It encapsulates all variable-related data for a specific device, providing a clean interface for variable resolution and management.

**Key Benefits:**
- Encapsulates device-specific state
- Provides clean separation of concerns
- Enables efficient variable lookups
- Supports per-device customization

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