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
2. `create()` method is called, which runs universal field validation via `run_universal_field_validation()`
3. For specific models (like TaskModel), additional post-creation validation may run via `run_post_creation_task_validation()`

This multi-layered approach ensures models are validated consistently while allowing flexibility where needed.

### HookableModel

Abstract base class for models that support hooks (e.g., TaskModel).

```python
from nornflow.models import HookableModel
```

**Purpose:**
HookableModel provides the infrastructure for models to support hook configurations. It manages hook discovery, caching, and validation, but delegates actual hook execution to the NornFlowHookProcessor during task runtime.

**Key Features:**
- Implements Flyweight pattern for hook instance management (one instance per unique hook configuration)
- Automatically migrates hook fields from model dict to hooks field during creation
- Caches hook instances and hook processor reference for performance
- Provides hook validation interface through `run_hook_validations()`

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `hooks` | `HashableDict[str, Any] \| None` | Hook configurations for this model |
| `_hooks_cache` | `list[Hook] \| None` | Cached hook instances (private) |
| `_hook_processor_cache` | `NornFlowHookProcessor \| None` | Cached hook processor reference (private) |

**Methods:**

#### `get_hooks() -> list[Hook]`
Get all hook instances for this model. Uses cached instances if available.

**Returns:**
- List of Hook instances configured for this model

#### `run_hook_validations() -> None`
Execute validation logic for all hooks configured on this model.

Should be called explicitly at the beginning of the `run()` method in subclasses.

**Raises:**
- `HookValidationError`: If any hook validation fails

#### `get_task_args() -> dict[str, Any]`
Get clean task arguments without any NornFlow-specific context.

**Returns:**
- Dictionary of task arguments for the task function

#### `validate_hooks_and_set_task_context(nornir_manager, vars_manager, task_func) -> None`
Validate hooks and set task-specific context in the hook processor.

**Parameters:**
- `nornir_manager`: The NornirManager instance
- `vars_manager`: The variables manager instance
- `task_func`: The task function that will be executed

**Raises:**
- `ProcessorError`: If hooks are configured but hook processor cannot be retrieved

**Immutability Constraints:**

> **CRITICAL**: HookableModel instances (and subclasses like TaskModel) are **hashable** by design as PydanticSerdes models. **NEVER modify model attributes** after initialization, especially within Hook classes! Modifying attributes breaks the hash contract and can corrupt internal caches.

### TaskModel

Represents individual tasks within a workflow. Inherits from HookableModel to support hooks.

