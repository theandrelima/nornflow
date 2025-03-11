# Getting Started with NornFlow

## Table of Contents
- [Installation](#installation)
  - [Using pip](#using-pip)
  - [Using poetry](#using-poetry)
  - [Using uv](#using-uv)
- [Basic Usage](#basic-usage)
  - [Initializing NornFlow](#initializing-nornflow)
  - [Cataloging Tasks](#cataloging-tasks)
  - [Cataloging Workflows](#cataloging-workflows)
  - [Cataloging Filters](#cataloging-filters)
  - [Running a Single Task](#running-a-single-task)
  - [Running a Workflow](#running-a-workflow)

## Installation

You can install NornFlow in a number of ways.

### Using pip

```sh
pip install nornflow
```


### Using poetry

```sh
poetry add nornflow
```


### Using uv

```sh
uv pip install nornflow
```

or

```sh
uv add nornflow
```

From a development point of view, NornFlow uses uv for dependency and environment management.

## Basic Usage

### Initializing NornFlow
Once nornflow has been installed in your environment, you can do:

```shell
 $nornflow init
+----------------------------------------------------------------------------+
| The 'init' command creates directories, and samples for configs, tasks and |
| workflows files, all with default values that you can modify as desired.   |
| No customization of 'init' parameters available yet.                       |
|                                                                            |
| Do you want to continue?                                                   |
+----------------------------------------------------------------------------+
Do you want to continue? [Y/n]:
```

>🚨 ***`nornflow init` attempts to create minimal assets required by NornFlow. If files and/or directories with the same names as of those that the `init` command tries to create already exist, they are just skipped.***

Assuming the user chooses to continue, the following output means NornFlow was successfully initialzed in the directory:
```shell
NornFlow will be initialized at /tmp/nornflow_test
Created directory: /tmp/nornflow_test/nornir_configs
Created a sample 'nornir_configs' directory: /tmp/nornflow_test/nornir_configs
Created a sample 'nornflow.yaml': /tmp/nornflow_test/nornflow.yaml
Created directory: /tmp/nornflow_test/tasks
Created sample tasks in directory: /tmp/nornflow_test/tasks
Created directory: /tmp/nornflow_test/workflows
Created a sample 'hello_world' workflow in directory: /tmp/nornflow_test/workflows
Created directory: /tmp/nornflow_test/filters


                  NORNFLOW SETTINGS                  
╭──────────────────────┬────────────────────────────╮
│       Setting        │ Value                      │
├──────────────────────┼────────────────────────────┤
│  nornir_config_file  │ config.yaml                │
├──────────────────────┼────────────────────────────┤
│   local_tasks_dirs   │ ['tasks']                  │
├──────────────────────┼────────────────────────────┤
│ local_workflows_dirs │ ['workflows']              │
├──────────────────────┼────────────────────────────┤
│  local_filters_dirs  │ ['filters']                │
├──────────────────────┼────────────────────────────┤
│  imported_packages   │ []                         │
├──────────────────────┼────────────────────────────┤
│       dry_run        │ False                      │
╰──────────────────────┴────────────────────────────╯


                                   TASKS CATALOG                                   
╭─────────────┬──────────────────────────────────────────┬────────────────────────╮
│  Task Name  │ Description                              │ Location               │
├─────────────┼──────────────────────────────────────────┼────────────────────────┤
│ greet_user  │ A simple Nornir task that greets a user. │ greet_user.py          │
├─────────────┼──────────────────────────────────────────┼────────────────────────┤
│ hello_world │ Hello World task.                        │ hello_world.py         │
╰─────────────┴──────────────────────────────────────────┴────────────────────────╯


                                  WORKFLOWS CATALOG                                  
╭──────────────────┬───────────────────────────────────┬────────────────────────────╮
│  Workflow Name   │ Description                       │ Location                   │
├──────────────────┼───────────────────────────────────┼────────────────────────────┤
│ hello_world.yaml │ A simple workflow that just works │ hello_world.yaml           │
╰──────────────────┴───────────────────────────────────┴────────────────────────────╯


                            FILTERS CATALOG                             
╭───────────────┬───────────────────────────────────┬──────────────────╮
│  Filter Name  │ Description                       │ Location         │
├───────────────┼───────────────────────────────────┼──────────────────┤
│    groups     │ Filter hosts by group membership. │ nornflow.filters │
│               │ Parameters: groups                │                  │
├───────────────┼───────────────────────────────────┼──────────────────┤
│     hosts     │ Filter hosts by hostname.         │ nornflow.filters │
│               │ Parameters: hosts                 │                  │
╰───────────────┴───────────────────────────────────┴──────────────────╯
```

Notice the files and folders the `nornflow init` command created:
- 📝 `nornflow.yaml` file: This settings file dictates NornFlow's behaviors and where it should look for Nornir Tasks and Workflows to include in its Catalogs. The output summarizes the settings in the `NORNFLOW SETTINGS` table. You can check the contents of this sample file [here](../nornflow/cli/samples/nornflow.yaml).
- 📂 `tasks` folder: Contains two .py files, each with a single Nornir task. NornFlow automatically identifies and imports Nornir tasks into its `TASK CATALOG`. Check the sample tasks in [hello_world.py](../nornflow/cli/samples/hello_world.py) and [greet_user.py](../nornflow/cli/samples/greet_user.py).
- 📂 `workflows` folder: Contains a single `hello_world.yaml` file. This workflow includes the same two tasks mentioned above. NornFlow automatically identifies and imports Workflows into its `WORKFLOWS CATALOG`. Check this sample Workflow in [hello_world.yaml](../nornflow/cli/samples/hello_world.yaml).
- 📂 `filters` folder: Initially empty, this folder is where you can place custom filter functions to be included in the `FILTERS CATALOG`. 
- 📂 `nornir_configs` folder: Contains Nornir YAML files with trivial configs using Nornir's 'SimpleInventory', a single host and group for localhost (127.0.0.1), and dummy credentials. For most real-world scenarios, these files will need to be reworked. Check the sample files [here](../nornflow/cli/samples/nornir_configs/).

For a detailed explanation of NornFlow Settings, see the [Settings](./nornflow_settings.md) section.


### Cataloging Tasks
> 🚨 ***NOTE: In this documentation, we won't go into the details of what are Tasks and how to write them. Those are Nornir concepts, and pre-requisites to use NornFlow. You may want to check [Nornir's docs](https://github.com/nornir-automation/nornir)***  


When writing Nornir tasks for NornFlow, it's important to know about the `local_tasks_dirs` in your `nornflow.yaml` file. This setting lists directories where NornFlow looks for Nornir tasks to include in its **Task Catalog**.  
NornFlow will recursively search these directories for Python modules. For NornFlow to identify Tasks, they must have at least one argument annotated with `Task` and a return type of `Result`, `MultiResult`, or `AggregatedResult`.  

For example:

```python
# /tmp/nornflow_test/tasks/new_task.py
from nornir.core.task import Task, Result

def gather_facts(task: Task) -> Result:
    """
    Docstring's first line will show up as the Task's 'Description' in the TASK CATALOG. 
    """
    facts = {
        "hostname": task.host.hostname,
        "username": task.host.username,
        "platform": task.host.platform,
    }
    return Result(
        host=task.host,
        result=facts
    )

# Write as many Nornir Tasks as you want in this same .py file.
# Other code may exist as well. Anything that is not a 
# Nornir Task (annoteted as such) will be ignored by NornFlow
```

Now you can check if your newly created Task can be used by NornFlow by checking the Catalog:
```shell
$ nornflow show --catalog


                                                               TASKS CATALOG
╭──────────────┬──────────────────────────────────────────────────────────────────────────────────────┬────────────────────────╮
│  Task Name   │ Description                                                                          │ Location               │
├──────────────┼──────────────────────────────────────────────────────────────────────────────────────┼────────────────────────┤
│ hello_world  │ Hello World task.                                                                    │ ./tasks/hello_world.py │
├──────────────┼──────────────────────────────────────────────────────────────────────────────────────┼────────────────────────┤
│ gather_facts │ Docstring's first line will show up as the Task's 'Description' in the TASK CATALOG. │ ./tasks/new_task.py    │<<<< HERE IT IS!!!
├──────────────┼──────────────────────────────────────────────────────────────────────────────────────┼────────────────────────┤
│  greet_user  │ A simple Nornir task that greets a user.                                             │ ./tasks/greet_user.py  │
╰──────────────┴──────────────────────────────────────────────────────────────────────────────────────┴────────────────────────╯

# 'WORKFLOWS CATALOG' omitted for brevity ...
```

### Cataloging Workflows

>🚨 ***NOTE: For greater details on how to write Workflows, check [Writing Workflows](./how_to_write_workflows.md)***  

When it comes to Workflows, pretty much the same general ideas around writing Tasks also apply. The important distinctions to keep in minde are:
- The relevant setting here is `local_workflows_dir`. It also is a list of directory paths that are supposed to hold workflow files written in YAML.
- The detection logic is simpler in this case, and will just assume any `.yml` or `.yaml` is a Workflow file. The search is also recursive.
- Only one Workflow is allowed per YAML file.


You can also check what workflows are known by NornFlow with the `nornflow show --catalog` command:
```
nornflow show --catalog

# 'TASKS CATALOG' ommited for brevity...

                          WORKFLOWS CATALOG
╭──────────────────┬───────────────────────────────────┬────────────────────────────╮
│  Workflow Name   │ Description                       │ Location                   │
├──────────────────┼───────────────────────────────────┼────────────────────────────┤
│ hello_world.yaml │ A simple workflow that just works │ workflows/hello_world.yaml │
╰──────────────────┴───────────────────────────────────┴────────────────────────────╯
```

Again, for a simple example of how a NornFlow Workflow YAML file should look like, check the sample workflow.

> 🚨 ***As of now, workflows still don't support advanced features like loops, conditionals and variables. These are planned features, but for the moment developers would have to account for it directly through Python logic implemented in their Tasks.***

### Cataloging Filters

NornFlow's filtering system allows you to target specific hosts in your inventory when running tasks or workflows. The `local_filters_dirs` setting in your `nornflow.yaml` file specifies directories where NornFlow looks for custom filter functions.

#### Built-in Filters

NornFlow comes with built-in filters in the [nornflow.filters](../nornflow/filters.py) module:

```shell
$ nornflow show --catalog

# 'TASKS CATALOG' and 'WORKFLOWS CATALOG' omitted for brevity...

                            FILTERS CATALOG                             
╭───────────────┬───────────────────────────────────┬──────────────────╮
│  Filter Name  │ Description                       │ Location         │
├───────────────┼───────────────────────────────────┼──────────────────┤
│    groups     │ Filter hosts by group membership. │ nornflow.filters │
│               │ Parameters: groups                │                  │
├───────────────┼───────────────────────────────────┼──────────────────┤
│     hosts     │ Filter hosts by hostname.         │ nornflow.filters │
│               │ Parameters: hosts                 │                  │
╰───────────────┴───────────────────────────────────┴──────────────────╯
```

#### Creating Custom Filters

Custom filters must follow this structure:
1. First parameter must be a `host` parameter
2. Return a boolean value
3. Any additional parameters will be matched with values provided in the workflow

For example:

```python
# /tmp/nornflow_test/filters/location_filters.py
from nornir.core.inventory import Host

def filter_by_location(host: Host, city: str, building: str) -> bool:
    """
    Filter hosts by location (city and building).
    
    This description will appear in the FILTERS CATALOG.
    """
    return (host.data.get("city") == city and
            host.data.get("building") == building)

def filter_by_city(host: Host, city: str) -> bool:
    """
    Filter hosts by city.
    """
    return host.data.get("city") == city
```

After creating this file, your custom filters will appear in the catalog:

```shell
$ nornflow show --catalog

# 'TASKS CATALOG' and 'WORKFLOWS CATALOG' omitted for brevity...

                                FILTERS CATALOG                                 
╭──────────────────┬───────────────────────────────────────┬───────────────────────────────╮
│   Filter Name    │ Description                           │ Location                      │
├──────────────────┼───────────────────────────────────────┼───────────────────────────────┤
│ filter_by_city   │ Filter hosts by city.                 │ ./filters/location_filters.py │
│                  │ Parameters: city                      │                               │
├──────────────────┼───────────────────────────────────────┼───────────────────────────────┤
│filter_by_location│ Filter hosts by location (city and    │ ./filters/location_filters.py │
│                  │ building).                            │                               │
│                  │ Parameters: city, building            │                               │
├──────────────────┼───────────────────────────────────────┼───────────────────────────────┤
│     groups       │ Filter hosts by group membership.     │ nornflow.filters              │
│                  │ Parameters: groups                    │                               │
├──────────────────┼───────────────────────────────────────┼───────────────────────────────┤
│     hosts        │ Filter hosts by hostname.             │ nornflow.filters              │
│                  │ Parameters: hosts                     │                               │
╰──────────────────┴───────────────────────────────────────┴───────────────────────────────╯
```

NornFlow automatically discovers filter functions and parameter names through introspection, allowing for flexible parameter passing in workflows. For more details on filters, see [Inventory Filtering](./how_to_write_workflows.md#inventory-filtering) section in the Workflows documentation.


### Running a Single Task
The only condition for NornFlow to be able to run a Task, is for it to be known in it's TASKS CATALOG. Once that condition is satisfied, users can use the `nornflow run` CLI command:
```
nornflow run <task-name> [--args]
```
> 💡***Refer to the CLI help (`nornflow run --help`) for more details, like valid formats for args, filtering options, etc...*** 

Here is an example of running a task without passing any args.

```shell
 $nornflow run greet_user

Running: greet_user (args: {}, hosts: None, groups: None, dry-run: False)
--------------------------------------------------------------------------------

Started: 2025-02-25 13:21:26

Task: greet_user | Host: localhost | Status: Success
Output:
Hello, User! Greeting from localhost

Finished: 2025-02-25 13:21:26

--------------------------------------------------------------------------------
```

As the 'Description' field in the TASKS CATALOG let us know, the `greet_user` task actually have 2 optional args:
 - greeting (str): The greeting to use (default: "Hello")
 - user (str): The name to greet (default: "User")

 Let's run that task again, now passing those arguments:

```shell
$ nornflow run greet_user --args "user='Andre', greeting='Hello there'"

Running: greet_user (args: {'user': 'Andre', 'greeting': 'Hello there'}, hosts: None, groups: None, dry-run: False)
--------------------------------------------------------------------------------

Started: 2025-02-25 13:40:37

Task: greet_user | Host: localhost | Status: Success
Output:
Hello there, Andre! Greetings from localhost

Finished: 2025-02-25 13:40:37

--------------------------------------------------------------------------------
```

### Running a Workflow
To run NornFlow Workflows, you still use the same CLI:
```
nornflow run <worflow_name.yaml>
```
> 💡 ***Refer to the CLI help (`nornflow run --help`) for more details, like filtering options, and dry-run mode.***  


Let's run the only Workflow currently present in the Workflows Catalog, the [hello_world.yaml](../nornflow/cli/samples/hello_world.yaml):  
```shell
$ nornflow run hello_world.yaml

Running: hello_world.yaml (args: {}, hosts: None, groups: None, dry-run: False)
--------------------------------------------------------------------------------

Started: 2025-02-25 15:16:03

Task: hello_world | Host: localhost | Status: Success
Output:
Hi there. NornFlow is working!

Finished: 2025-02-25 15:16:03

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------

Started: 2025-02-25 15:16:03

Task: greet_user | Host: localhost | Status: Success
Output:
Hello, you beautiful person! Greetings from localhost

Finished: 2025-02-25 15:16:03

--------------------------------------------------------------------------------


```
The *TARGET* for the `nornflow run` command **MUST** have a `.yaml` or `.yml` extension to indicate a workflow execution.  

While a Task must exist in the TASK CATALOG for NornFlow to run it, the WORKFLOWS CATALOG is just a convenience. You can run any workflow by passing its file path to the `nornflow run` command, even if it isn't in the `local_workflows_dirs` setting.  

Still, there are real benefits for properly cataloging workflows:
- **Organization**: Set locations for workflows make them easy to find.
- **Less typing**: Run cataloged workflows by name instead of the full file path.

  
  <div align="center">
    
  ## Navigation
  
  [Next: NornFlow Settings](./nornflow_settings.md)
  
  </div>