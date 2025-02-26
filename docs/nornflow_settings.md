# NornFlow Settings

Table of Contents
- [Finding the Settings File](#finding-the-settings-file)
- [Mandatory Settings](#mandatory-settings)
  - [`nornir_config_file`](#nornir_config_file)
- [Optional Settings](#optional-settings)
  - [`local_tasks_dirs`](#local_tasks_dirs)
  - [`local_workflows_dirs`](#local_workflows_dirs)
  - [`dry_run`](#dry_run)
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

### `dry_run`

- **Description**: If set to True, NornFlow will invoke Nornir in dry-run mode.
- **Type**: `bool`
- **Default**: `False`
- **Example**:
  ```yaml
  dry_run: True
  ```  
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

<table width="100%">
<tr>
<td width="33%" align="left">
<a href="./getting_started.md">← Previous: Getting Started</a>
</td>
<td width="33%" align="center">
</td>
<td width="33%" align="right">
<a href="./nornflow_and_workflows.md">Next: NornFlow & Workflows →</a>
</td>
</tr>
</table>

</div>