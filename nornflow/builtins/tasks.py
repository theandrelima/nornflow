from nornir.core.task import Result, Task
from nornflow.builtins.utils import build_set_task_report


def set(task: Task, **kwargs) -> Result:
    """
    NornFlow built-in task to set runtime variables for the current device.

    This task allows you to define new NornFlow runtime variables or update existing ones
    for the specific device the task is currently operating on. The actual variable
    setting logic, including Jinja2 template resolution for values, is handled by
    the `NornFlowVariableProcessor` before this Python function is called.

    Variables set using this task become "Runtime Variables" (precedence #2)
    in the NornFlow variable system for the current device. These variables are
    isolated to the device instance.

    Args:
        task: The Nornir Task object.
        **kwargs: Key-value pairs representing the NornFlow runtime variables to set.
                  The keys are the variable names, and the values are their
                  corresponding values (which can be Jinja2 templates). These
                  arguments are defined under the 'args:' section of the 'set'
                  task in a workflow YAML file.

    Returns:
        Result: A Nornir Result object indicating the task was processed.
                The `result` attribute contains a detailed report of what 
                variables were set and their resolved values.

    Example in workflow YAML:
        ```yaml
        - name: set_device_specific_info
          task: set
          args:
            backup_filename: "{{ host.name }}_{{ '%Y%m%d' | strftime }}.cfg"
            is_configured: true
            attempt_counter: "{{ attempt_counter | default(0) | int + 1 }}"
            complex_data:
              status: "active"
              interfaces: ["{{ host.data.mgmt_if }}", "lo0"]
        ```
    """
    # By the time this function is called, the NornFlowVariableProcessor has already
    # resolved the Jinja2 templates and set the variables. We need to retrieve the
    # resolved values from the variable manager to show what was actually set.
    
    report = build_set_task_report(task, kwargs)
    return Result(host=task.host, result=report)


def echo(task: Task, msg: str) -> Result:
    """
    Echoes the provided text back to the user.

    Returns:
        Result object containing the echoed text
    
    Example:
        echo:
          args:
            text: "Hello from {{ host.name }}, platform is {{ host.platform }}"
    """
    return Result(host=task.host, result=msg)