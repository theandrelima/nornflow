# Blueprints Guide

## Table of Contents
- [Overview](#overview)
- [What Are Blueprints?](#what-are-blueprints)
- [When to Use Blueprints](#when-to-use-blueprints)
- [Creating Blueprints](#creating-blueprints)
  - [Blueprint Structure](#blueprint-structure)
  - [Blueprint Discovery](#blueprint-discovery)
  - [Blueprint Catalog](#blueprint-catalog)
- [Using Blueprints in Workflows](#using-blueprints-in-workflows)
  - [Basic Blueprint Reference](#basic-blueprint-reference)
  - [Conditional Blueprint Inclusion](#conditional-blueprint-inclusion)
  - [Nested Blueprints](#nested-blueprints)
  - [Dynamic Blueprint Selection](#dynamic-blueprint-selection)
- [Variable Resolution in Blueprints](#variable-resolution-in-blueprints)
  - [Assembly-Time vs Runtime](#assembly-time-vs-runtime)
  - [Variable Precedence for Blueprints](#variable-precedence-for-blueprints)
  - [Using Variables in Blueprint References](#using-variables-in-blueprint-references)
- [Blueprint Composition Strategies](#blueprint-composition-strategies)
- [Blueprint Nesting: Circular vs Repeated Use](#blueprint-nesting-circular-vs-repeated-use)

## Overview

Blueprints solve a fundamental problem in workflow automation: **how do you reuse common task sequences without copy-pasting them everywhere?**. 

Instead of repeating the same 5-10 tasks across multiple workflows, you define them once as a blueprint and reference them by the blueprint name, just like you do with a workflow. You can think of blueprints as 'macros' or 'functions' that allows you to define automation once, and reuse it wherever it makes sense to. 

Blueprints are expanded during workflow loading (assembly-time), meaning they become part of the workflow structure before execution begins. 

**Key characteristics:**
- **Reusable**: Define once, use in multiple workflows
- **Composable**: Blueprints can reference other blueprints
- **Conditional**: Include blueprints based on conditions
- **Parameterizable**: Use variables to customize behavior
- **Assembly-time**: Expanded before workflow execution starts

## What Are Blueprints?

Blueprints are YAML files containing a `tasks` list that can be referenced by name or path within workflows. Unlike workflows, blueprints:

- Contain **ONLY** a `tasks` root-level key (no workflow metadata like name, description, etc.)
- Are **referenced** within workflows, **not executed directly**
- Support **nested composition** (blueprints can reference other blueprints)
- Have access to a **subset of NornFlow variables** during expansion (*more about this later*)
- Are **expanded during workflow loading**, not during execution

**Comparison:**

| Aspect | Blueprint | Workflow | Task |
|--------|-----------|----------|------|
| **Purpose** | Reusable task collection | Complete automation definition | Single operation |
| **Structure** | A YAML/dict with a single `tasks` key | Full YAML/dict workflow definition with metadata | Python function with signature |
| **Usage** | Referenced in workflows | Executed directly | Referenced in workflows/blueprints |
| **Nesting** | Can reference other blueprints | Cannot be nested | N/A |
| **Variables** | Assembly-time subset | Full runtime access | Full runtime access |
| **When processed** | Workflow loading | N/A | Task execution |

## When to Use Blueprints

Blueprints are ideal for:

**Common task sequences:**
```yaml
# blueprints/pre_checks.yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show version"
  - name: netmiko_send_command
    args:
      command_string: "show interfaces status"
```

**Environment-specific configurations:**
```yaml
# workflows/deploy.yaml
workflow:
  name: "Deploy Configuration"
  tasks:
    - blueprint: pre_checks.yaml
    - name: apply_config
```

**Modular workflow construction:**
```yaml
# workflows/full_audit.yaml
workflow:
  name: "Complete Device Audit"
  tasks:
    - blueprint: hardware_checks.yaml
    - blueprint: software_checks.yaml
    - blueprint: security_checks.yaml
    - blueprint: compliance_checks.yaml
    - name: generate_report
```

## Creating Blueprints

### Blueprint Structure

A blueprint is a YAML file containing only a tasks list. It can be defined and follows the same rules of the tasks list in a regular workflow YAML/dict. 

This means you can use all available (catalogued) tasks, filters, hooks and jinja2 filters in a blueprint definition. 

```yaml
# blueprints/network_validation.yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show ip interface brief"
    set_to: interfaces
  
  - name: netmiko_send_command
    args:
      command_string: "show ip route summary"
    set_to: routes
  
  - name: echo
    args:
      msg: "Found {{ interfaces | length }} interfaces and {{ routes | length }} routes"
    if: "{{ 'interfaces' | is_set }}"
```

**Important:** Blueprints contain ONLY the tasks key. No `workflow`, `name`, `description`, etc.

### Blueprint Discovery

NornFlow automatically discovers blueprints from directories specified in your nornflow.yaml:

```yaml
# nornflow.yaml
local_blueprints:
  - "blueprints"
  - "shared/blueprints"
  - "/opt/company/common_blueprints"
```

**Discovery rules:**
- Search is **recursive** (includes subdirectories)
- All `.yaml` and `.yml` files are considered blueprints
- Both **relative** and **absolute** paths supported
- Relative paths resolve against the settings file directory

**Directory structure example:**
```
my_project/
├── nornflow.yaml
└── blueprints/
    ├── validation.yaml
    ├── backup/
    │   ├── full_backup.yaml
    │   └── config_only.yaml
    └── security/
        ├── compliance_checks.yaml
        └── vulnerability_scan.yaml
```

### Blueprint Catalog

All discovered blueprints are cataloged by filename (without extension):

```bash
# View discovered blueprints
nornflow show --blueprints
```

**Catalog naming:**
- `blueprints/validation.yaml` → `validation`
- `blueprints/backup/full_backup.yaml` → `full_backup`
- `blueprints/security/compliance_checks.yaml` → `compliance_checks`

**Name conflicts:** If multiple blueprints have the same filename, the last discovered one wins. Use unique names.

> **NOTE:** *We understand this is somehow restricting, but a decision was made to keep things simle here, as it shouldn't be too hard to prevent clashes by using different file names. Future releases of NornFlow, may revist this decision and allow blueprints to be ID in the catalogue with a fully qualified name.*

## Using Blueprints in Workflows

### Basic Blueprint Reference

Reference blueprints by name from the catalog:

```yaml
workflow:
  name: "Device Maintenance"
  tasks:
    - blueprint: validation.yaml
    - blueprint: backup.yaml
    - name: perform_maintenance
    - blueprint: validation.yaml
```
Notice the file extension is required, as blueprints are catalogued with their filenames. This means `my_blueprint.yml` and `my_blueprint.yaml` are two different blueprints, since they both use valid but different extensions.

**By path (relative or absolute):**

You can also reference blueprints (that are NOT in the catalog) by using file paths:

```yaml
workflow:
  name: "Big Workflow"
  tasks:
    # Relative path - resolved against current working directory
    - blueprint: ./external_blueprints/common_checks.yaml
    
    # Absolute path - used as-is
    - blueprint: /opt/shared/blueprints/corporate_standard.yaml
    
    - name: domain_specific_task
```

> ⚠️ **Important: Understanding Relative Path Resolution**
> 
> When using **relative paths** for blueprints (not catalog names), the path is resolved against the **current working directory** where the nornflow command is executed — NOT the workflow file location or the blueprint file location.
> 
> In practice, you **SHOULD** always run nornflow commands from your project root directory (where n`ornflow.yaml` is located), so relative paths effectively resolve from there.
> 
> **BEST PRACTICE:** For blueprints outside your configured `local_blueprints` directories, prefer **absolute paths** to avoid confusion about path resolution.

**Example with uncatalogued blueprints:**

Consider this project structure:

```
my_project/
├── nornflow.yaml              # local_blueprints: ["blueprints"]
├── blueprints/                # Catalogued blueprints
│   └── standard_checks.yaml
├── external_blueprints/       # NOT in local_blueprints (not catalogued)
│   ├── special_audit.yaml
│   └── vendor_specific.yaml
└── workflows/
    └── my_workflow.yaml
```

In `my_workflow.yaml`:

```yaml
workflow:
  name: "Mixed Blueprint Sources"
  tasks:
    # From catalog (discovered in blueprints/)
    - blueprint: standard_checks.yaml
    
    # NOT catalogued - must use path
    # This works IF you run 'nornflow run' from my_project/
    - blueprint: ./external_blueprints/special_audit.yaml
    
    # Absolute path - always works regardless of where command is run
    - blueprint: /home/user/my_project/external_blueprints/vendor_specific.yaml
```

**Within uncatalogued blueprints referencing other blueprints:**

When a blueprint references another blueprint using a relative path, that path is ALSO resolved against the current working directory:

```yaml
# external_blueprints/special_audit.yaml
tasks:
  - name: some_task
  
  # Relative path resolves from where 'nornflow' was run, NOT from this file's location
  - blueprint: external_blueprints/vendor_specific.yaml  # ✅ Works from project root
  
  # This would NOT work (resolves to ./vendor_specific.yaml from CWD)
  - blueprint: ./vendor_specific.yaml  # ❌ Won't find the file
  
  # Absolute paths always work
  - blueprint: /home/user/my_project/external_blueprints/vendor_specific.yaml  # ✅ Always works
```

### Conditional Blueprint Inclusion

Use the `if` condition to include blueprints conditionally:

```yaml
workflow:
  name: "Environment-Aware Deployment"
  vars:
    environment: "prod"
    enable_monitoring: true
  tasks:
    - blueprint: pre_deployment_checks.yaml
    
    - blueprint: prod_validation.yaml
      if: "{{ environment == 'prod' }}"
    
    - blueprint: dev_validation.yaml
      if: "{{ environment == 'dev' }}"
    
    - name: deploy_configuration
    
    - blueprint: monitoring_setup.yaml
      if: "{{ enable_monitoring }}"
```

**Important:** 
- The `if` condition is evaluated during assembly-time (workflow loading), not runtime. Only variables available at assembly-time can be used.
- The `if` field here is NOT an `if` hook, and is processed entirely differently. The key name is the same for consistency, but only direct boolean values or jinja templates are acceptable inputs (Nornir filters are not).

### Nested Blueprints

Blueprints can reference other blueprints:

```yaml
# blueprints/full_health_check.yaml
tasks:
  - blueprint: hardware_checks.yaml
  - blueprint: software_checks.yaml
  - blueprint: connectivity_checks.yaml
```

```yaml
# blueprints/hardware_checks.yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show environment"
  - name: netmiko_send_command
    args:
      command_string: "show inventory"
```

**Maximum nesting depth:** No enforced limit, but circular dependencies are detected and prevented.

### Dynamic Blueprint Selection

Use Jinja2 templates with **assembly-time variables** to dynamically select blueprints:

```yaml
workflow:
  name: "Platform-Specific Workflow"
  vars:
    platform: "ios"
    region: "us-east"
  tasks:
    - blueprint: "{{ platform }}_validation.yaml"
    - name: generic_task
    - blueprint: "{{ region }}_compliance.yaml"
```

The `platform` and `region` vars above could be passed through other forms too. More about it in the [Variable Resolution in Blueprints](#variable-resolution-in-blueprints) section.

## Variable Resolution in Blueprints

### Assembly-Time vs Runtime

Understanding when variables are resolved is crucial for working with blueprints.

**Assembly-Time (Workflow Loading):**
- Happens when `WorkflowModel.create()` is called
- Blueprint `if` conditions are evaluated
- Dynamic blueprint names are resolved
- Blueprint references are expanded into actual tasks

**Runtime (Task Execution):**
- Happens when `nornflow.run()` is called
- Tasks execute on target devices
- Task arguments are processed
- Runtime variables are created/updated

**Critical distinction:** Blueprint expansion happens BEFORE any actual workflow execution, so blueprints cannot access runtime variables.

### Variable Precedence for Blueprints

During assembly-time, blueprints have access to these variable sources (highest to lowest priority):

1. **CLI Variables** (`--vars` option)
2. **Workflow Variables** (vars in YAML/dict)
3. **Domain Variables** (`vars/{domain}/defaults.yaml` - *by default*)
4. **Global Variables** (defaults.yaml  - *by default*)
5. **Environment Variables** (`NORNFLOW_VAR_*`)

**NOT available at assembly-time:**
- Runtime variables (set by `set` task or `set_to` hook)
- Host inventory data (`host.*` namespace)

**Example:**

```yaml
# vars/defaults.yaml
backup_enabled: true
validation_level: "basic"

# workflows/maintenance/daily.yaml
workflow:
  name: "Daily Maintenance"
  vars:
    validation_level: "thorough"
  tasks:
    - blueprint: "validation_{{ validation_level }}.yaml"
      if: "{{ backup_enabled }}"
```

With CLI override:
```bash
nornflow run daily.yaml --vars "validation_level=minimal,backup_enabled=false"
```

Result: The blueprint name is resolved to `validation_minimal.yaml` (*validation_level=minimal*), and it is NOT expanded/included in the final workflow (*backup_enabled=false*)

### Using Variables in Blueprint References

Variables can be used in three places when working blueprints:

**1. Blueprint name/path:**
```yaml
tasks:
  - blueprint: "{{ platform }}_config.yaml"
  - blueprint: "../{{ region }}/standard_checks.yaml"
```

**2. Conditional inclusion:**
```yaml
tasks:
  - blueprint: security_scan.yaml
    if: "{{ security_enabled and environment == 'prod' }}"
```

**3. Within the blueprint itself:**
```yaml
# blueprints/backup.yaml
tasks:
  - name: write_file
    args:
      filename: "{{ backup_path }}/{{ host.name }}.cfg"
```

**Variable resolution timing:**
- Blueprint name/path: Resolved during assembly-time
- `if` condition: Resolved during assembly-time (ultimately must evaluate to `True`/`False`)
- Task arguments within blueprint: Resolved during runtime (just like all other directly included tasks in the workflow)

## Blueprint Composition Strategies

**Layered composition:**
```yaml
# blueprints/base_validation.yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show version"

# blueprints/extended_validation.yaml
tasks:
  - blueprint: base_validation.yaml
  - name: netmiko_send_command
    args:
      command_string: "show interfaces"
  - name: netmiko_send_command
    args:
      command_string: "show ip route"
```

**Conditional composition:**
```yaml
# blueprints/smart_deployment.yaml
tasks:
  - blueprint: pre_checks.yaml
  
  - blueprint: maintenance_mode.yaml
    if: "{{ requires_maintenance }}"
  
  - name: apply_configuration
  
  - blueprint: exit_maintenance_mode.yaml
    if: "{{ requires_maintenance }}"
  
  - blueprint: post_checks.yaml
```
Employing the `smart_deployment.yaml` blueprint example above requires a `requires_maintenance` var to exist in workflow assembly-time (*check [Variable Resolution in Blueprints](#variable-resolution-in-blueprints) again*).

**Platform-specific composition:**
```yaml
# workflows/universal_config.yaml
workflow:
  name: "Universal Configuration"
  vars:
    platform: "ios"
  tasks:
    - blueprint: "{{ platform }}_pre_config.yaml"
    - name: apply_base_config
    - blueprint: "{{ platform }}_post_config.yaml"
```

## Blueprint Nesting: Circular vs Repeated Use

Blueprints support arbitrary nesting depth with automatic circular dependency detection. Understanding the distinction between ***circular dependencies*** and ***repeated use*** is critical.

### Recursive Expansion

When blueprints are nested, NornFlow expands them recursively during workflow loading:

```
Workflow
  ├── Task A
  ├── Blueprint X (conditionally included based on {{ env }})
  │     ├── Task B
  │     ├── Blueprint Y (conditionally included)
  │     │     ├── Task C
  │     │     └── Task D
  │     └── Task E
  └── Task F

Expands to: Task A → Task B → Task C → Task D → Task E → Task F
(assuming all conditions evaluate to true)
```

### Circular Dependency (INVALID)

A **circular dependency** occurs when a blueprint appears within its own expansion chain, creating an infinite loop:

```yaml
# blueprints/a.yaml
tasks:
  - blueprint: b.yaml

# blueprints/b.yaml
tasks:
  - blueprint: c.yaml

# blueprints/c.yaml
tasks:
  - blueprint: a.yaml  # ERROR: Circular dependency!
```

**This will fail with:**
```
BlueprintCircularDependencyError: Circular dependency detected: a.yaml → b.yaml → c.yaml → a.yaml
```

NornFlow tracks the current expansion path and raises an error when it detects a blueprint that's already being expanded in the current chain.

### Repeated Sequential Use (VALID)

**Repeated use** means using the same blueprint multiple times at the same nesting level or in different branches. This is perfectly valid because each reference is expanded independently:

```yaml
# VALID: Same blueprint used multiple times sequentially
workflow:
  name: "Multi-Stage Validation"
  tasks:
    - blueprint: health_check.yaml    # Expands completely
    - name: configure_device
    - blueprint: health_check.yaml    # Valid: previous expansion finished
    - name: save_config
    - blueprint: health_check.yaml    # Valid: can repeat as needed
```

```yaml
# VALID: Same blueprint in different branches
workflow:
  name: "Environment-Aware Deployment"
  vars:
    environment: "prod"
  tasks:
    - blueprint: validation.yaml      # Pre-deployment validation
    - name: deploy_configuration
    - blueprint: validation.yaml      # Post-deployment validation
```

```yaml
# VALID: Same blueprint in nested structure (different paths)
# blueprints/comprehensive_check.yaml
tasks:
  - blueprint: base_check.yaml        # First expansion
  - name: intermediate_task
  - blueprint: base_check.yaml        # Valid: not in expansion chain

# blueprints/base_check.yaml
tasks:
  - name: netmiko_send_command
    args:
      command_string: "show version"
```

**Why this works:** NornFlow uses a stack-based approach. When a blueprint finishes expanding, it's removed from the expansion stack, allowing legitimate reuse. Only blueprints currently being expanded (on the stack) trigger circular dependency errors.

---

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./core_concepts.md">← Previous: Core Concepts</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./failure_strategies.md">Next: Failure Strategies →</a>
</td>
</tr>
</table>

</div>
