# NornFlow Hooks Guide

## Table of Contents

- [Overview](#overview)
- [Hooks as Nornir Processors](#hooks-as-nornir-processors)
- [Execution Lifecycle](#execution-lifecycle)
- [Performance Characteristics](#performance-characteristics)
- [Hook-Driven Template Resolution](#hook-driven-template-resolution)
- [Built-in Hooks](#nornflows-built-in-hooks)
  - [The `if` Hook](#the-if-hook)
  - [The `set_to` Hook](#the-set_to-hook)
  - [The `shush` Hook](#the-shush-hook)
- [Hook Configuration](#hook-configuration)
  - [Task-Level Configuration](#task-level-configuration)
  - [Multiple Hooks per Task](#multiple-hooks-per-task)
- [Creating Your Custom Hooks](#creating-your-custom-hooks)
  - [Basic Hook Structure](#basic-hook-structure)
  - [Hook Registration](#hook-registration)
  - [Hook Discovery and Loading](#hook-discovery-and-loading)
  - [Lifecycle Methods](#lifecycle-methods)
  - [Execution Scopes](#execution-scopes)
  - [Context Access](#context-access)
  - [Jinja2 Template Support](#jinja2-template-support)
  - [Hook Validation](#hook-validation)
  - [Custom Exception Handling](#custom-exception-handling)
- [Advanced Concepts](#advanced-concepts)
  - [Hook Processor Integration](#hook-processor-integration)
  - [Flyweight Pattern Implementation](#flyweight-pattern-implementation)

## Overview

Hooks are a powerful extension mechanism provided by NornFlow, allowing you to inject custom behavior into task execution without modifying task code. They provide a clean, declarative way to add functionality at specific points in the task lifecycle.

### Key Concepts

- **Hooks are Nornir Processors**: Hooks are implemented as Nornir processors, giving them access to the full task execution lifecycle.
- **Lifecycle Integration**: Hooks can execute code before, during, and after task execution.
- **Configuration-Driven**: Hooks are configured in workflow YAML/dict and applied automatically.
- **Validation**: Hook configurations are validated during workflow preparation.
- **Context Awareness**: Hooks have access to variables, inventory data, and execution context.

**Potential use cases:**
- **Task-level orchestration**: Implement setup or teardown logic that runs once per task across all hosts
- **Per-host customization**: Add behavior that executes independently for each host in your inventory
- **Selective application**: Apply specialized logic to specific tasks without affecting others
- **Result processing**: Capture, transform, or validate task outcomes on a per-task or per-host basis
- **Execution control**: Conditionally skip or modify task execution based on runtime state
- **Cross-cutting concerns**: Implement logging, auditing, or notification logic without cluttering task code
- **Dynamic behavior injection**: Add functionality to tasks without modifying their source code

Unlike Nornir processors (which apply globally to all tasks) or filters (which apply at the inventory level), hooks provide surgical precision: they only activate when explicitly configured on individual tasks in your workflow.

## Hook Architecture

### Hooks as Nornir Processors

Under the hood, hooks are Nornir processors managed by the [`NornFlowHookProcessor`](../nornflow/builtins/processors/hook_processor.py). The design provides:

1. **Full lifecycle access**: Hooks can react to any point in task execution
2. **Processor chain integration**: Hooks work alongside other processors
3. **Performance optimization**: Hook instances are cached and reused

### Execution Lifecycle

Hooks can participate in these task lifecycle events:

```
┌─────────────────────────────────────────────────────────┐
│                    Task Execution                       │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   task_started       │  ← Once per task
              │   (all hosts)        │
              └──────────┬───────────┘
                         │
         ┌───────────────┴───────────────┐
         │  For each host in parallel:   │
         └───────────────┬───────────────┘
                         │
              ┌──────────▼───────────┐
              │ task_instance_       │  ← Per host
              │ started              │
              └──────────┬───────────┘
                         │
              ┌──────────▼───────────┐
              │ Execute task         │
              │ function             │
              └──────────┬───────────┘
                         │
              ┌──────────▼───────────┐
              │ task_instance_       │  ← Per host
              │ completed            │
              └──────────┬───────────┘
                         │
         ┌───────────────┴───────────────┐
         │  After all hosts complete:    │
         └───────────────┬───────────────┘
                         │
              ┌──────────▼───────────┐
              │   task_completed     │  ← Once per task
              │   (all hosts)        │
              └──────────────────────┘
```

### Performance Characteristics

- **Hook instances**: Created ONCE per unique (hook_class, value) pair 
- **Memory usage**: O(unique_hooks) - shared instances across tasks
- **Thread safety**: Guaranteed via execution context isolation
- **Registration**: Happens at import time via `__init_subclass__`
- **Validation**: Happens once per task during workflow preparation

### Hook-Driven Template Resolution

Hook-Driven Template Resolution is a mechanism for optimizing variable template resolution when hooks need to evaluate conditions or perform logic before task args templates are processed. This is an **optional capability** that hooks can opt into via the `requires_deferred_templates` class attribute.

#### How It Works

The system operates in two phases when deferred processing is requested:

**Phase 1 - Pre-Execution Logic:**
1. The Hook class declares `requires_deferred_templates = True`
2. `NornFlowVariableProcessor` detects this requirement during `task_instance_started()`
3. **Task parameter templates** are stored without resolution (e.g., `args: {config: "{{ some_var }}"`)
4. **Hook configuration templates**, if any, are resolved using current variable context (if the hook supports jinja2 templates as input - as is the case with the `if` and `shush` hooks, for example)
5. Hook performs its pre-execution logic using the resolved hook configurations

**Phase 2 - Just-In-Time Resolution:**
1. After hook logic completes, the hook triggers `resolve_deferred_params()`
2. `NornFlowVariableProcessor` resolves stored task parameter templates using the current host context
3. Task executes with fully resolved parameters

#### Mandatory vs Optional

**This feature is completely optional:**
- Hooks that don't need deferred processing work normally (immediate resolution)
- Only hooks that declare `requires_deferred_templates = True` trigger deferred mode
- The processor automatically selects the appropriate strategy based on hook declarations

> **NOTE FOR DEVELOPERS:** Developers writing their own custom Hooks are strongly encouraged to check the code (and included docstrings) in [nornflow/vars/processors.py](../nornflow/vars/processors.py) and [nornflow/builtins/hooks/if_hook.py](../nornflow/builtins/hooks/if_hook.py) for a deeper understanding and a working example of a Hook that fully takes advantage of this feature.

## NornFlow's Built-in Hooks

NornFlow includes three built-in hooks that demonstrate the framework's capabilities and serve as practical examples for creating your own custom hooks.

### The `if` Hook

Conditionally execute tasks based on filter functions or Jinja2 expressions.

You are encouraged to examine the source code for the `if` Hook [here](../nornflow/builtins/hooks/if_hook.py), but as a summary, here is how it works:

1. **task_started**: Decorates the task function with skip-checking logic
2. **task_instance_started**: Evaluates condition for each host
3. If condition is evaluated to `false`: Sets `nornflow_skip_flag` in `host.data`
4. Decorated function checks flag and returns skipped Result if set

#### Configuration Formats

The `if` Hook accepts inputs either as Jinja2 templates or as Nornir filters in the filters catalogue.

##### Jinja2 Expression Details

Expressions have access to:
- `host.*` namespace (Nornir inventory)
- All NornFlow variables (runtime, CLI, domain, default, env)
- All Jinja2 filters (defaults, and NornFlow provided)

Users must ensure that the template input evaluates to boolean:
```yaml
# ✅ Valid
if: "{{ enabled }}"
if: "{{ host.platform == 'ios' }}"
if: "{{ count > 5 }}"

# ❌ Invalid (not boolean)
if: "{{ host.name }}"  # Returns string
if: "{{ vlans }}"      # Returns list
```

##### Filter Function Details

The Filter functions must:
1. Be registered in filters catalog
2. Accept `Host` as first parameter
3. Return boolean value

```python
# Custom filter hypothetical example
def platform_filter(host: Host, platform: str) -> bool:
    """Filter hosts by platform."""
    return host.platform == platform
```

**Using the `if` Hook with Nornir Filter Functions**
```yaml
tasks:
  - name: netmiko_send_command
    if:
      platform_filter: "ios" # assuming a 'platform_filter' exists in the catalog
    args: 
      command: "show version"
```

#### How IfHook Uses Hook-Driven Template Resolution

The IfHook leverages Hook-Driven Template Resolution to evaluate conditions before resolving task argument templates, preventing errors on hosts where variables might not exist.

**Declaration:**
```python
class IfHook(Hook, Jinja2ResolvableMixin):
    hook_name = "if"
    run_once_per_task = False
    requires_deferred_templates = True  # Enables two-phase processing
```

**Usage Flow:**
1. **Configuration**: User configures `if` condition in workflow YAML
2. **Declaration Detection**: `NornFlowVariableProcessor` sees `requires_deferred_templates = True`
3. **Template Storage**: Task parameters with `{{ variables }}` are stored without resolution
4. **Condition Evaluation**: `IfHook` evaluates the condition using current variable context
5. **Skip Decision**: Hosts failing the condition get `nornflow_skip_flag` set
6. **Just-in-Time Resolution**: For passing hosts, `skip_if_condition_flagged` decorator resolves templates via `resolve_deferred_params()` method provided by the `NornFlowVariableProcessor`.
7. **Task Execution**: Task runs with resolved parameters only on eligible hosts

**Example:**
```yaml
tasks:
  - name: configure_feature
    if: "{{ host.data.has_feature }}"  # Condition uses host inventory data
    args:
      config: "{{ feature_template }}"  # Template uses variable that might not exist on all hosts
```

Without deferred processing, this would fail on hosts missing `feature_template`. With deferred processing, only hosts that pass the `if` condition have their templates resolved.

### The `set_to` Hook

You are encouraged to refer to the source code for the `set_to` Hook [here](../nornflow/builtins/hooks/set_to.py), but here is a summary of how it works:

1. **Validation**: Checks configuration format during task preparation
2. **task_instance_completed**: Runs after task completes on each host
3. **Storage**: Stores extracted value as runtime variable for the host

The actual data captured depends on the configuration format used for the `set_to` hook:  
   - In *simple mode*, the entire Nornir's `Result` object returned by a task execution is captured and assigned
   - In *extraction mode*, you specify exactly what nested data out of the `Result` object you want to capture and assign to your variable.

#### Configuration Formats

**Simple Mode (stores the complete Nornir's `Result` object)**
```yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show version"
    set_to: device_facts # stores the entire Result object returned by `netmiko_send_command` to a 'device_facts' var
```

**Extraction Mode (extracts specific data from the Nornir's `Result.result` object)**
```yaml
tasks:
  - name: napalm_get
    args:
      getters: ["facts", "interfaces"]
    set_to:
      mgmt_ip: "interfaces.Management1.ipv4.address" # stores the IPv4 Address deeply nested in the Result object returned by the `napalm_get` task to a var named 'mgmt_ip'
```

#### Extraction Path Syntax

Access data from `Result.result` dictionary using:

**Dot notation for nested dicts:**

The below would update/create two NornFlow vars named "**vendor**" (with the value extracted from `Result.result['vendor']`) and "**cpu**" (with the value extracted from `Result.result['environment']['cup']['usage']`)

```yaml
set_to:
  vendor: "vendor"
  cpu: "environment.cpu.usage"
```

**Bracket notation for lists:**

The below would update/create two NornFlow vars named "**first_cpu**" (with the value extracted from `Result.ressult['environment']['cpu'][0]['usage']`) and "**interface_ip**" (with the value extracted from `Result.result['interfaces']['eth0']['ipv4'][0]['address']`). 

```yaml
set_to:
  first_cpu: "environment.cpu[0].usage"
  interface_ip: "interfaces.eth0.ipv4[0].address"
```

**Special prefixes for Result attributes:**
```yaml
set_to:
  task_failed: "_failed" # the `Result.failed` object
  task_changed: "_changed" # the `Result.changed` object
  complete_result: "_result" # the `Result.result` object
```

### The `shush` Hook

Signal to output processors if a task results should be suppressed.

You are encouraged to refer to the source code for the `shush` Hook [here](../nornflow/builtins/hooks/shush.py), but here is a summary of how it works:

1. **task_started**: Checks for compatible processors with `supports_shush_hook` attribute
2. Evaluates the configured value (boolean or Jinja2 expression)
3. If the value evaluates to `True`: Marks task in suppression set on Nornir instance. It uses a unique key (combining task name and ID) to correctly handle multiple tasks with the same name.
4. Output processor checks suppression set and skips output display while preserving all data
5. **task_completed**: Removes task from suppression set after completion

#### Configuration Formats

**Boolean (static suppression)**
```yaml
tasks:
  - name: netmiko_send_command
    shush: true
    args:
      command_string: "show version"
```

**Jinja2 Expression (dynamic suppression)**

```yaml
vars:
  debug_mode: false
  quiet_mode: true
  
tasks:
  - name: backup_config
    shush: "{{ not debug_mode }}"  # Suppress unless debugging
    set_to: config_backup
    
  - name: get_facts
    shush: "{{ quiet_mode }}"  # Suppress based on variable
    set_to: device_facts
    
  - name: show_interfaces
    shush: "{{ host.platform == 'ios'}}"  # dynamic condition
```

**Expression Evaluation:**
- Jinja2 expressions have access to all NornFlow variables (runtime, CLI, inline, domain, default, env)
- Expressions have access to host.* namespace (Nornir inventory)
- Must contain Jinja2 markers ({{, {%, or {#)
- Expressions are resolved to strings, then evaluated as boolean. 
- String values "true", "yes", "1" evaluate to True. 
- All other string values evaluate to False. 

#### Processor Compatibility

The `shush` hook is **automatically supported** by NornFlow's `DefaultNornFlowProcessor`, which is applied by default to all workflows.

If you configure custom processors via the `processors` setting (either globally in `nornflow.yaml` or per-workflow), the `shush` hook will only work if at least one of those processors also implement `supports_shush_hook` attribute

In summary: 
- **Signal mechanism**: The hook doesn't implement suppression directly - it signals to compatible processors
- **Data preservation**: Result objects remain intact regardless of suppression
- **Warning on incompatibility**: Shows warning if no compatible processor is found

**Configuring Custom Processors:**

```yaml
# nornflow.yaml (global) or workflow YAML (per-workflow)
processors:
  - class: "my_package.MyCustomProcessor"
    # ⚠️ shush won't work unless MyCustomProcessor supports it
```

To support `shush` in a custom processor, your processor's code would have to include something like this:

```python
class MyCustomProcessor(Processor):
    """Custom processor that supports the shush hook for output suppression."""
    
    supports_shush_hook = True
    
    def _is_output_suppressed(self, task: Task) -> bool:
        if not hasattr(task.nornir, "_nornflow_suppressed_tasks"):
            return False

        for proc in task.nornir.processors:
            if hasattr(proc, "task_specific_context"):
                nornflow_task_model = proc.task_specific_context.get("task_model")
                return nornflow_task_model.canonical_id in task.nornir._nornflow_suppressed_tasks
    
    def task_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        """Process task completion and handle output suppression."""
        suppress_output = self._is_output_suppressed(task)
        
        if suppress_output:
            # Skip printing or handle suppressed output (e.g., print a shushed message)
            print(f"Task '{task.name}' on '{host.name}' output suppressed.")
        else:
            # Normal output logic here ...
```

## Hook Configuration

### Task-Level Configuration

Hooks are configured directly on tasks in workflow YAML/dict like if it were one of the attributes of a task, rather than args passed to a task:

```yaml
# ✅ Correct - hooks configured at task level
tasks:
  - name: my_task
    args:                  # Task arguments
      arg1: true
      arg2: "device"
    set_to: result_var     # Hook configuration

# ❌ Incorrect - hooks inside args block
tasks:
  - name: my_task
    args:
      arg1: true
      arg2: "device"
      set_to: result_var       # Wrong! This is passed to task function
```

### Multiple Hooks per Task

Tasks can use multiple hooks simultaneously:

```yaml
tasks:
  - name: get_data
    if: "{{ should_run }}"
    set_to: captured_data
    shush: true
```

**Execution order:**
1. `if` hook evaluates condition (task_instance_started)
2. If condition passes, task executes
3. `set_to` hook captures results (task_instance_completed)
4. `shush` hook affects output display

## Creating Your Custom Hooks

### Basic Hook Structure

Creating a custom hook is simple - just inherit from `Hook` and define a `hook_name`. Registration happens automatically!

```python
from typing import Any
from nornir.core.task import Task
from nornir.core.inventory import Host
from nornflow.hooks import Hook

class MyCustomHook(Hook):
    hook_name = "my_custom"
    run_once_per_task = False
    
    def __init__(self, value: Any = None):
        """Initialize with configuration value from YAML."""
        super().__init__(value)
        self.my_config = value
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        """Called before task executes on each host."""
        pass
    
    def task_instance_completed(self, task: Task, host: Host, result: Any) -> None:
        """Called after task executes on each host."""
        pass
```

### Hook Registration

**Automatic Registration via Inheritance**

When you define a hook class that inherits from `Hook` and sets a `hook_name`, it's automatically registered when Python imports the module.

```python
from nornflow.hooks import Hook

class MyHook(Hook):
    hook_name = "my_hook"
    ...
```

After your hook module is imported (via `local_hooks`), it's immediately available in workflows:

```yaml
tasks:
  - name: netmiko_send_command
    my_hook: "configuration value"
```

### Hook Discovery and Loading

**This is critical**: For NornFlow to find and register your custom hooks, you need to either:
1. Place them in the default hooks directory in the root of your NornFlow project, OR
2. Configure `local_hooks_dirs` to point to your custom location

#### The `local_hooks_dirs` Setting

Configure this in your `nornflow.yaml` file:

```yaml
# nornflow.yaml
local_hooks_dirs:
  - "hooks"
  - "custom_extensions/hooks"
  - "/absolute/path/to/hooks"
```

**Behavior:**
- If not configured: NornFlow defaults to `["hooks"]` (a hooks directory in project root)
- If configured: NornFlow uses ONLY the specified directories

#### How Hook Discovery Works

When NornFlow starts, it:

1. **Reads `local_hooks_dirs`** from settings (or uses default `["hooks"]`)
2. **Recursively scans** each directory for `.py` files
3. **Imports** each Python module found
4. **Registration happens automatically** via `__init_subclass__` during import
5. **Hooks become available** for use in workflows

```
Project Structure:
├── nornflow.yaml
├── hooks/
│   ├── __init__.py
│   ├── validation_hooks.py      ← Discovered and imported
│   ├── notification_hooks.py    ← Discovered and imported
│   └── custom/
│       └── special_hooks.py     ← Discovered and imported (recursive)
├── workflows/
│   └── my_workflow.yaml
└── ...
```

**Registration timing:**
- Hooks are registered **at import time** when the `Hook.__init_subclass__` mechanism is triggered
- This happens **before** any workflow execution
- The `Hook.__init_subclass__` mechanism adds the hook to the global registry immediately

**Common pitfalls:**

1. **Wrong directory structure:**
   ```
   ❌ Wrong:
   project/
   └── my_hooks/          # Doesn't match default or configured path
       └── custom.py
   
   ✅ Correct (using default):
   project/
   └── hooks/             # Matches default
       └── custom.py
   
   ✅ Correct (using custom):
   project/
   ├── nornflow.yaml      # local_hooks_dirs: ["my_hooks"]
   └── my_hooks/          # Matches configuration
       └── custom.py
   ```

2. **Missing `hook_name`:**
   ```python
   # ❌ Hook won't be registered
   class MyHook(Hook):
       pass  # No hook_name defined
   
   # ✅ Correct
   class MyHook(Hook):
       hook_name = "my_hook"
   ```

3. **Syntax errors in hook files:**
   - Python import errors will prevent hook registration
   - Check logs for import failures during NornFlow startup

### Lifecycle Methods

Unlike traditional Nornir Processor implementations where you must explicitly define all lifecycle methods (even if just with `pass` statements), NornFlow's Hook framework handles this automatically. You only need to override the specific lifecycle methods your hook actually uses.

**Available lifecycle methods** (override only what you need):

```python
class Hook(ABC):
    # Task-level (runs once per task)
    def task_started(self, task: Task) -> None:
        """Called when task starts (before any host)."""
        pass
    
    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Called when task completes (after all hosts)."""
        pass
    
    # Instance-level (runs per host)
    def task_instance_started(self, task: Task, host: Host) -> None:
        """Called before task executes on specific host."""
        pass
    
    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Called after task executes on specific host."""
        pass
    
    # Subtask support
    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Called before subtask executes on host."""
        pass
    
    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Called after subtask executes on host."""
        pass
```

**Example - Hook using only one lifecycle method:**
```python
from nornir.core.task import Task
from nornir.core.inventory import Host
from nornflow.hooks import Hook

class SimpleValidationHook(Hook):
    """Only needs task_instance_started - no need to define others."""
    
    hook_name = "simple_validation"
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        if not host.username:
            raise ValueError(f"No username for {host.name}")
```

The base `Hook` class already provides default implementations (empty `pass` statements) for all lifecycle methods, so your custom hook only needs to inherit from `Hook` and set `hook_name`.

### Execution Scopes

Control whether your hook executes once per task or independently for each host using the `run_once_per_task` class attribute:

**Once per task** - Hook logic runs only for the first host, subsequent hosts skip execution:

```python
class MyHook(Hook):
    run_once_per_task = True
  
```

Use this when your hook's logic applies to the entire task regardless of which hosts are involved. Examples: deciding whether to suppress output (`shush`), logging task start/completion, or setting task-wide flags.

**Per host (default)** - Hook logic runs independently for every host:

```python
class MyHook(Hook):
    run_once_per_task = False  # This is the default

```

Use this when your hook needs to evaluate conditions or perform actions specific to each individual host. Examples: conditional execution based on host attributes (`if`), storing per-host results (`set_to`), or per-host validation.


### Context Access

Hooks receive context from the `NornFlowHookProcessor`. You can easily access various NornFlow components through it by accessing `self.context`:

```python
class MyHook(Hook):
    def task_instance_started(self, task: Task, host: Host):
        context = self.context
        
        vars_manager = context.get("vars_manager")
        task_model = context.get("task_model")
        tasks_catalog = context.get("tasks_catalog")
        filters_catalog = context.get("filters_catalog")
        workflows_catalog = context.get("workflows_catalog")
        nornir_manager = context.get("nornir_manager")
        
        device_ctx = vars_manager.get_device_context(host.name)
        my_var = vars_manager.get_nornflow_variable("my_var", host.name)
```

### Jinja2 Template Support

NornFlow provides an optional `Jinja2ResolvableMixin` that makes it easy to add Jinja2 template support to your custom hooks. This mixin handles all the complexity of detecting Jinja2 expressions, validating them during workflow preparation, resolving them through the variable system at runtime, and converting results to the appropriate type.  

#### When to Use the Mixin

The mixin is **entirely optional** and should only be used when:

1. ✅ **Your hook accepts user-provided values** that could benefit from dynamic resolution
2. ✅ **You want to support both static values AND Jinja2 expressions** seamlessly

**Do NOT use the mixin when:**

1. ❌ **Your hook should NEVER accept Jinja2 expressions**
2. ❌ **Your hook has complex custom Jinja2 resolution and/or validation logic** that conflicts with standard Jinja2 resolution provided by the Mixin

#### How the Mixin Works

When you use the mixin, it provides a single method `get_resolved_value()` that:

1. Checks if `self.value` contains Jinja2 markers (`{{`, `{%`, `{#`)
2. If yes: Resolves the template using NornFlow's variable system
3. If no: Returns the value as-is
4. Optionally converts the result to boolean or applies a default

**This means your hook automatically accepts BOTH:**
- Static values: `my_hook: true`, `my_hook: "static_string"`
- Jinja2 expressions: `my_hook: "{{ some_variable }}"`, `my_hook: "{{ host.platform == 'ios' }}"`

#### Basic Usage

```python
from nornir.core.task import Task
from nornir.core.inventory import Host
from nornflow.hooks import Hook, Jinja2ResolvableMixin

class MyConditionalHook(Hook, Jinja2ResolvableMixin):
    """Hook that conditionally executes based on static or dynamic values."""
    
    hook_name = "my_hook"
    run_once_per_task = False
    
    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        super().execute_hook_validations(task_model)
        # your own custom validations here if any...
        # otherwise, you don't even need to override this method at all
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        condition = self.get_resolved_value(task, host=host, as_bool=True, default=False)
        
        if condition:
            print(f"Executing for {host.name}")
```

**YAML usage:**
```yaml
tasks:
  # Static boolean value
  - name: task1
    my_hook: true
  
  # Jinja2 expression
  - name: task2
    my_hook: "{{ enabled and host.platform == 'ios' }}"
  
  # Static string (evaluated as boolean)
  - name: task3
    my_hook: "yes"  # Truthy string value
```

#### Automatic Validation

When you use the mixin, **validation happens automatically** during workflow preparation for Jinja2 expressions. The mixin validates that strings containing Jinja2 markers (`{{`, `{%`, `{#`) are properly formatted templates.

**What gets validated by the mixin:**
- **Jinja2 expressions are validated**: `my_hook: "{{ variable }}"` - Template syntax checked
- **Plain strings are NOT validated**: `my_hook: "plain text"` - Passed through as-is
- **Empty strings are NOT validated**: `my_hook: ""` - Treated as falsy value
- **Non-string values skip validation**: `my_hook: true`, `my_hook: {"key": "value"}` - No checks. Returns as-is for your Hook's own processing logic.

**Individual hooks can add stricter validation** if needed:

```python
from nornflow.hooks import Hook, Jinja2ResolvableMixin
from nornflow.hooks.exceptions import HookValidationError

class StrictHook(Hook, Jinja2ResolvableMixin):
    """Hook that rejects empty strings as meaningless configuration."""
    
    hook_name = "strict_hook"
    
    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        super().execute_hook_validations(task_model) # ATTENTION: If you don't call super's execute_hook_validations, you loose all the Mixin's validations.
        
        if isinstance(self.value, str) and not self.value.strip():
            raise HookValidationError(
                "StrictHook",
                [("empty_string", f"Task '{task_model.name}': strict_hook value cannot be empty")]
            )
```

**Example: The `if` hook adds empty string validation** because an empty condition is meaningless:

```python
class IfHook(Hook, Jinja2ResolvableMixin):
    hook_name = "if"
    
    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        super().execute_hook_validations(task_model)
        
        if isinstance(self.value, str):
            if not self.value.strip():
                raise HookValidationError(
                    "IfHook",
                    [("empty_string", f"Task '{task_model.name}': if condition cannot be empty string")]
                )
```

**Validation responsibility split:**
- **Mixin validates**: Jinja2 expression syntax (only when markers present)
- **Individual hooks validate**: Hook-specific constraints (empty strings, value types, etc.)

The mixin uses **cooperative super() calls**, so it works correctly with multiple inheritance. You are **strongly** encouraged to always call `super().execute_hook_validations(task_model)` first in your validation method.

#### The `get_resolved_value()` Method

```python
def get_resolved_value(
    self,
    task: Task,
    host: Host | None = None,
    as_bool: bool = False,
    default: Any = None
) -> Any:
    """Get the final resolved value, handling Jinja2 automatically."""
    ...
```

**Parameters:**
- `task`: The current Nornir task (used to extract host for template resolution)
- `host`: The specific host for per-host resolution (MUST provide in task_instance_started)
- `as_bool`: Convert the final result to boolean (useful for conditional hooks)
- `default`: Fallback value if `self.value` is None or empty

**Return value:**
- If `self.value` is falsy: Returns `default`
- If `self.value` contains Jinja2: Resolves template and returns result
- If `self.value` is static: Returns value as-is
- If `as_bool=True`: Converts final result to boolean

#### Boolean Conversion

When using `as_bool=True`, the mixin converts values to boolean using NornFlow's standard truthy values:

**Truthy strings** (case-insensitive):
- `"true"`, `"yes"`, `"1"`, `"on"`, `"y"`, `"t"`, `"enabled"`

**Falsy strings:**
- Any other string value

**Other types:**
- Booleans: Returned as-is
- Other values: Converted using Python's `bool()`

```python
# All these evaluate to True:
get_resolved_value(task, as_bool=True)  # if self.value = "yes"
get_resolved_value(task, as_bool=True)  # if self.value = "{{ 'enabled' }}"
get_resolved_value(task, as_bool=True)  # if self.value = True

# All these evaluate to False:
get_resolved_value(task, as_bool=True)  # if self.value = "no"
get_resolved_value(task, as_bool=True)  # if self.value = "{{ 'disabled' }}"
get_resolved_value(task, as_bool=True)  # if self.value = False
```

#### Examples from Built-in Hooks

**The `shush` hook** (see [source](../nornflow/builtins/hooks/shush.py)):
```python
class ShushHook(Hook, Jinja2ResolvableMixin):
    hook_name = "shush"
    run_once_per_task = True
    
    def task_started(self, task: Task) -> None:
        # Single line to get resolved boolean value
        should_suppress = self.get_resolved_value(task, as_bool=True, default=False)
        
        if should_suppress:
            # Mark task for suppression
            ...
```

**The `if` hook** (see source) uses the mixin for Jinja2 expression support:
```python
class IfHook(Hook, Jinja2ResolvableMixin):
    hook_name = "if"
    run_once_per_task = False
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        if isinstance(self.value, str):
            should_run = self.get_resolved_value(task, host=host, as_bool=True, default=True)
        else:
            should_run = self._evaluate_filter_condition(host)
        
        if not should_run:
            host.data["nornflow_skip_flag"] = True
```

#### Advanced: Custom Type Conversion

If you need custom type conversion beyond boolean, you can use the mixin's resolution and add your own logic:

```python
class NumericHook(Hook, Jinja2ResolvableMixin):
    hook_name = "numeric"
    
    def task_instance_started(self, task: Task, host: Host) -> None:
        raw_value = self.get_resolved_value(task, host=host)
        
        try:
            numeric_value = int(raw_value)
        except (ValueError, TypeError):
            numeric_value = 0
        
        if numeric_value > 10:
            ...
```

### Hook Validation

Validate configuration during task preparation:

```python
from nornflow.hooks.exceptions import HookValidationError

class MyHook(Hook):
    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        
        if not isinstance(self.value, str):
            raise HookValidationError(
                f"my_hook expects string, got {type(self.value).__name__}"
            )
        
        if not self.value.strip():
            raise HookValidationError("my_hook value cannot be empty")
        
        incompatible_tasks = ["set", "echo"]
        if task_model.name in incompatible_tasks:
            raise HookValidationError(
                f"my_hook cannot be used with task '{task_model.name}'"
            )
```

### Custom Exception Handling

Hooks can define custom exception handlers to gracefully handle specific error conditions without stopping workflow execution:

> NOTE: below example in hypothetical and not necessarily the optimal way of achieving the purpose.

```python
import logging
import smtplib
from email.message import EmailMessage
from nornir.core.task import Task, MultiResult
from nornir.core.inventory import Host
from nornflow.hooks import Hook

logger = logging.getLogger(__name__)


class DeviceUnreachableError(Exception):
    """Raised when device cannot be reached."""
    pass


class NotifyOnErrorHook(Hook):
    """Send email notification when specific errors occur."""
    
    hook_name = "notify_on_error"
    
    exception_handlers = {
        DeviceUnreachableError: "_handle_unreachable_device"
    }
    
    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        if result.failed and "unreachable" in str(result.exception).lower():
            raise DeviceUnreachableError(f"Device {host.name} is unreachable")
    
    def _handle_unreachable_device(self, exception: Exception, task: Task, args: tuple) -> None:
        """Send email notification without failing the workflow."""
        host = args[1] if len(args) > 1 else "unknown"
        
        logger.error(f"Device unreachable: {host} - {exception}")
        
        msg = EmailMessage()
        msg.set_content(f"Device {host} became unreachable during task '{task.name}'")
        msg['Subject'] = f'NornFlow Alert: Device Unreachable'
        msg['From'] = self.value.get('from_email', 'nornflow@example.com')
        msg['To'] = self.value.get('to_email', 'ops@example.com')
        
        try:
            smtp_server = self.value.get('smtp_server', 'localhost')
            with smtplib.SMTP(smtp_server) as s:
                s.send_message(msg)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
```

Usage:
```yaml
tasks:
  - name: netmiko_send_config
    notify_on_error:
      from_email: "nornflow@company.com"
      to_email: "ops-team@company.com"
      smtp_server: "smtp.company.com"
    args:
      config_commands:
        - "interface GigabitEthernet0/1"
        - "description Production Interface"
```

**Key points about exception handlers:**
- They catch exceptions raised within hook methods
- Allow custom error handling without stopping workflow execution
- Useful for logging, notifications, or storing error state
- Handler methods receive: `(exception, task, args)` where `args` is the tuple of original method arguments

## Advanced Concepts

### Hook Processor Integration

The `NornFlowHookProcessor` orchestrates all hooks:

```python
class NornFlowHookProcessor(Processor):
    """Manages hook execution and context injection."""
    
    @property
    def task_hooks(self) -> list[Hook]:
        """Get hooks for current task from task-specific context."""
        return self.task_specific_context.get('hooks', [])
    
    @hook_delegator
    def task_instance_started(self, task: Task, host: Host):
        """Automatically delegates to all task hooks."""
        pass
```

The `@hook_delegator` decorator:
1. Extracts method name (e.g., "task_instance_started")
2. Finds all hooks with that method
3. Checks `should_execute()` for each hook
4. Injects context via `_current_context`
5. Calls hook method
6. Handles exceptions via `exception_handlers`

### Flyweight Pattern Implementation

Hook instances are created once and reused:

```python
class HookableModel:
    """Base class for models supporting hooks."""
    
    _hooks_cache: list[Hook] | None = None
    
    def get_hooks(self) -> list[Hook]:
        """Get or create hook instances (Flyweight)."""
        if self._hooks_cache is not None:
            return self._hooks_cache
        
        self._hooks_cache = load_hooks(self.hooks or {})
        return self._hooks_cache
```

This means:
- Same hook configuration = same hook instance
- Memory efficient for large workflows
- Thread-safe via caching mechanism

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./variables_basics.md">← Previous: Variables Basics</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./nornflow_settings.md">Next: NornFlow Settings →</a>
</td>
</tr>
</table>

</div>