```python
from nornflow.models import TaskModel
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `id` | `int \| None` | Auto-incrementing task ID |
| `name` | `str` | Task name (must exist in tasks catalog) |
| `args` | `HashableDict[str, Any] \| None` | Task arguments (supports Jinja2) |
| `hooks` | `HashableDict[str, Any] \| None` | Hook configurations (inherited from HookableModel) |

**Key Characteristics:**
- Inherits from `HookableModel` (not RunnableModel)
- Instances are hashable and immutable after creation
- Hook validation delegated to parent via `run_hook_validations()`
- Excludes `args` and hooks from universal field validation

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
| `tasks` | `OneToMany[TaskModel, ...]` | List of tasks in the workflow |
| `dry_run` | `bool` | Whether to run in dry-run mode |
| `vars` | `HashableDict[str, Any] \| None` | Workflow-level variables |
| `failure_strategy` | `FailureStrategy` | Failure handling strategy |

**Class Methods:**

#### `create(dict_args: dict[str, Any]) -> WorkflowModel`
Create a new WorkflowModel from a workflow dictionary.

## Hook Classes

Hooks extend task behavior without modifying task code. They are implemented as Nornir Processors that activate when configured on specific tasks.

> **For comprehensive hook documentation, including lifecycle methods, creating custom hooks, validation patterns, and exception handling, see:** Hooks Guide

### Hook Base Class

Base class for all hooks with lifecycle management and context access.

```python
from nornflow.hooks import Hook
```

**Class Attributes:**

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `hook_name` | `str` | Yes | Unique identifier for this hook type |
| `run_once_per_task` | `bool` | No | If True, runs once per task; if False, runs per host (default: False) |
| `exception_handlers` | `dict[type[Exception], str]` | No | Maps exception types to handler method names |

**Constructor:**

```python
def __init__(self, value: Any = None)
```

**Parameters:**
- `value`: Hook configuration value from YAML

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `value` | `Any` | Hook configuration value |
| `context` | `dict[str, Any]` | Execution context injected by NornFlowHookProcessor (read-only) |

**Context Dictionary Contents:**

The `context` property provides access to execution context populated by `NornFlowHookProcessor`:

- `vars_manager`: NornFlowVariablesManager instance for variable resolution
- `nornir_manager`: NornirManager instance for Nornir operations
- `tasks_catalog`: Dictionary of available task functions
- `filters_catalog`: Dictionary of available inventory filter functions
- `workflows_catalog`: FileCatalog of available workflow files
- `task_model`: Current TaskModel being executed (task-specific context)

**Important:** Context is only available during hook lifecycle execution (after `task_started`). It will be empty during `__init__()` and `execute_hook_validations()`.

**Key Lifecycle Methods:**

All lifecycle methods are optional - override only those needed:

- `task_started(task: Task) -> None`
- `task_completed(task: Task, result: AggregatedResult) -> None`
- `task_instance_started(task: Task, host: Host) -> None`
- `task_instance_completed(task: Task, host: Host, result: MultiResult) -> None`
- `subtask_instance_started(task: Task, host: Host) -> None`
- `subtask_instance_completed(task: Task, host: Host, result: MultiResult) -> None`

**Control Methods:**

#### `should_execute(task: Task) -> bool`
Check if this hook should execute for given task.

**Returns:**
- `True` if hook should execute, `False` to skip

#### `execute_hook_validations(task_model: TaskModel) -> None`
Execute validation logic specific to this hook.

Called during workflow preparation before any task execution. Uses cooperative `super()` to ensure validation methods in mixins and parent classes are called properly.

**Parameters:**
- `task_model`: TaskModel instance to validate against

**Raises:**
- `HookValidationError`: If validation fails

### Jinja2ResolvableMixin

***Optional*** mixin providing automatic Jinja2 validation and seamless template resolution for hooks.

```python
from nornflow.hooks import Jinja2ResolvableMixin
```

**Purpose:**
Adds automatic Jinja2 validation during workflow preparation and resolution methods for execution. Developers using this mixin don't need Jinja2 awareness - just include it in the inheritance chain, optionally override `execute_hook_validations()` to add custom validations, and call `get_resolved_value()` in lifecycle methods.

**When to Use:**
- ✅ Hook accepts both static values AND Jinja2 expressions
- ✅ Hook needs automatic validation of Jinja2 expressions

**When NOT to Use:**
- ❌ Hook should never accept Jinja2 expressions (security/performance)
- ❌ Hook demands custom/complex Jinja2 resolution logic


**Usage:**

```python
class MyHook(Hook, Jinja2ResolvableMixin):
    hook_name = "my_hook"
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        condition = self.get_resolved_value(task, host=host, as_bool=True, default=False)
        if condition:
            pass
```

You can override `execute_hook_validations()` if you need additional custom validation:

```python
class MyHook(Hook, Jinja2ResolvableMixin):
    hook_name = "my_hook"
    
    def execute_hook_validations(self, task_model: TaskModel) -> None:
        super().execute_hook_validations(task_model)
        
        if self.value and not isinstance(self.value, (str, bool)):
            raise HookValidationError(
                self.hook_name,
                [("value_type", "my_hook only accepts strings or booleans")]
            )
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        condition = self.get_resolved_value(task, host=host, as_bool=True, default=False)
        if condition:
            pass
```


**Automatic Validation:**

The mixin automatically validates Jinja2 expressions by overriding `execute_hook_validations()`. Thanks to cooperative `super()` calls in the Hook base class, this works with any inheritance order.

**What gets validated by the mixin:**
- **Jinja2 expressions are validated**: `my_hook: "{{ variable }}"` - Template syntax checked
- **Plain strings are NOT validated**: `my_hook: "plain text"` - Passed through as-is
- **Empty strings are NOT validated**: `my_hook: ""` - Treated as falsy value
- **Non-string values skip validation**: `my_hook: true`, `my_hook: {"key": "value"}` - No checks

**Individual hooks can add stricter validation** if needed:

```python
from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookValidationError

class StrictHook(Hook, Jinja2ResolvableMixin):
    """Hook that rejects empty strings as meaningless configuration."""
    
    hook_name = "strict_hook"
    
    def execute_hook_validations(self, task_model: TaskModel) -> None:
        super().execute_hook_validations(task_model)
        
        if isinstance(self.value, str) and not self.value.strip():
            raise HookValidationError(
                "StrictHook",
                [("empty_string", f"Task '{task_model.name}': strict_hook value cannot be empty")]
            )
