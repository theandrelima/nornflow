# NornFlow Variables System

## Table of Contents
- [Variable Resolution Architecture](#variable-resolution-architecture)
  - [1. Variable Sources and Precedence](#1-variable-sources-and-precedence-highest-to-lowest-priority)
  - [2. Per-Device Variable Context](#2-per-device-variable-context)
  - [3. The 'global' Namespace](#3-the-global-namespace)
  - [4. Case Sensitivity Rules](#4-case-sensitivity-rules)
- [Directory Structure Example](#directory-structure-example)
  - [Domain Resolution with Multiple Workflow Directories](#domain-resolution-with-multiple-workflow-directories)
  - [Special Cases](#special-cases)
  - [Example Multi-Directory Setup](#example-multi-directory-setup)
- [Configuration in nornflow.yaml](#configuration-in-nornflowyaml)
- [Example Workflow with Variables](#example-workflow-with-variables)
- [Variable File Contents Example](#variable-file-contents-example)
- [Resolution Process Example](#resolution-process-example)

## Variable Resolution Architecture

NornFlow implements a powerful variable management system with per-device isolation by default and an optional global sharing mechanism when needed.

### 1. Variable Sources and Precedence (Highest to Lowest Priority)

When resolving variables for each device's context, NornFlow combines variables from multiple sources following this precedence order:

1. **CLI Variables** (***CLI is King!*** 👑)
   - Variables passed through command line arguments with `--vars`

2. **Runtime Variables**
   - Set programmatically during workflow execution

3. **Inline Workflow Variables**
   - Defined directly in workflow YAML under the `vars:` section

4. **Paired Workflow Variables**
   - From a paired file in the same directory, with same name as the workflow but prepended with '_vars' (e.g., `deploy_vars.yaml`, for a workflow file named `deploy.yaml`)

5. **Domain-specific Default Variables**
   - Variables specific to a domain (determined by first directory after a workflow root)
   - Stored in `{vars_dir}/{domain}/defaults.yaml`
   - **Example:**
      - For a workflow at `workflows/security/compliance/audit.yaml`, domain is "security" (not "compliance")
      - Variables loaded from `vars/security/defaults.yaml` (regardless of nesting depth)

6. **Default Variables**
   - Shared across all workflows regardless of domain or location
   - Stored in `{vars_dir}/defaults.yaml`

7. **Nornir Inventory Variables**
   - From Nornir's inventory system (includes host and inherited group variables)

8. **Environment Variables** (lowest priority)
   - System environment variables with prefix `NORNFLOW_VAR_`
   - Example: `NORNFLOW_VAR_template_dir` would resolve as `{{ template_dir }}`

> **IMPORTANT NOTE**: In NornFlow, all variables are accessed directly using their name (e.g., `{{ hostname }}`, `{{ site_id }}`), regardless of their source. The system automatically searches all sources according to the precedence order above. Only the `global` namespace requires a prefix (e.g., `{{ global.variable_name }}`).

### 2. Per-Device Variable Context

NornFlow's Variables core design principle is device isolation:

- All variables from all sources are combined into a single unified context for each device
- Each device's context is completely isolated from other devices
- Changes to variables during task execution affect only the current device
- The precedence order above determines which value "wins" when the same variable name appears in multiple sources

### 3. The 'global' Namespace

In specific cases where you need to share data across all devices, NornFlow provides the `global` namespace:

- Variables accessed with the `global.` prefix are shared across all devices
- Example: `{{ global.counter }}` refers to a value that all devices can see and modify
- Changes to global namespace variables are visible to all devices immediately
- Use this namespace with caution, as it can lead to race conditions in parallel execution

> **IMPORTANT**: `global` is the **only** namespace in NornFlow. All other variables are accessed directly by their name without any prefix, regardless of their source.

### 4. Case Sensitivity Rules

Variables in NornFlow are **strictly case-sensitive**:

- A variable named `fictional_var` is completely different from `FICTIONAL_VAR`
- No automatic case conversion or matching is performed
- This applies to ALL variable sources, including environment variables

For environment variables, while the prefix `NORNFLOW_VAR_` must be uppercase, the remainder must exactly match the case used in templates:

```bash
# This environment variable:
NORNFLOW_VAR_fictional_var="some value"

# Will ONLY match this variable reference:
{{ fictional_var }}

# And NOT these:
{{ FICTIONAL_VAR }}
{{ Fictional_Var }}
```

## Directory Structure Example

NornFlow recommends organizing your project with a clear separation of workflows by domain. The structure below represents a recommended organization:

> **Note:** This example assumes the default configuration where `vars_dir="vars"` and `local_workflows_dirs=["workflows"]`. The paths would change accordingly if you customize these settings in your nornflow.yaml file.

```bash
project/
├── nornflow.yaml                  # Contains the `vars_dir` (defaults to "vars") and `local_workflows_dirs` (defaults to ["workflows"]) settings
├── workflows/                     # Default workflow directory 
│   ├── network_ops/               # Grouped workflows by domain 
│   │   ├── deploy.yaml            # Workflow with inline vars section
│   │   └── deploy_vars.yaml       # Paired variables file (lower precedence than inline vars)
│   └── security/                  # Another domain
│       └── audit.yaml             # Another workflow
├── vars/                          # Variables directory (vars_dir)
│   ├── defaults.yaml              # Default variables for all workflows
│   ├── network_ops/               # Domain-specific variables
│   │    └── defaults.yaml         # Variables for network_ops domain workflows
│   └── security/                  # Another domain's variables
│       └── defaults.yaml          # Variables for security domain workflows
└── nornir_configs/                # Nornir configuration files
```

When resolving variables, NornFlow will automatically load appropriate variables based on this directory structure. For example, when running a workflow at `workflows/network_ops/deploy.yaml`, NornFlow will load variables from `vars/network_ops/defaults.yaml`.

### Domain Resolution with Multiple Workflow Directories

NornFlow supports configuring multiple workflow directories via the `local_workflows_dirs` setting:

```yaml
local_workflows_dirs:
  - "workflows"
  - "custom/projects"
  - "/path/to/other/workflows"
```

When resolving domain-specific variables, NornFlow uses the following approach:

1. **Domain Resolution:** The domain is determined by the **first directory after a workflow root directory**.
2. **Variable Location:** Domain variables are always stored directly under `{vars_dir}/{domain}/defaults.yaml`

**Just to reemphasize:** Even for deeply nested workflow files, the domain is **always the first directory after the workflow root**. For example, based in the above samples configs for `local_workflows_dirs`:

```
workflows/security/compliance/pci.yaml → Domain is "security" (not "compliance")
custom/projects/network/datacenter/deploy.yaml → Domain is "network" (not "datacenter")
```

The domain-specific variables will be searched (respectively) for in:
```
vars/security/defaults.yaml
vars/network/defaults.yaml
```

#### Special Cases:

1. **Workflows directly in a root directory:**
   ```
   workflows/deploy.yaml → No domain (directly in workflow root)
   ```
   In this case, no domain-specific variables are loaded.

2. **Workflows not under any known workflow root:**
   ```
   some/random/path/workflow.yaml → No domain (not in a workflow root)
   ```
   No domain-specific variables are loaded.

#### Example Multi-Directory Setup

```bash
project/
├── workflows/                            # A workflow root 
│   ├── security/                         # workflows nested under this dir will be in Domain 'security'                       
│   │   ├── audit.yaml                    # Domain: "security"
│   │   └── compliance/pci.yaml           # Domain: "security"
│   └── network/                          # workflows nested under this dir will be in Domain 'network'
│       └── datacenter/core/deploy.yaml   # Domain: "network"
├── custom/projects/                      # Another workflow root
│   ├── security/                         # workflows nested under this dir will be in Domain 'security'
│   │   └── scan.yaml                     # Domain: "security"
│   └── cloud/                            # workflows nested under this dir will be in Domain 'cloud'
│       └── provision.yaml                # Domain: "cloud"
├── vars/
│   ├── defaults.yaml                     # Variables here apply to ALL workflows, everywhere, regardless of domain (if any)
│   ├── security/
│   │   └── defaults.yaml                 # Variables here apply to ALL workflows in domain 'security'
│   ├── network/
│   │   └── defaults.yaml                 # Variables here apply to ALL workflows in domain 'network'
│   └── cloud/
│       └── defaults.yaml                 # Variables for ALL workflows in domain 'cloud'
└── nornflow.yaml
```

To be clear, in this setup:

1. All workflows under both `workflows/security/` and `custom/projects/security/` share the same domain-specific variables from `vars/security/defaults.yaml`.
2. Nested directories like `workflows/security/compliance/` do not create separate domains.

## Configuration in nornflow.yaml

```yaml
# Variables directory setting (optional, defaults to "vars" if not set)
vars_dir: "vars"

# Workflow directories (optional, defaults to ["workflows"] if not set)
local_workflows_dirs:
  - "workflows"
  - "custom/projects"
```

## Example Workflow with Variables

Here's a complete example of a hypothetical `workflows/network_ops/deploy.yaml` workflow:

> **Note on Example Tasks**: These are hypothetical examples for illustration purposes only.

```yaml
workflow:
  name: Network Configuration Deployment
  description: "Deploys configuration to network devices"
  
  # Inline workflow variables (precedence #3)
  vars:
    template_dir: "/workflows/templates"  # This overrides any template_dir in deploy_vars.yaml
    timeout: 30
    backup_enabled: true
    config_sections:
      - interfaces
      - routing
      - acl
  
  # Inventory filters
  inventory_filters:
    platform: "ios"
    
  # Tasks with variable references
  tasks:
    - name: create_backup
      # Sets variables during workflow execution (device-specific)
      task: set
      args:
        backup_path: "/backups/{{ hostname }}/{{ '%Y%m%d' | strftime }}"
        
    - name: backup_config
      task: backup_device
      args:
        dest_dir: "{{ backup_path }}"  # Using device's variable 
        timeout: "{{ timeout }}"  # Using workflow variable through precedence
        
    - name: generate_config
      task: template_config
      args:
        template: "{{ template_dir }}/{{ hostname }}.j2"
        dest: "configs/{{ hostname }}.cfg"
        sections: "{{ config_sections }}"
        
    - name: deploy_config
      task: push_config
      args:
        config_file: "configs/{{ hostname }}.cfg"
        timeout: "{{ timeout }}"
        save_config: "{{ backup_enabled }}"
        
    - name: count_deployments
      # Increments a counter shared across all devices
      task: increment_counter
      args:
        counter_name: "{{ global.deployment_count }}"
        
    - name: verify_deployment
      task: run_commands
      args:
        commands: 
          - "show ip interface brief"
          - "show version"
        log_level: "{{ log_level | default('info') }}"
        output_dir: "{{ backup_dir | default('/tmp') }}"
```

## Variable File Contents Example

```yaml
# In deploy_vars.yaml (paired workflow file - precedence #4)
template_dir: "/opt/templates"  # Will be overridden by inline vars in deploy.yaml
additional_options:
  save_on_exit: true
  verify_config: true

# vars/network_ops/defaults.yaml (domain defaults - precedence #5)
ntp_servers:
  - 10.0.0.1
  - 10.0.0.2
timeout_default: 120  # Overrides global timeout_default
log_level: "debug"    # Domain-specific log level

# vars/defaults.yaml (defaults - precedence #6)
admin_email: admin@example.com
timeout_default: 60
log_level: "info"
```

## Resolution Process Example

Assume we have these variables defined:

```
# CLI: (precedence #1)
--vars "deploy_mode=test,debug=true,custom_var=cli_value"

# Runtime variables (precedence #2, set programmatically for device router1):
backup_path = "/backups/router1/20250415/"
custom_var = "runtime_value"  # Will be overridden by CLI

# workflows/network_ops/deploy.yaml: (inline workflow vars - precedence #3)
vars:
  template_dir: "/workflows/templates"
  timeout: 30
  backup_enabled: true

# workflows/network_ops/deploy_vars.yaml: (paired workflow vars - precedence #4)
template_dir: "/paired/templates"  # Overridden by inline vars above
additional_options:
  save_on_exit: true

# vars/network_ops/defaults.yaml: (domain defaults - precedence #5)
template_dir: "/network/templates"  # Lower precedence than both workflow var sources
log_level: "debug"

# vars/defaults.yaml: (defaults - precedence #6)
template_dir: "/default/templates"
log_level: "info"
debug: false

# Nornir inventory variables for host "router1": (precedence #7)
hostname = "router1"
site_id = "NYC01"

# Environment variables: (precedence #8)
NORNFLOW_VAR_backup_dir="/tmp/backups"
```

For a device named "router1", variables would resolve as:

- `{{ deploy_mode }}` → "test" (from CLI, precedence #1)
- `{{ debug }}` → true (from CLI, precedence #1, overriding defaults.yaml)
- `{{ custom_var }}` → "cli_value" (from CLI, precedence #1, overriding runtime)
- `{{ backup_path }}` → "/backups/router1/20250415/" (from runtime, precedence #2)
- `{{ template_dir }}` → "/workflows/templates" (from inline workflow vars, precedence #3, overriding paired vars)
- `{{ timeout }}` → 30 (from inline workflow vars, precedence #3)
- `{{ additional_options.save_on_exit }}` → true (from paired workflow vars, precedence #4)
- `{{ log_level }}` → "debug" (from domain defaults, precedence #5)
- `{{ hostname }}` → "router1" (from Nornir inventory, precedence #7)
- `{{ site_id }}` → "NYC01" (from Nornir inventory, precedence #7) 
- `{{ backup_dir }}` → "/tmp/backups" (from environment, precedence #8)

And for global variables:
- `{{ global.deployment_count }}` → A shared variable visible to all devices (from the global namespace)
