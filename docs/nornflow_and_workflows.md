# NornFlow & Workflows

In NornFlow, a **Workflow** is a central concept that represents a sequence of one or more tasks to be executed on a Nornir inventory. Workflows are crucial to the NornFlow application as they define the automation processes that will be run on network devices.  

NornFlow acts like a central control pane, a 'know-it-all' manager making sure to instantiate all required objects to get tasks executed successfully. However, it doesn't actually execute any tasks, or handles the inventory in any way.  

The actual heavy-lifting of inventory handling and task execution is handled by the `Workflow` class with the help of the `NornirManager` class.

## The Role of the [NornFlow Class](../nornflow/nornflow.py)

The `NornFlow` class manages the app and it's required resources, taking care of:
- **Settings Management**: Creating a `NornFlowSettings` object if one was not passed to its initializer already.
- **Catalog Management**: Creating and keeping track of Tasks, Workflows, and Filters Catalogs.
- **Workflow Creation**: Creating a `Workflow` object if one was not passed to its initializer already.
- **NornirManager Creation**: Based on its settings object, it creates a `NornirManager` that will handle Nornir instances. This instance is later passed to the `Workflow` object.
- **Workflow Execution**: Acting as an abstraction for the Workflow execution via its own `run` method.

The `run` method in the `NornFlow` class is merely responsible for invoking the `run` method of its instantiated Workflow object, passing to it the Task Catalog and the NornirManager object.

## The Role of the [NornirManager Class](../nornflow/nornir_manager.py)

The `NornirManager` class serves as an abstraction layer between the Workflow and Nornir. It's responsible for:

- **Nornir Instance Creation**: Creating and configuring the Nornir object based on settings.
- **Processor Management**: Applying processors to the Nornir instance.
- **Inventory Management**: Providing methods to access and filter the inventory.

This abstraction provides better separation of concerns and allows for more flexible customization of the Nornir instance.

## The Role of the [Workflow Class](../nornflow/workflow.py)

The `Workflow` class is responsible for managing and executing the sequence of tasks. It takes care of:

- **Ensuring Filters**: Workflow identifies the filtering criteria requested by the user and interfaces with the `NornirManager` object to filter the inventory down to the devices the tasks should be run on. It supports multiple filtering methods:
  - **Built-in filters**: Special 'hosts' and 'groups' filters for simple device selection
  - **Custom filter functions**: Advanced filtering logic defined in your filters catalog
  - **Direct attribute filtering**: Simple equality matching using any host attribute  
These filters are applied sequentially, each narrowing down the inventory selection with AND logic.
- **Task Execution**: Running the tasks in the workflow using the Tasks Catalog received from `NornFlow` and the Nornir instance exposed by the `NornirManager`.
- **Execution Flow**: Managing the execution flow including processor application and summary generation.

The `run` method in the `Workflow` class is where the actual execution happens.

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
<a href="./how_to_write_workflows.md">Next: Writing Workflows →</a>
</td>
</tr>
</table>

</div>