```

**Validation responsibility split:**
- **Mixin validates**: Jinja2 expression syntax (only when markers present)
- **Individual hooks validate**: Hook-specific constraints (empty strings, value types, etc.)

Always call `super().execute_hook_validations(task_model)` first in your validation method to ensure cooperative super() calls work correctly with multiple inheritance.

**Methods:**

#### `execute_hook_validations(task_model: TaskModel) -> None`
Validate hook configuration, including automatic Jinja2 validation for expressions containing markers.

Subclasses can override to add additional validation but must call `super().execute_hook_validations(task_model)` first.

**Parameters:**
- `task_model`: TaskModel to validate against

**Raises:**
- `HookValidationError`: If validation fails

#### `get_resolved_value(task: Task, host: Host | None = None, as_bool: bool = False, default: Any = None) -> Any`
Get the final resolved value, handling Jinja2 automatically.

Detects if `self.value` contains Jinja2 markers and resolves through variable system if needed.

**Parameters:**
- `task`: Task being executed (used to extract host for template resolution)
- `host`: The specific host to resolve for. **MUST** be provided when calling from `task_instance_started()` for per-host resolution
- `as_bool`: Convert result to boolean using standard truthy values
- `default`: Fallback value if `self.value` is falsy

**Returns:**
- Resolved value, optionally converted to boolean

**Raises:**
- `HookError`: If vars_manager not available (likely called outside lifecycle methods) or if task has no hosts

**Boolean Conversion:**

When `as_bool=True`, converts values using these rules:

- **Truthy strings** (case-insensitive): `"true"`, `"yes"`, `"1"`, `"on"`, `"y"`, `"t"`, `"enabled"`
- **Other strings**: Falsy
- **Booleans**: Returned as-is
- **Other types**: Converted via Python's `bool()`

**Important:** Only call `get_resolved_value()` inside lifecycle methods where context has been populated by the framework. When calling from `task_instance_started()`, always pass the `host` parameter explicitly.

#### `_is_jinja2_expression(value: Any) -> bool`
Check if value contains Jinja2 template markers.

**Parameters:**
- `value`: Value to check

**Returns:**
- `True` if value is string with Jinja2 markers (`{{`, `{%`, `{#`), `False` otherwise

#### `_resolve_jinja2(value: str, host: Host) -> Any`
Resolve Jinja2 template string through variable system.

**Parameters:**
- `value`: Template string to resolve
- `host`: Host to resolve for

**Returns:**
- Resolved value from template

**Raises:**
- `HookError`: If vars_manager not available in context

#### `_to_bool(value: Any) -> bool`
Convert value to boolean.

**Parameters:**
- `value`: Value to convert

**Returns:**
- Boolean representation using standard truthy values

#### `_validate_jinja2_string(task_model: TaskModel) -> None`
Validate that string value containing Jinja2 markers is a proper Jinja2 expression.

**Parameters:**
- `task_model`: The task model being validated

**Raises:**
- `HookValidationError`: If string with Jinja2 markers has invalid template syntax

### Built-in Hooks

#### IfHook

Conditionally execute tasks per host based on filter functions or Jinja2 expressions.

```python
from nornflow.builtins.hooks import IfHook
```

Supports two evaluation modes:

**Filter-based (dictionary syntax):**
```yaml
tasks:
  - name: napalm_get
    args:
      getters: ["facts"]
    if:
      platform: "ios"
```

**Jinja2 expression (string syntax):**
```yaml
tasks:
  - name: napalm_get
    args:
      getters: ["facts"]
    if: "{{ host.platform == 'ios' }}"
```

**Boolean Semantics:**
- `True` (or truthy): Task **executes** for the host
- `False` (or falsy): Task **skips** for the host

This follows Python's standard truthiness rules where `True` means "proceed" and `False` means "don't proceed".

**Features:**
- Uses `Jinja2ResolvableMixin` for Jinja2 expression support with automatic validation
- Evaluates per host (`run_once_per_task = False`)
- Sets skip flag on hosts that don't match condition
- Supports all registered inventory filters

#### SetToHook

Capture and store task results as runtime variables.

```python
from nornflow.builtins.hooks import SetToHook
```

**Store entire result:**
```yaml
tasks:
  - name: napalm_get
    args:
      getters: ["facts"]
    set_to: "device_facts"
```

**Extract nested data using dot notation:**
```yaml
tasks:
  - name: napalm_get
    args:
      getters: ["facts", "environment"]
    set_to:
      vendor: "vendor"
      cpu_usage: "environment.cpu.0.%usage"
```

**Features:**
- Extracts data from Nornir Result objects
- Supports dot notation for nested paths
- Array indexing with numeric indices
- Dictionary key access with special characters via `%` prefix
- Stores variables per-host in runtime context

#### ShushHook

Suppress task output printing conditionally.

```python
from nornflow.builtins.hooks import ShushHook
```

**Static suppression:**
```yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show version"
    shush: true
```

**Dynamic suppression:**
```yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show interfaces"
    shush: "{{ verbose_mode == false }}"
```

**Features:**
- Uses `Jinja2ResolvableMixin` for dynamic evaluation with automatic validation
- Runs once per task (`run_once_per_task = True`)
- Requires compatible processor with `supports_shush_hook` attribute
- Marks tasks in processor's suppression registry

## Variable System Classes

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

**Purpose:**
Acts as a proxy to provide direct access to host attributes and `host.data` dictionary values within Jinja2 templates. Managed by `NornFlowVariableProcessor` which sets the current host context before variable resolution.

**Key Features:**
- Read-only access to Nornir inventory
- Provides `host.name`, `host.platform`, `host.data.*` access in templates
- Automatically set by `NornFlowVariableProcessor` during task execution
- Does not modify Nornir inventory

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `current_host` | `Host \| None` | Current Nornir Host object being proxied |
| `nornir` | `Nornir \| None` | Nornir instance for inventory access |
| `current_host_name` | `str \| None` | Name of current host |

**Setting `current_host_name`:**
When set, looks up the host in Nornir inventory and sets `current_host`. If host not found or Nornir instance not set, clears current host context.

**Magic Method:**

#### `__getattr__(name: str) -> Any`
Dynamically retrieve attributes or data keys from current Nornir host.

Follows precedence:
1. Direct Host object attributes (e.g., `name`, `platform`, `data`)
2. Keys within `Host.data` dictionary (merged from host, groups, defaults)

**Parameters:**
- `name`: Attribute or data key name

**Returns:**
- Value from host's inventory

**Raises:**
- `VariableError`: If no Nornir instance or current host set, or if attribute/key not found

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

### NornFlowHookProcessor

Orchestrator processor that delegates execution to registered hooks.

```python
from nornflow.builtins.processors import NornFlowHookProcessor
```

**Purpose:**
Manages all hook executions by extracting hook information from task context and calling appropriate hook methods at each lifecycle point. Automatically added to processor chain when hooks are present in workflow.

**Key Features:**
- Delegates to registered hooks at appropriate lifecycle points
- Manages two-tier context system (workflow + task-specific)
- Injects complete context into hooks before execution
- Handles hook exception delegation to custom handlers

**Constructor:**

```python
def __init__(self, workflow_context: dict[str, Any] | None = None)
```

**Parameters:**
- `workflow_context`: Optional workflow-level context set during initialization

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `workflow_context` | `dict[str, Any]` | Workflow-level context (vars_manager, catalogs, etc.) |
| `task_specific_context` | `dict[str, Any]` | Current task-specific context (task_model, hooks) |
| `context` | `dict[str, Any]` | Combined workflow + task-specific context (read-only) |
| `task_hooks` | `list[Hook]` | Active hooks for current task (read-only) |

**Context Management:**

The processor manages two types of context:

1. **Workflow Context** (set once during initialization):
   - `vars_manager`: Variable resolution system
   - `nornir_manager`: Nornir operations manager  
   - `tasks_catalog`: Available tasks
   - `filters_catalog`: Available inventory filters
   - `workflows_catalog`: Available workflows

2. **Task-Specific Context** (set per task execution):
   - `task_model`: Current TaskModel being executed
   - hooks: List of Hook instances for this task

The `context` property always returns merged dictionary of both contexts. Task-specific context is set at task start and cleared at task completion.

**Lifecycle Methods:**

All lifecycle methods use the `@hook_delegator` decorator which:
- Extracts hooks from `task_specific_context`
- Injects merged context into each hook's `_current_context`
- Delegates to corresponding hook methods
- Handles custom exception handlers defined by hooks

#### `task_started(task: Task) -> None`
Delegates to hooks' `task_started` methods.

#### `task_completed(task: Task, result: AggregatedResult) -> None`
Delegates to hooks' `task_completed` methods and clears task-specific context.

#### `task_instance_started(task: Task, host: Host) -> None`
Delegates to hooks' `task_instance_started` methods.

#### `task_instance_completed(task: Task, host: Host, result: MultiResult) -> None`
Delegates to hooks' `task_instance_completed` methods.

#### `subtask_instance_started(task: Task, host: Host) -> None`
Delegates to hooks' `subtask_instance_started` methods.

#### `subtask_instance_completed(task: Task, host: Host, result: MultiResult) -> None`
Delegates to hooks' `subtask_instance_completed` methods.

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
