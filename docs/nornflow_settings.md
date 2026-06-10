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
  - [`local_j2_filters`](#local_j2_filters)
  - [`vars_dir`](#vars_dir)
  - [`dry_run`](#dry_run)
  - [`failure_strategy`](#failure_strategy)
  - [`processors`](#processors)
  - [`logger`](#logger)
  - [`redaction`](#redaction)
  - [`packages`](#packages)
- [NornFlow Settings vs Nornir Configs](#nornflow-settings-vs-nornir-configs)


NornFlow uses a settings file to configure different behaviors, including to specify where to find Nornir tasks and workflows. This settings file is typically named `nornflow.yaml` and is located in the root of your project. You can customize this file to fit your project's requirements.

## Finding the Settings File

NornFlow will try to find a settings YAML file in the following order:

1. The path specified in the environment variable `NORNFLOW_SETTINGS`.
2. The path passed to the `NornFlowSettings` initializer (through the CLI, it can be done using `nornflow --settings <PATH> ...` option).
3. The path `nornflow.yaml` in the root of the project.

## Environment Variable Support

Most settings can be overridden using environment variables with the `NORNFLOW_SETTINGS_` prefix. The **`packages`** setting is an exception: it cannot be overridden via environment variables and must be set in the settings YAML file (see [`packages`](#packages)).

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
1. Programmatic overrides (passed directly to `NornFlowSettings.load()` as `**overrides`)
2. Values from settings YAML file
3. Environment variables with `NORNFLOW_SETTINGS_` prefix
4. Default values defined in the NornFlowSettings class

> **Design Rationale**: NornFlow uses `NornFlowSettings.load()` as the standard entry point, which reads the YAML file and passes its contents (merged with any programmatic overrides) as init kwargs to the Pydantic model. Because init kwargs take precedence over environment variables in pydantic-settings, YAML values effectively override environment variables. Environment variables serve as a fallback for fields not present in the YAML file, which is useful in containerized environments, CI/CD pipelines, and cloud deployments where you want to provide defaults without modifying files.

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

- **Description**: List of paths to directories containing the Nornir tasks to be included in NornFlow's task catalog. The search is recursive, meaning that all subdirectories will be searched as well. Both absolute and relative paths are supported.
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
- **Important**: If you plan to delete any of the automatically created directories (from `nornflow init`) without creating or pointing to your own alternative source directories for this setting, you must set `local_tasks` to an empty list (`[]`) in `nornflow.yaml`. Otherwise, NornFlow will raise ResourceError exceptions during initialization and break.

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
- **Important**: If you plan to delete any of the automatically created directories (from `nornflow init`) without creating or pointing to your own alternative source directories for this setting, you must set `local_workflows` to an empty list (`[]`) in `nornflow.yaml`. Otherwise, NornFlow will raise ResourceError exceptions during initialization and break.

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
- **Important**: If you plan to delete any of the automatically created directories (from `nornflow init`) without creating or pointing to your own alternative source directories for this setting, you must set `local_filters` to an empty list (`[]`) in `nornflow.yaml`. Otherwise, NornFlow will raise ResourceError exceptions during initialization and break.

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
- **Important**: If you plan to delete any of the automatically created directories (from `nornflow init`) without creating or pointing to your own alternative source directories for this setting, you must set `local_hooks` to an empty list (`[]`) in `nornflow.yaml`. Otherwise, NornFlow will raise ResourceError exceptions during initialization and break.
- **Deep Dive**: [Hooks Guide](./hooks_guide.md)

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
- **Important**: If you plan to delete any of the automatically created directories (from `nornflow init`) without creating or pointing to your own alternative source directories for this setting, you must set `local_blueprints` to an empty list (`[]`) in `nornflow.yaml`. Otherwise, NornFlow will raise ResourceError exceptions during initialization and break.
- **Deep Dive**: [Blueprints Guide](./blueprints_guide.md)

### `local_j2_filters`

- **Description**: List of paths to directories containing custom Jinja2 filter functions. These filters extend the built-in Jinja2 filters available in NornFlow templates and can be used throughout workflows, blueprints, and task arguments. The search is recursive, meaning all subdirectories will be searched. All callable functions in Python files are registered as filters. Both absolute and relative paths are supported.
- **Type**: list[str]
- **Default**: ["j2_filters"]
- **Path Resolution**: 
  - When loaded through `NornFlowSettings.load`, relative paths resolve against the settings file directory
  - Direct instantiation leaves relative paths untouched, so they resolve against the runtime working directory
  - Absolute paths are used as-is
- **Example**:
  ```yaml
  local_j2_filters:
    - "j2_filters"
    - "/opt/company/shared_filters"
  ```
- **Environment Variable**: `NORNFLOW_SETTINGS_LOCAL_J2_FILTERS`
- **Important**: If you plan to delete any of the automatically created directories (from `nornflow init`) without creating or pointing to your own alternative source directories for this setting, you must set `local_j2_filters` to an empty list (`[]`) in `nornflow.yaml`. Otherwise, NornFlow will raise ResourceError exceptions during initialization and break.
- **Deep Dive**: [Jinja2 Filters Reference](./jinja2_filters.md)

### `vars_dir`

- **Description**: Path to the directory containing variable files for NornFlow's variable system. This directory will store global variables (defaults.yaml) and domain-specific variables. Both absolute and relative paths are supported.
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
- **Deep Dive**: [Variables Basics](./variables_basics.md)

### `dry_run`

- **Description**: If set to True, NornFlow will invoke Nornir in dry-run mode. This setting can be overridden at multiple levels during runtime.
- **Type**: `bool`
- **Default**: `False`
- **Runtime Precedence** (highest to lowest):
  1. CLI `--dry-run` flag or NornFlow constructor `dry_run` parameter
  2. Workflow-level `dry_run` setting in workflow YAML
  3. This settings value (which itself follows: programmatic overrides > YAML file > env var > default)
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
  3. This settings value (which itself follows: programmatic overrides > YAML file > env var > default)
- **Example**:
  ```yaml
  failure_strategy: "fail-fast"
  ```
- **Deep Dive**: [Failure Strategies](./failure_strategies.md)

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

### `logger`

- **Description**: Configuration for NornFlow's logging system. Controls where log files are written and the logging verbosity level.
- **Type**: `dict` with keys `directory` and `level`
- **Default**: `{"directory": ".nornflow/logs", "level": "INFO"}`
- **Example**:
  ```yaml
  logger:
    directory: ".nornflow/logs"
    level: "DEBUG"
  ```
- **Sub-keys**:
  - `directory`: Path to the directory where log files will be written. Relative paths resolve against the project root. The directory is created automatically if it doesn't exist.
  - `level`: Logging verbosity level. Valid values: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- **Log Levels**:
  | Level | Description |
  |-------|-------------|
  | `DEBUG` | Detailed diagnostic information including variable resolution, template compilation |
  | `INFO` | General execution flow, task start/completion, workflow progress |
  | `WARNING` | Potential issues that don't stop execution |
  | `ERROR` | Errors that may affect results (also printed to console) |
  | `CRITICAL` | Severe errors that may halt execution |
- **Note**: Log files are automatically created with timestamped filenames (e.g., `my_workflow_20260115_143022.log`). Each workflow execution creates a new log file. Errors (`ERROR` level and above) are printed to stderr regardless of the log level setting.
- **Sensitive Data Protection**: Log redaction is controlled by [`redaction.logs_enabled`](#redaction) (see section below). When enabled, values associated with keys like `password`, `secret`, `token`, or `api_key` are replaced with `***REDACTED***` in log files and stderr log output. **This is best-effort ONLY; avoid logging sensitive data, unless you know what and why you are doing it.**

### `redaction`

Controls where NornFlow redacts sensitive values before they reach an operator. Redaction is **best-effort**: it matches key names and `key=value` / `key: value` patterns in unstructured text. It is not a secrets manager.

- **Type**: `dict` — only `enabled` and `logs_enabled` are accepted; unknown keys raise a settings error.
- **Default**: `{"enabled": true, "logs_enabled": true}` when the section is omitted (***NOTE***:*`logs_enabled` inherits `enabled`* if omitted).

#### Sub-keys

| Key | Default | Applies to |
|-----|---------|------------|
| `enabled` | `true` | Terminal surfaces: `nornflow show` tables, `nornflow run` task stdout, workflow overview vars, failure/error panels |
| `logs_enabled` | inherits `enabled` | Log files under `logger.directory` and ERROR+ messages on stderr via the logging system |

**Inheritance rule:** If `logs_enabled` is omitted, it takes the same value as `enabled`. Set `logs_enabled` explicitly only when you want logs to behave differently from terminal output.

#### Examples

Default (redact everywhere):

```yaml
redaction:
  enabled: true
```

Disable redaction for local debugging (terminal **and** logs, because `logs_enabled` inherits):

```yaml
redaction:
  enabled: false
```

Redact terminal output but allow plaintext in log files (uncommon; use when you need full detail in persisted logs only):

```yaml
redaction:
  enabled: true
  logs_enabled: false
```

#### Environment variables

```bash
export NORNFLOW_SETTINGS_REDACTION__enabled=false
export NORNFLOW_SETTINGS_REDACTION__logs_enabled=false
```

#### CLI override

`--no-redact` on `nornflow show` or `nornflow run` disables **terminal** redaction for that invocation only. Log redaction is **not** affected by the CLI flag — it always follows `logs_enabled` in settings (regardless if set explicitly to `true` or `false`). To disable log redaction, set `logs_enabled: false` or just `enabled: false` (which inherits to logs when `logs_enabled` is omitted).

One-off terminal debugging with logs still protected (default settings):

```bash
nornflow show --no-redact --settings
nornflow run --no-redact workflows/my_workflow.yaml
```

#### CLI warnings

When redaction is partially or fully disabled, `nornflow show` and `nornflow run` print a yellow warning before output. Only one warning is shown per invocation:

| State | Typical cause | Message intent |
|-------|---------------|----------------|
| Terminal off, logs off | `enabled: false` (logs inherit), or both keys explicitly `false` | Secrets may appear in **terminal and log files** |
| Terminal off, logs on | `--no-redact`, or terminal disabled while `logs_enabled: true` | Secrets may appear on **screen only**; logs stay redacted |
| Terminal on, logs off | `enabled: true` with `logs_enabled: false` | Secrets may appear in **log files and stderr log output** only |

#### Placeholder

Redacted values are always shown as `***REDACTED***`.

#### What redaction does not cover

- Values stored under key names that do not match [protected keywords](../nornflow/constants.py) (`PROTECTED_KEYWORDS`)
- Secrets embedded in unstructured device output with no matching keyword pattern
- In-memory APIs (`settings.as_dict`, `nornir_configs`) — these return unmasked data; redact before printing with `nornflow.masking.mask_for_display()`:

  ```python
  from nornflow.masking import mask_for_display

  print(mask_for_display(nornflow.settings.as_dict))
  ```

#### Operator responsibility for false positives

Broad keywords like `encryption_key` or `secret_message` may be redacted even when the value is not secret. There is no per-key allowlist in V1. Workarounds:

1. **Rename the variable** — use a non-sensitive key name (e.g. `encryption_algorithm` instead of `encryption_key`).
2. **Disable terminal redaction for one command** — `nornflow show --no-redact` or `nornflow run --no-redact` (logs unaffected).
3. **Split surfaces** — keep `enabled: true` and set `logs_enabled: false` if you only need plaintext in log files.

Do not disable redaction in production.

### `packages`

- **Description**: List of NornFlow-compatible package descriptors. Each entry declares an installed Python package that contributes with NornFlow assets (tasks, workflows, filters, hooks, blueprints, Jinja2 filters, and/or processors) into NornFlow's catalogs.
- **Type**: `list[dict]`
- **Default**: `[]`
- **Example**:
  ```yaml
  packages:
    - name: "nornflow_acme_toolkit"         # import all resource types
    - name: "nornflow_xyz"
      include:                              # import only selected resource types
        - hooks
        - j2_filters
  ```
- **Deep Dive**: [Packages Guide](./packages_guide.md)

> **Note**: Environment variable override is not supported for this setting. Package declarations are structural project decisions that belong in `nornflow.yaml`.

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
<a href="./core_concepts.md">← Previous: Core Concepts</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./blueprints_guide.md">Next: Blueprints Guide →</a>
</td>
</tr>
</table>

</div>
