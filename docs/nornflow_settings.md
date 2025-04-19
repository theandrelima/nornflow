# NornFlow Settings

## Table of Contents
- [Finding the Settings File](#finding-the-settings-file)
- [Mandatory Settings](#mandatory-settings)
  - [`nornir_config_file`](#nornir_config_file)
- [Optional Settings](#optional-settings)
  - [`local_tasks_dirs`](#local_tasks_dirs)
  - [`local_workflows_dirs`](#local_workflows_dirs)
  - [`local_filters_dirs`](#local_filters_dirs)
  - [`dry_run`](#dry_run)
  - [`processors`](#processors)
  - [`imported_packages`](#imported_packages)
- [NornFlow Settings vs Nornir Configs](#nornflow-settings-vs-nornir-configs)


NornFlow uses a settings file to configure different behaviors, including to specify where to find Nornir tasks and workflows. This settings file is typically named `nornflow.yaml` and is located in the root of your project. You can customize this file to fit your project's requirements.

## Finding the Settings File

NornFlow will try to find a settings YAML file in the following order:
1. The path specified in the environment variable `NORNFLOW_SETTINGS`.
2. The path passed to the `NornFlowSettings` initializer (through the CLI, it can be done using `nornflow --settings <PATH> ...` option).
3. The path `nornflow.yaml` in the root of the project.

## Mandatory Settings

### `nornir_config_file`

- **Description**: Path to Nornir's configuration file.
- **Type**: `str`
- **Example**:
  ```yaml
  nornir_config_file: "nornir_configs/config.yaml"
  ```

## Optional Settings

### `local_tasks_dirs`

- **Description**: List of paths to directories containing the Nornir tasks to be included in NornFlow's task catalog. The search is recursive, meaning that all subdirectories will be searched as well. Be careful with this.
- **Type**: list[str]
- **Default**: ["tasks"]
- **Example**:
  ```yaml
  local_tasks_dirs:
    - "tasks" 
    - "/home/myself/other_tasks"
  ```

### `local_workflows_dirs`

- **Description**: List of paths to directories containing the Nornir workflows to be included in NornFlow's workflow catalog. The search is recursive, meaning that all subdirectories will be searched as well. Be aware that all files with a .yaml or .yml extension will be considered workflows.
- **Type**: list[str]
- **Default**: ["workflows"]
- **Example**:
  ```yaml
  local_workflows_dirs:
    - "workflows"
    - "../automation/nornflow_worflows"
  ```

### `local_filters_dirs`

- **Description**: List of paths to directories containing custom filter functions to be included in NornFlow's filter catalog. These filter functions can be referenced by name in workflow YAML files to perform advanced inventory filtering. The search is recursive, meaning that all subdirectories will be searched as well.
- **Type**: list[str]
- **Default**: ["filters"]
- **Example**:
  ```yaml
  local_filters_dirs:
    - "filters"
    - "../custom_filters"
  ```
- **Note**: For details on how these filters can be used in workflows, see the [Inventory Filtering](./how_to_write_workflows.md#inventory-filtering) section in the Workflows documentation.

### `dry_run`

- **Description**: If set to True, NornFlow will invoke Nornir in dry-run mode.
- **Type**: `bool`
- **Default**: `False`
- **Example**:
  ```yaml
  dry_run: True
  ```  

### `processors`
- **Description**: List of Nornir processor configurations to be applied during task/workflow execution. If not provided, NornFlow will default to using only its default processor: `nornflow.builtins.processors.DefaultNornFlowProcessor`.
- **Type**: `list[dict]`
- **Default**: Uses `DefaultNornFlowProcessor` if not specified
- **Example**:
  ```yaml
  processors:
    - class: "nornflow.builtins.processors.DefaultNornFlowProcessor"
      args: {} # included for completeness. If empty, it can be simply omitted. 
    - class: "mypackage.mymodule.MyCustomProcessor" 
      args:
        verbose: true
        log_level: "INFO"
  ```
- **Note**: Each processor configuration requires:
  - `class`: Full Python import path to the processor class
  - `args`: Optional dictionary of keyword arguments passed to the processor constructor

  **IMPORTANT**: If you specify custom processors, the `DefaultNornFlowProcessor` **WILL NOT** be automatically included. You must explicitly add it if you still want its functionality.
  
  Workflows can define their own processors section in their YAML files, with the same structure. Processor precedence follows this order:
  1. CLI arguments (via `--processors`/`-p` option)
  2. Workflow-specific processors (defined in the YAML file)
  3. Global processors setting (defined in the settings YAML file - defaults to `nornflow.yaml` in the root of the project directory)
  4. `DefaultNornFlowProcessor` (if no other processors specified)

---
> 🚨 ***NOTE: `imported_packages` is planned, but not yet supported and right now has no effect at all.***
### *`imported_packages`*

- ***Description**: List of Python packages installed in your environment that contain Nornir tasks and filter functions to be included in NornFlow's catalogs.*
- ***Type**: `list[str]`*
- ***Default**: `[]`*
- ***Example**:*
  ```yaml
  imported_packages: []
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
<a href="./getting_started.md">← Previous: Getting Started</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./nornflow_and_workflows.md">Next: NornFlow & Workflows →</a>
</td>
</tr>
</table>

</div>
