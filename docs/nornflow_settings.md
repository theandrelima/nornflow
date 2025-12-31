# NornFlow Settings

## Table of Contents
- [Finding the Settings File](#finding-the-settings-file)
- [Environment Variable Support](#environment-variable-support)
- [Mandatory Settings](#mandatory-settings)
  - [`nornir_config_file`](#nornir_config_file)
- [Optional Settings](#optional-settings)
  - [`local_tasks`](#local_tasks)
  - [`local_workflows`](#local_workflows)
  - [`local_filters`](#local_filters)
  - [`local_hooks`](#local_hooks)
  - [`local_blueprints`](#local_blueprints)
  - [`vars_dir`](#vars_dir)
  - [`dry_run`](#dry_run)
  - [`failure_strategy`](#failure_strategy)
  - [`processors`](#processors)
  - [`imported_packages`](#imported_packages)
- [NornFlow Settings vs Nornir Configs](#nornflow-settings-vs-nornir-configs)


NornFlow uses a settings file to configure different behaviors, including to specify where to find Nornir tasks and workflows. This settings file is typically named `nornflow.yaml` and is located in the root of your project. You can customize this file to fit your project's requirements.

## Finding the Settings File

NornFlow will try to find a settings YAML file in the following order:
1. The path specified in the environment variable `NORNFLOW_SETTINGS`.
2. The path passed to the `NornFlowSettings` initializer (through the CLI, it can be done using `nornflow --settings <PATH> ...` option).
3. The path `nornflow.yaml` in the root of the project.

## Environment Variable Support

All settings can be overridden using environment variables with the `NORNFLOW_SETTINGS_` prefix:

```bash
# Override nornir_config_file
export NORNFLOW_SETTINGS_NORNIR_CONFIG_FILE="configs/nornir-prod.yaml"

# Override failure strategy
export NORNFLOW_SETTINGS_FAILURE_STRATEGY="fail-fast"

# Override list values (JSON format)
export NORNFLOW_SETTINGS_LOCAL_TASKS='["tasks", "custom_tasks"]'

# Override dry run
export NORNFLOW_SETTINGS_DRY_RUN=true
```

**Settings Loading Priority (highest to lowest):**
1. Environment variables with `NORNFLOW_SETTINGS_` prefix
2. Values from settings YAML file
3. Default values defined in the NornFlowSettings class

> **Design Rationale**: NornFlow follows the [12-factor app](https://12factor.net/config) methodology where environment variables take precedence over configuration files for application settings. This allows for deployment-time configuration changes without modifying files, which is especially useful in containerized environments, CI/CD pipelines, and cloud deployments.

Additionally, for certain settings like `dry_run` and `failure_strategy`, there's a **runtime precedence** layer that sits above the settings loading priority:

**Runtime Precedence (for dry_run, failure_strategy, processors):**
1. CLI flags or NornFlow constructor parameters (highest - explicit runtime intent)
2. Workflow-level definitions in YAML (workflow-specific configuration)
3. Settings value (from the loading priority chain above)

This means even if you set `NORNFLOW_SETTINGS_FAILURE_STRATEGY="fail-fast"`, passing `--failure-strategy skip-failed` via CLI will override it, as the CLI represents the most explicit user intent at runtime.

## Mandatory Settings

### `nornir_config_file`

- **Description**: Path to Nornir's configuration file. This setting is **required** and must be provided.
- **Type**: `str`
- **Required**: **Yes** (mandatory field)
- **Path Resolution**: When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory. Direct instantiation leaves the path untouched, so it resolves relative to the runtime working directory. Absolute paths are used as-is.
- **Example**:
  ```yaml
  nornir_config_file: "nornir_configs/config.yaml"
  ```
- **Note**: Can be set via environment variable `NORNFLOW_SETTINGS_NORNIR_CONFIG_FILE`.

## Optional Settings

### `local_tasks`

- **Description**: List of paths to directories containing the Nornir tasks to be included in NornFlow's task catalog. The search is recursive, meaning that all subdirectories will be searched as well. Be careful with this. Both absolute and relative paths are supported.
- **Type**: list[str]
- **Default**: ["tasks"]
- **Path Resolution**: 
  - When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory
  - Direct instantiation leaves relative paths untouched, so they resolve against the runtime working directory
  - Absolute paths are used as-is
- **Example**:
  ```yaml
  local_tasks:
    - "tasks"                    # Relative to settings file
    - "/abs/path/to/tasks"       # Absolute path
    - "../shared_tasks"          # Relative to settings file
  ```
- **Environment Variable**: `NORNFLOW_SETTINGS_LOCAL_TASKS`

### `local_workflows`

- **Description**: List of paths to directories containing the Nornir workflows to be included in NornFlow's workflow catalog. The search is recursive, meaning that all subdirectories will be searched as well. Be aware that all files with a .yaml or .yml extension will be considered workflows. Both absolute and relative paths are supported.
- **Type**: list[str]
- **Default**: ["workflows"]
- **Path Resolution**: 
  - When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory
  - Direct instantiation leaves relative paths untouched, so they resolve against the runtime working directory
  - Absolute paths are used as-is
- **Example**:
  ```yaml
  local_workflows:
    - "workflows"
    - "/shared/workflows"
  ```
- **Environment Variable**: `NORNFLOW_SETTINGS_LOCAL_WORKFLOWS`

### `local_filters`

- **Description**: List of paths to directories containing custom filter functions to be included in NornFlow's filter catalog. These filter functions can be referenced by name in workflow YAML files to perform advanced inventory filtering. The search is recursive, meaning that all subdirectories will be searched as well. Both absolute and relative paths are supported.
- **Type**: list[str]
- **Default**: ["filters"]
- **Path Resolution**: 
  - When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory
  - Direct instantiation leaves relative paths untouched, so they resolve against the runtime working directory
  - Absolute paths are used as-is
- **Example**:
  ```yaml
  local_filters:
    - "filters"
    - "../custom_filters"
  ```
- **Environment Variable**: `NORNFLOW_SETTINGS_LOCAL_FILTERS`
- **Note**: For details on how these filters can be used in workflows, see the Inventory Filtering section in the Workflows documentation.

### `local_hooks`

- **Description**: List of paths to directories containing custom hook implementations to be included in NornFlow's hook registry. Hooks extend task behavior without modifying task code. The search is recursive, meaning that all subdirectories will be searched as well. Both absolute and relative paths are supported.
- **Type**: list[str]
- **Default**: ["hooks"]
- **Path Resolution**: 
  - When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory
  - Direct instantiation leaves relative paths untouched, so they resolve against the runtime working directory
  - Absolute paths are used as-is
- **Example**:
  ```yaml
  local_hooks:
    - "hooks"
    - "/shared/custom_hooks"
  ```
- **Environment Variable**: `NORNFLOW_SETTINGS_LOCAL_HOOKS`
- **Note**: For details on creating custom hooks, see the Hooks Guide documentation.

### `local_blueprints`

- **Description**: List of paths to directories containing blueprint definitions. The search is recursive, meaning all subdirectories will be searched. All files with `.yaml` or `.yml` extensions are considered blueprints. Both absolute and relative paths are supported.
- **Type**: list[str]
- **Default**: ["blueprints"]
- **Path Resolution**: 
  - When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory
  - Direct instantiation leaves relative paths untouched, so they resolve against the runtime working directory
  - Absolute paths are used as-is
- **Example**:
  ```yaml
  local_blueprints:
    - "blueprints"
    - "../shared_blueprints"
    - "/opt/company/blueprints"
  ```
- **Environment Variable**: `NORNFLOW_SETTINGS_LOCAL_BLUEPRINTS`
- **Note**: Blueprints are expanded during workflow loading (assembly-time) and have access to a subset of the variable system. See the Blueprints Guide for details.

### `vars_dir`

- **Description**: Path to the directory containing variable files for NornFlow's variable system. This directory will store global variables (`defaults.yaml`) and domain-specific variables. Both absolute and relative paths are supported.
- **Type**: `str`
- **Default**: "vars"
- **Path Resolution**: 
  - When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory
  - Direct instantiation leaves relative paths untouched, so they resolve against the runtime working directory
  - Absolute paths are used as-is
- **Example**:
  ```yaml
  vars_dir: "vars"
  # Or with absolute path:
  vars_dir: "/shared/variables"
  ```
- **Note**: For details on how variables are loaded and their precedence, see the Variables Basics documentation.

### `dry_run`

- **Description**: If set to True, NornFlow will invoke Nornir in dry-run mode. This setting can be overridden at multiple levels during runtime.
- **Type**: `bool`
- **Default**: `False`
- **Runtime Precedence** (highest to lowest):
  1. CLI `--dry-run` flag or NornFlow constructor `dry_run` parameter
  2. Workflow-level `dry_run` setting in workflow YAML
  3. This settings value (which itself follows: env var > YAML file > default)
- **Example**:
  ```yaml
  dry_run: True
  ```
- **Note**: The runtime precedence means that even if you set `NORNFLOW_SETTINGS_DRY_RUN=true`, passing `--dry-run false` via CLI will override it.

### `failure_strategy`

- **Description**: Sets NornFlow's behavior when a task fails for a host during the execution of workflows. This setting controls whether NornFlow will skip failed hosts from subsequent tasks, stop execution as soon as possible, or continue running all tasks regardless of failures.
- **Type**: `str` (one of: "skip-failed", "fail-fast", "run-all")
- **Default**: "skip-failed"
- **Runtime Precedence** (highest to lowest):
  1. CLI `--failure-strategy` flag or NornFlow constructor `failure_strategy` parameter
  2. Workflow-level `failure_strategy` setting in workflow YAML
  3. This settings value (which itself follows: env var > YAML file > default)
- **Example**:
  ```yaml
  failure_strategy: "fail-fast"
  ```
- **Note**: For details on how failure strategies work, see the Failure Strategies documentation.

### `processors`
- **Description**: List of Nornir processor configurations to be applied during task/workflow execution. If not provided, NornFlow will default to using only its default processor: `nornflow.builtins.DefaultNornFlowProcessor`.
- **Type**: `list[dict]`
- **Default**: Uses `DefaultNornFlowProcessor` if not specified
- **Example**:
  ```yaml
  processors:
    - class: "nornflow.builtins.DefaultNornFlowProcessor"
    - class: "my_custom_package.MyCustomProcessor"
      args:
        verbosity: 2
  ```
- **Note**: Each processor configuration requires:
  - `class`: Full Python import path to the processor class
  - `args` (optional): Dictionary of arguments to pass to the processor's `__init__` method
  
  **Runtime Precedence** (highest to lowest):
  1. Processors passed directly to NornFlow constructor
  2. Processors defined in workflow YAML
  3. Processors defined in this settings file
  4. `DefaultNornFlowProcessor` (if no other processors specified)

---
> 🚨 ***NOTE: `imported_packages` is planned, but not yet supported and right now has no effect at all.***
### *`imported_packages`*

- ***Description**: List of Python packages installed in your environment that contain Nornir tasks and filter functions to be included in NornFlow's catalogs.*
- ***Type**: `list[str]`*
- ***Default***: `[]`
- ***Example***:
  ```yaml
  imported_packages:
    - "nornir_napalm"
    - "nornir_netmiko"
  ```
---
<br><br>

## NornFlow Settings vs Nornir Configs

NornFlow is designed to work with Nornir seamlessly. For that reason, NornFlow maintains its settings in a completely separate file.  
 
The decision to keep NornFlow settings and Nornir configurations in separate files is intentional and serves several purposes:

1. **Clarity and Focus**: By separating them, each file can focus on its specific purpose.

2. **Modularity**: Users can update or change the settings for NornFlow without affecting the Nornir configurations and vice versa. This modularity makes it easier to manage and maintain the files.

3. **Flexibility**: The separation provides flexibility in managing different environments and use cases. For example, you can have different NornFlow settings for different projects while reusing the same Nornir configurations across multiple projects.

In fact, even the choice of words here is purposeful: you may have noticed that throughout this documentation (and the code itself), the term "settings" is employed when referring to NornFlow, while "configs" is used in the context of Nornir. This distinction is intentional to emphasize the separation between the two applications - *even though grammatically these words could be used interchangeably*.


<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./hooks_guide.md">← Previous: Hooks Guide</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./jinja2_filters.md">Next: Jinja2 Filters Reference →</a>
</td>
</tr>
</table>

</div>
