# NornFlow & Workflows

In NornFlow, a **Workflow** is a central concept that represents a sequence of one or more tasks to be executed on a Nornir inventory. Workflows are crucial to the NornFlow application as they define the automation processes that will be run on network devices.  

NornFlow acts like a central control pane, a 'know-it-all' manager making sure to instantiate all required objects to get tasks executed successfully. However, it doesn't actually execute any tasks, or handles the inventory in any way.  

The actual heavy-lifting of inventory handling and task execution is handled by the `Workflow` class. 

## The Role of the NornFlow Class

The `NornFlow` class manages the app and it's required resources, taking care of:
- **Settings Management**: Creating a `NornFlowSettings` object if one was not passed to its initializer already.
- **Catalog Management**: Creating and keeping track of Tasks and Workflows Catalogs.
- **Workflow Creation**: Creating a `Workflow` object if one was not passed to its initializer already.
- **Nornir Instance**: Based on its settings object, as well as potentially other keyword arguments, it creates a Nornir object.
- **Workflow Execution**: Acting as an abstraction for the Workflow execution via its own `run` method.

The `run` method in the `NornFlow` class is merely responsible for invoking the `run` method of its instantiated Workflow object, passing to it the Task Catalog and the Nornir object.  

## The Role of the Workflow Class

The `Workflow` class is responsible for managing and executing the sequence of tasks. It takes care of:

- **Inventory Filtering**: Applying filters to the Nornir inventory to determine which devices the tasks should be run on.
- **Task Execution**: Running the tasks in the workflow using the provided Nornir instance and tasks catalog.

The `run` method in the `Workflow` class is where the actual execution happens. It validates the tasks, applies inventory filters, and runs the tasks using the Nornir instance.



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