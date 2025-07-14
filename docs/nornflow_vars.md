# NornFlow Variables System

## Table of Contents
- [Variable Namespaces](#variable-namespaces)
- [The `default` Namespace - NornFlow Variables](#the-default-namespace---nornflow-variables)
  - [Variable Sources and Precedence](#variable-sources-and-precedence)
  - [What is a Domain?](#what-is-a-domain)
  - [Per-Device Variable Context](#per-device-variable-context)
  - [The `vars_dir` Setting](#the-vars_dir-setting)
- [The `host` Namespace - Nornir Inventory Variables](#the-host-namespace---nornir-inventory-variables)
  - [Nornir Inventory Variable Access](#nornir-inventory-variable-access)
  - [Host Variable Resolution Order](#host-variable-resolution-order)
- [Setting Variables During Workflow Execution (Runtime NornFlow Variables)](#setting-variables-during-workflow-execution-runtime-nornflow-variables)
  - [Using the built-in `set` task](#using-the-built-in-set-task)
  - [Advanced Operations with `set` and Jinja2](#advanced-operations-with-set-and-jinja2)
  - [Capturing Task Outputs Directly into Variables](#capturing-task-outputs-directly-into-variables)
- [CLI Variables and Late Binding](#cli-variables-and-late-binding)
- [Directory Structure Example](#directory-structure-example)
  - [Domain Resolution with Multiple Workflow Directories](#domain-resolution-with-multiple-workflow-directories)
  - [Special Cases for Domain Resolution](#special-cases-for-domain-resolution)
  - [Example Multi-Directory Setup](#example-multi-directory-setup)
- [Example Workflow with Variables](#example-workflow-with-variables)
- [Variable File Contents Example](#variable-file-contents-example)
- [Resolution Process Example](#resolution-process-example)
- [Advanced Topics](#advanced-topics)
  - [Case Sensitivity](#case-sensitivity)
  - [Nested Variable Access](#nested-variable-access)
- [Navigation](#navigation)

## Variable Namespaces

NornFlow implements a flexible variable management system that separates variables into two distinct namespaces. This separation allows for powerful and dynamic workflow configurations while maintaining clear boundaries between different types of data.

NornFlow provides two types of variables:

1. **NornFlow Variables (Default Namespace)** - Your workflow's dynamic data
2. **Host Namespace (`host.`)** - Read-only access to Nornir inventory data

Let's explore each namespace in detail.

## The `default` Namespace - NornFlow Variables

NornFlow Variables are accessed directly by name without any prefix:

```jinja2
{{ variable_name }}
{{ backup_filename }}
{{ operation_timeout }}
```

These variables form the primary way to manage dynamic data within your workflows. They are device-specific, meaning each device maintains its own isolated set of these variables during workflow execution.

> **BEST PRACTICE**: Avoid creating NornFlow variables with names that begin with `host`, as this may cause confusion with the `host.` namespace prefix. For example, instead of `hostname`, consider using `device_name` or `system_hostname`.

### Variable Sources and Precedence

NornFlow combines variables from multiple sources to create each device's variable context. When multiple sources define the same variable name, NornFlow uses a clear precedence order (highest to lowest priority):

1. **Runtime Variables** (highest priority)
   - Variables set during workflow execution using the built-in `set` task
   - Example: `backup_filename: "{{ host.name }}_backup.cfg"`
   - These provide the highest level of control, allowing workflows to adapt based on discovered conditions
   - OBS: Notice that in this example we are accessing a variable in the `host` namespace (Nornir inventory) to define a variable in the `default` (NornFlow) namespace. This is perfectly fine.

2. **CLI Variables**
   - Variables passed via `--vars` command-line option
   - Example: `nornflow run workflow.yaml --vars "env=prod,region=us-west"`
   - Useful for ad-hoc parameter changes or CI/CD pipeline parameters

3. **Inline Workflow Variables**
   - Variables defined inside the workflow's YAML file under `vars:` key.
   - These are specific to the workflow in which they are defined

4. **Domain-specific Default Variables**
   - Variables that apply to all workflows within a specific "domain" *(formally defined in the next section)*
   - Example: In `workflows/network_provisioning/setup.yaml`, the domain is "network_provisioning"
   - **Must be stored in `{vars_dir}/{domain_name}/defaults.yaml`** - this is the only file NornFlow will check for domain-specific variables

5. **Default Variables**
   - Global variables that apply to all workflows
   - **Must be stored in `{vars_dir}/defaults.yaml`** - this is the only file NornFlow will check for global default variables

6. **Environment Variables** (lowest priority)
   - System environment variables prefixed with `NORNFLOW_VAR_`
   - Example: `NORNFLOW_VAR_api_key` becomes available as `{{ api_key }}`

This hierarchy provides flexibility while keeping things simple (KISS) and predictable.

### What is a Domain?

In NornFlow's variables system, a **domain** is determined by your workflow's location within the project structure:

- **Domain = First-level subdirectory name** under any configured workflow root directory
- **Example**: For workflow `workflows/network_provisioning/site_setup.yaml`
  - Workflow root: `workflows/` (configured in `local_workflows_dirs`)
  - Domain: `network_provisioning`
  - Domain variables loaded from: `vars/network_provisioning/defaults.yaml`

**Special Cases:**
- Workflows directly in a root directory (e.g., `workflows/utility.yaml`) have **no domain**
- Workflows outside configured roots have **no domain**
- Only workflows with a domain load domain-specific variables
- Domain variables **must** be in a file named `defaults.yaml` within the domain subdirectory

**Multiple Workflow Roots:**  
If you configure multiple workflow directories, the domain is still determined by the first-level subdirectory under whichever root contains your workflow:

```yaml
# nornflow.yaml
local_workflows_dirs:
  - "core_workflows"
  - "customer_projects/flows"
```

- `core_workflows/networking/setup.yaml` → Domain: "networking"
- `customer_projects/flows/security/audit.yaml` → Domain: "security"
- `customer_projects/flows/networking/custom_setup.yaml` → Domain: "networking" (yes, the same "networking" domain as above)

**Important**: When the same domain name exists across multiple workflow roots (like "networking" in the example above), **all workflows with that domain name share the same domain-specific variables** from `vars/networking/defaults.yaml`. NornFlow doesn't distinguish between domains based on which workflow root they're in - only the domain name matters for variable resolution.

### Per-Device Variable Context

Each device processed by a workflow maintains its own independent variable context:

- Variables set for one device don't affect other devices
- Parallel execution is safe and predictable
- You can reason about variable states without worrying about cross-device interference

### The `vars_dir` Setting

The `vars_dir` setting in your `nornflow.yaml` file specifies where NornFlow looks for variable files:

```yaml
# In nornflow.yaml
vars_dir: "vars"  # Default value
```

This creates the structure:
- `{vars_dir}/defaults.yaml` - Global default variables
- `{vars_dir}/{domain_name}/defaults.yaml` - Domain-specific variables

## The `host` Namespace - Nornir Inventory Variables

The `host` namespace provides read-only access to Nornir inventory data for the current device:

```jinja2
{{ host.name }}           # Device name
{{ host.platform }}       # Device platform  
{{ host.data.site_id }}   # Custom inventory data
```

This namespace is distinct from NornFlow variables. Essentially, it's a read-only proxy to Nornir's own Inventory data, with its well established rules.

### Nornir Inventory Variable Access

Access any Nornir inventory data using the `host.` prefix:

```jinja2
# Core host attributes
{{ host.name }}
{{ host.hostname }}
{{ host.platform }}

# Custom data from inventory
{{ host.data.site_code }}
{{ host.data.management_vlan }}

# Nested inventory data
{{ host.data.interfaces.eth0.ip_address }}
```

### Host Variable Resolution Order

When accessing `host.` variables, Nornir resolves them in this order:

1. **Direct Host Attributes** - Core Nornir `Host` object properties
2. **Host-Specific Data** - Custom variables for this specific host
3. **Group-Inherited Data** - Variables inherited from host groups
4. **Inventory Defaults** - Default variables defined at the inventory level

## Setting Variables During Workflow Execution (Runtime NornFlow Variables)

Use the built-in `set` task to create or modify NornFlow variables during workflow execution.

### Using the built-in `set` task

A task defined with `name: set` prompts NornFlow to call its builtin `set` task, which accepts one or more *'k:v'* pairs as `args`. For each, it will create (or edit, if it already exists) a NornFlow runtime variable with name 'k' and value 'v'. Notice that this behavior will override the value of an existing variable with name 'k'. 

```yaml
- name: set
  args:
    backup_filename: "{{ host.name }}_backup.cfg"
    is_configuration_applied: true
    current_retry_count: 0
    interface_description: "Configured interface: {{ previous_task_result.interface_name }}"
```
The example above acts on 4 variables at once. These variables:
- Take highest precedence (Runtime)
- Override any variables from CLI, workflow, domain, or global sources
- Are isolated on a per-device basis.

> **IMPORTANT**: The `set` task only affects NornFlow variables (default namespace) for the current device. It cannot modify Nornir inventory variables (`host.` namespace).

### Advanced Operations with `set` and Jinja2

Use Jinja2's capabilities for dynamic variable manipulation:

**Conditional Initialization and Counters:**
```yaml
- name: set
  args:
    # Initialize if undefined, then increment
    attempt_count: "{{ attempt_count | default(0) | int + 1 }}"
    
    # Conditional status messages
    status_message: "{{ 'Error: ' + last_error_code if last_error_code is defined else 'Success' }}"
    
    # Ensure list exists
    processed_interfaces: "{{ processed_interfaces | default([]) }}"
```

**List and Dictionary Operations:**
```yaml
- name: set
  args:
    # Append to lists
    collected_vlans: "{{ collected_vlans | default([]) + [10, 20, host.data.management_vlan] }}"
    
    # Create dictionaries
    device_settings: "{{ {'name': host.name, 'location': host.data.location, 'contact': admin_email} }}"
```

### Capturing Task Outputs Directly into Variables

Use `set_to` to capture task results directly into variables:

```yaml
- name: napalm_get
  args:
    getters: ["interfaces_ip"]
  set_to: interface_ip_data  # Store the complete result here
```

> **IMPORTANT**: The `set_to` keyword is **not supported** for NornFlow's built-in `echo` and `set` tasks (makes sense, right?). Use it only with Nornir tasks that produce meaningful result objects.

## CLI Variables and Late Binding

CLI variables provide pre-runtime parameterization from the command line:

```bash
nornflow run my_workflow.yaml --vars="region=us-east,environment=prod,debug_level=2"
```

These variables:
- Have precedence #2 (override most sources except runtime variables)
- Are available to all tasks in the workflow
- Allow flexible parameterization without modifying workflow files

```yaml
- name: echo
  args:
    msg: "Working on region: {{ region }} in {{ environment }} environment"
```

## Directory Structure Example

Organize your project with clear separation of variable files:

```
project_root/
├── nornflow.yaml
├── workflows/
│   ├── network_provisioning/      # Domain: "network_provisioning"
│   │   └── new_site_setup.yaml
│   └── security_audits/           # Domain: "security_audits"
│       └── compliance_check.yaml
├── vars/
│   ├── defaults.yaml              # Global variables (precedence #5)
│   ├── network_provisioning/
│   │   └── defaults.yaml          # Domain variables (precedence #4)
│   └── security_audits/
│       └── defaults.yaml
└── tasks/
    └── ...
```

### Example Multi-Directory Setup

```
my_project/
├── base_flows/                    # Workflow root
│   ├── branch_offices/            # Domain: "branch_offices"
│   │   └── configure_router.yaml
│   └── utility_tasks.yaml         # No domain
└── global_vars/
    ├── defaults.yaml              # Global defaults
    └── branch_offices/
        └── defaults.yaml          # Domain defaults
```

## Example Workflow with Variables

```yaml
workflow:
  name: New Site Setup
  description: "Provisions network devices for a new site"
  
  # Inline Workflow Variables (precedence #3)
  vars:
    operation_timeout: 600
    enable_backup_post_provision: true
    standard_services: [ntp, dns, syslog]
  
  inventory_filters:
    new_site_tag: "{{ cli_site_tag | default('PENDING_PROVISION') }}"

  tasks:
    - name: set
      args:
        provision_start: true
        device_identifier: "{{ host.name }}_{{ host.platform }}"
        
    - name: my_custom_template_task
      args:
        target_hostname: "{{ host.name }}"
        site_code: "{{ host.data.site_code }}"
        services_to_enable: "{{ standard_services }}"
      set_to: generated_config_result

    - name: set
      args:
        completed_steps: "{{ completed_steps | default([]) + ['config_generated'] }}"
        action_attempts: "{{ action_attempts | default(0) | int + 1 }}"

      (...)
```

## Variable File Contents Example

**`vars/defaults.yaml` (Global Variables):**
```yaml
global_admin_contact: "netops-alerts@example.com"
default_snmp_community: "public_readonly"
default_operation_timeout: 300
```

**`vars/network_provisioning/defaults.yaml` (Domain Variables):**
```yaml
operation_timeout: 900  # Overrides global default
provisioning_vlans:
  data: 100
  voice: 110
  guest: 120
```

## Resolution Process Example

For device `edge-router-01` in the `network_provisioning` domain:

**Variable Sources:**
1. **Runtime**: `provision_start: true`, `action_attempts: 1`
2. **CLI**: `debug_level=5`, `operation_timeout=1200`  
3. **Inline**: `enable_backup_post_provision: true`
4. **Domain**: `provisioning_vlans: {data: 100, voice: 110}`
5. **Global**: `global_admin_contact: "netops-alerts@example.com"`
6. **Environment**: `api_token: "abcdef12345"`

**Final Resolution:**
- `{{ operation_timeout }}` → `1200` (CLI overrides domain and global)
- `{{ provision_start }}` → `true` (Runtime, highest precedence)
- `{{ global_admin_contact }}` → `"netops-alerts@example.com"` (Global, not overridden)

**Host Variables:**
- `{{ host.name }}` → `"edge-router-01"`
- `{{ host.data.site_code }}` → `"NYC01"`

## Advanced Topics

### Case Sensitivity

All variable names in NornFlow are **strictly case-sensitive**:

- `myVar` is different from `MYVAR`
- Environment variables: `NORNFLOW_VAR_api_key` becomes `{{ api_key }}` (exact case match required)
- This applies to all variable sources and namespaces

### Nested Variable Access

NornFlow supports nested variable access using standard Jinja2 patterns:

**Dot Notation:**
```jinja2
{{ my_dict.key.subkey }}
{{ host.data.site_id }}
```

**Bracket Notation:**
```jinja2
{{ my_dict['key']['subkey'] }}
{{ host.data['site_id'] }}
```

**How it Works:**
- **Default namespace**: Nested access works through Jinja2's native dictionary handling when your variables contain nested structures
- **Host namespace**: Nested access is handled by Nornir's `Host` object, providing access to both direct attributes and the nested `host.data` dictionary

**Example with nested data:**
```yaml
# In vars/defaults.yaml
database_config:
  host: "db.example.com"
  credentials:
    username: "admin"
    password: "secret"
```

```jinja2
# In templates
{{ database_config.host }}                    # "db.example.com"
{{ database_config.credentials.username }}    # "admin"
{{ database_config['credentials']['password'] }} # "secret"
```
## Navigation

<div align="center">
  
<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./how_to_write_workflows.md">← Previous: Writing Workflows</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
</td>
</tr>
</table>

</div>