# Jinja2 Filters Reference

## Table of Contents
- [Introduction](#introduction)
- [Built-in Jinja2 Filters](#built-in-jinja2-filters)
- [NornFlow Custom Filters](#nornflow-custom-filters)
  - [List Operations](#list-operations)
  - [String Manipulation](#string-manipulation)
  - [Data Operations](#data-operations)
  - [Utility Filters](#utility-filters)
- [NornFlow Python Wrapper Filters](#nornflow-python-wrapper-filters)
- [Filter Chaining](#filter-chaining)
- [Common Patterns](#common-patterns)

## Introduction

NornFlow supports all standard Jinja2 filters plus custom filters included for some common automation scenarios. Filters transform variables using the pipe (`|`) symbol:

```yaml
# Basic syntax
{{ variable | filter }}
{{ variable | filter(argument) }}
{{ variable | filter1 | filter2 }}  # Chaining
```

## Built-in Jinja2 Filters

These filters come with Jinja2 and are always available:

### Essential Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `default` | Provide fallback value | `{{ vlan_id \| default(1) }}` |
| `length` | Get length of string/list/dict | `{{ vlans \| length }}` |
| `join` | Join list elements | `{{ vlans \| join(', ') }}` |
| `split` | Split string into list | `{{ csv_data \| split(',') }}` |
| `upper` | Convert to uppercase | `{{ hostname \| upper }}` |
| `lower` | Convert to lowercase | `{{ hostname \| lower }}` |
| `replace` | Replace text | `{{ text \| replace('old', 'new') }}` |
| `trim` | Remove whitespace | `{{ input \| trim }}` |
| `int` | Convert to integer | `{{ vlan_id \| int }}` |
| `float` | Convert to float | `{{ price \| float }}` |
| `string` | Convert to string | `{{ number \| string }}` |
| `bool` | Convert to boolean | `{{ enabled \| bool }}` |
| `list` | Convert to list | `{{ items \| list }}` |

### Advanced Jinja2 Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `selectattr` | Select by attribute | `{{ hosts \| selectattr('platform', 'eq', 'ios') }}` |
| `rejectattr` | Reject by attribute | `{{ hosts \| rejectattr('enabled', 'false') }}` |
| `map` | Apply filter to all | `{{ names \| map('upper') \| list }}` |
| `select` | Filter list items | `{{ numbers \| select('>', 5) \| list }}` |
| `reject` | Remove list items | `{{ numbers \| reject('>', 5) \| list }}` |
| `unique` | Remove duplicates | `{{ items \| unique \| list }}` |
| `sort` | Sort items | `{{ items \| sort }}` |
| `reverse` | Reverse items | `{{ items \| reverse }}` |
| `first` | Get first item | `{{ items \| first }}` |
| `last` | Get last item | `{{ items \| last }}` |
| `max` | Maximum value | `{{ numbers \| max }}` |
| `min` | Minimum value | `{{ numbers \| min }}` |
| `sum` | Sum values | `{{ numbers \| sum }}` |
| `abs` | Absolute value | `{{ number \| abs }}` |
| `round` | Round number | `{{ 3.14159 \| round(2) }}` |
| `format` | String formatting | `{{ 'Hello %s' \| format(name) }}` |

## NornFlow Custom Filters

### List Operations

**`flatten_list`**
```yaml
# Flatten nested lists
{{ [[1, 2], [3, 4], [5]] | flatten_list }}
# Result: [1, 2, 3, 4, 5]
```

**`unique_list`**
```yaml
# Remove duplicates while preserving order
{{ [1, 2, 2, 3, 1, 4] | unique_list }}
# Result: [1, 2, 3, 4]
```

**`chunk_list`**
```yaml
# Split list into chunks
{{ [1, 2, 3, 4, 5] | chunk_list(2) }}
# Result: [[1, 2], [3, 4], [5]]
```

### String Manipulation

**`regex_replace`**
```yaml
# Replace using regex
{{ "Router-NYC-001" | regex_replace('\d+', 'XXX') }}
# Result: "Router-NYC-XXX"

# With flags (case insensitive using re.IGNORECASE = 2)
{{ "ROUTER-nyc-001" | regex_replace('nyc', 'LAX', 2) }}
# Result: "ROUTER-LAX-001"
```

**`to_snake_case`**
```yaml
# Convert to snake_case
{{ "MyVariableName" | to_snake_case }}      # my_variable_name
{{ "VLAN-Management" | to_snake_case }}     # vlan_management
{{ "ConfigBackupTask" | to_snake_case }}    # config_backup_task
```

**`to_kebab_case`**
```yaml
# Convert to kebab-case
{{ "MyVariableName" | to_kebab_case }}      # my-variable-name
{{ "VLAN_Management" | to_kebab_case }}     # vlan-management
{{ "ConfigBackupTask" | to_kebab_case }}    # config-backup-task
```

### Data Operations

**`json_query`**
```yaml
# JMESPath queries on data structures
vars:
  interfaces:
    - name: "Gi0/1"
      vlan: 100
    - name: "Gi0/2"
      vlan: 200
tasks:
  - name: echo
    args:
      # Get all interface names
      msg: "{{ interfaces | json_query('[*].name') }}"
      # Result: ['Gi0/1', 'Gi0/2']
```

**`deep_merge`**
```yaml
# Recursively merge dictionaries
vars:
  defaults:
    ntp:
      server: "10.0.0.1"
      source: "Lo0"
    snmp:
      community: "public"
  custom:
    ntp:
      server: "10.0.0.2"
tasks:
  - name: echo
    args:
      msg: "{{ defaults | deep_merge(custom) }}"
      # Result: {ntp: {server: "10.0.0.2", source: "Lo0"}, snmp: {community: "public"}}
```

### Utility Filters

**`random_choice`**
```yaml
# Pick a random item from a list
{{ [1, 2, 3, 4, 5] | random_choice }}
```

**`is_set`**
```yaml
# Check if a variable exists and is not None
# Useful for conditional logic, including usage in 'if' hooks

# Check simple variable
{{ 'my_var' | is_set }}

# Check nested variable path
{{ 'my_var.nested.key' | is_set }}

# Check host attribute
{{ 'host.platform' | is_set }}

# Usage in 'if' hook
tasks:
  - name: backup_config_task
    if: "{{ 'running_config' | is_set }}"
```

> **What counts as "set":** The `is_set` filter returns `True` if a variable exists and is not `None`. Empty values like `""`, `[]`, `{}`, and `0` are considered "set" because they are valid assigned values. Only `None` or undefined variables return `False`.

> **Template validation with `if` hooks:** When using `is_set` with the `if` hook, task arguments (`args`) are validated before the `if` condition is evaluated. If your args reference variables that might not exist, the workflow will fail with a template error even if `if` would have been `False`. To handle potentially-missing variables in args, use the `default` filter:
> ```yaml
> tasks:
>   - name: echo
>     if: "{{ 'optional_var' | is_set }}"
>     args:
>       msg: "{{ optional_var | default('fallback value') }}"
> ```

## NornFlow Python Wrapper Filters

These provide Python-like functionality not available in standard Jinja2:

| Filter | Description | Example |
|--------|-------------|---------|
| `enumerate` | Get index-value pairs | `{{ items \| enumerate }}` → `[(0, 'a'), (1, 'b'), (2, 'c')]` |
| `zip` | Combine sequences | `{{ list1 \| zip(list2) }}` → `[('a', 1), ('b', 2), ('c', 3)]` |
| `range` | Generate number sequence | `{{ 5 \| range }}` → `[0, 1, 2, 3, 4]` |
| `divmod` | Division with remainder | `{{ 10 \| divmod(3) }}` → `(3, 1)` |
| `splitx` | Python-style split with maxsplit | `{{ text \| splitx(' ', 2) }}` |
| `type` | Get the type name of a value | `{{ value \| type }}` → `'str'` |
| `any` | Check if any element is truthy | `{{ [false, true, false] \| any }}` → `true` |
| `all` | Check if all elements are truthy | `{{ [true, false, true] \| all }}` → `false` |
| `len` | Get the length of a value | `{{ [1, 2, 3] \| len }}` → `3` |
| `sorted` | Sort items with optional key and reverse | `{{ [3, 1, 2] \| sorted }}` → `[1, 2, 3]` |
| `reversed` | Return list in reverse order | `{{ [1, 2, 3] \| reversed }}` → `[3, 2, 1]` |
| `strip` | Remove leading and trailing characters | `{{ " text " \| strip }}` → `"text"` |
| `joinx` | Join iterable with separator | `{{ [1, 2, 3] \| joinx('-') }}` → `"1-2-3"` |
| `startswith` | Check if string starts with prefix | `{{ "Router-NYC-001" \| startswith("Router") }}` → `true` |

## Filter Chaining

Filters can be chained to perform complex transformations:

```yaml
# Clean and format interface names
{{ interface | trim | upper | regex_replace('GIGABITETHERNET', 'Gi') }}
# " gigabitethernet0/1 " → "GI0/1"

# Process list of VLANs
{{ vlan_string | split(',') | map('trim') | map('int') | unique | sort }}
# "100, 200, 100, 300" → [100, 200, 300]

# Complex data extraction
{{ interfaces | json_query('[*].vlan') | unique_list | sort }}
```

## Common Patterns

### Safe Variable Access
```yaml
# Multiple fallback levels
{{ specific_ntp | default(site_ntp | default(global_ntp | default('pool.ntp.org'))) }}

# Handle missing data gracefully
{{ host.data.get('vlan_id', 1) | int }}

# Check existence before use (using is_set)
{{ 'variable_name' | is_set }}
```

### List Processing
```yaml
# Convert comma-separated string to clean list
{{ "sw1, sw2,  sw3" | split(',') | map('trim') | list }}

# Batch processing
vars:
  all_devices: ["dev1", "dev2", "dev3", "dev4", "dev5"]
tasks:
  - name: process_batch
    args:
      batch: "{{ all_devices | chunk_list(2) }}"
```

### String Formatting
```yaml
# Build consistent naming
vars:
  site: "nyc"
  role: "core"
  number: 1
tasks:
  - name: set_hostname
    args:
      hostname: "{{ site | upper }}-{{ role | upper }}-{{ '%03d' | format(number) }}"
      # Result: "NYC-CORE-001"
```

### Data Extraction with JMESPath
```yaml
# Extract nested values safely
vars:
  devices:
    - name: "router1"
      interfaces:
        - {name: "Gi0/1", vlan: 100}
        - {name: "Gi0/2", vlan: 200}
tasks:
  - name: echo
    args:
      msg: "{{ devices | json_query('[*].interfaces[*].vlan') | flatten_list | unique_list }}"
      # Result: [100, 200]
```

<div align="center">
  
## Navigation

<table width="100%" border="0" style="border-collapse: collapse;">
<tr>
<td width="33%" align="left" style="border: none;">
<a href="./nornflow_settings.md">← Previous: NornFlow Settings</a>
</td>
<td width="33%" align="center" style="border: none;">
</td>
<td width="33%" align="right" style="border: none;">
<a href="./api_reference.md">Next: API Reference →</a>
</td>
</tr>
</table>

</div>
