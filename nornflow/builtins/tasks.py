from pathlib import Path

from nornir.core.task import Result, Task

from nornflow.builtins.utils import build_set_task_report

try:
    from nornir_napalm.plugins.tasks import *  # noqa: F403
    from nornir_netmiko.tasks import *  # noqa: F403
except ImportError:
    pass


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
    # resolved values from the variable manager to show what was actually set. This
    # task function merely handles reporting.

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


def write_file(task: Task, filename: str, content: str, append: bool = False, mkdir: bool = True) -> Result:
    """
    Write content to a file, creating directories as needed.

    Args:
        task (Task): Nornir task object
        filename (str): Path to file to write
        content (str): Content to write to file
        append (bool): Append to file instead of overwriting (default: False)
        mkdir (bool): Create parent directories if needed (default: True)

    Returns:
        Result: Result object with the path to the written file
    """
    if not filename:
        return Result(host=task.host, failed=True, exception=ValueError("filename argument is required"))

    if content is None:
        return Result(host=task.host, failed=True, exception=ValueError("content argument is required"))

    try:
        file_path = Path(filename)
        
        # Dry run mode - simulate the operation without making changes
        if task.dry_run:
            # Check if directories would need to be created
            dirs_to_create = []
            if mkdir and not file_path.parent.exists():
                dirs_to_create = [str(file_path.parent)]
            
            # Check if file exists to determine if it would be created or modified
            file_exists = file_path.exists()
            action = "append to" if (append and file_exists) else ("modify" if file_exists else "create")
            
            result_data = {
                "path": str(file_path),
                "action": f"would {action} file",
                "content_length": len(str(content)),
                "mode": "append" if append else "write",
                "dry_run": True
            }
            
            if dirs_to_create:
                result_data["directories_to_create"] = dirs_to_create
                
            return Result(host=task.host, result=result_data, changed=True)
        
        # Normal execution mode
        # Create directory if it doesn't exist
        if mkdir:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        mode = "a" if append else "w"
        with file_path.open(mode=mode, encoding="utf-8") as f:
            f.write(str(content))

        return Result(host=task.host, result={"path": str(file_path)}, changed=True)

    except Exception as e:
        return Result(host=task.host, failed=True, exception=e)