# ruff: noqa: T201
import threading
from pathlib import Path

from nornir.core.task import Result, Task

from nornflow.builtins.utils import build_set_task_report, get_task_vars_manager
from nornflow.logger import logger


def set(task: Task, print_output: bool = True, **kwargs) -> Result:
    """
    NornFlow built-in task to set runtime variables for the current device.

    This task allows you to define new NornFlow runtime variables or update existing ones
    for the specific device the task is currently operating on. The variable setting logic,
    including Jinja2 template resolution for values, is handled directly by this task function.

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

    Raises:
        ProcessorError: If the NornFlowVariableProcessor cannot be found in the processor chain.

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
    vars_manager = get_task_vars_manager(task)

    # Process and set each variable
    for key, value in kwargs.items():
        # Resolve templates in the value (if any)
        resolved_value = vars_manager.resolve_data(value, task.host.name)
        # Store the variable in the runtime namespace for the current host
        vars_manager.set_runtime_variable(key, resolved_value, task.host.name)

    # Generate the detailed report
    report = build_set_task_report(task, kwargs) if print_output else None
    return Result(host=task.host, result=report)


def echo(task: Task, msg: str) -> Result:
    """
    Echoes the provided text back to the user.

    Returns:
        Result object containing the echoed text

    Example:
        name: echo
        args:
            msg: "Hello from {{ host.name }}, platform is {{ host.platform }}"
    """
    return Result(host=task.host, result=msg)


def pause(task: Task, msg: str = "", timer: int = 0) -> Result:
    """Pause workflow execution, optionally with a countdown timer.

    When ``timer`` is provided, displays a countdown and auto-continues
    when it expires.

    When no ``timer`` is given, blocks until the user presses Enter.

    Args:
        task: The Nornir Task object.
        msg: Optional message explaining the reason for the pause.
        timer: Seconds to wait before auto-continuing. 0 means wait
            indefinitely for user input.

    Returns:
        Result with a summary of the pause action.

    Example in workflow YAML:
        ```yaml
        - name: wait_for_reboot
          task: pause
          single: true
          args:
            msg: "Device is rebooting — wait for it to come back"
            timer: 120

        - name: confirm_cabling
          task: pause
          single: true
          args:
            msg: "Verify all cables are connected, then press Enter"
        ```
    """
    host_label = f"[{task.host.name}]"

    if msg:
        print(f"\n{'=' * 60}")
        print(f"{host_label} {msg}")
        print(f"{'=' * 60}")

    if timer:
        result_msg = _pause_with_timer(host_label, timer)
    else:
        result_msg = _pause_wait_for_enter(host_label)

    return Result(host=task.host, result=result_msg)


def _pause_with_timer(host_label: str, seconds: int) -> str:
    """Run a countdown timer that auto-continues when expired.

    Uses threading.Event.wait() as a portable, interruptible sleep
    that responds to Ctrl+C cleanly via KeyboardInterrupt.

    Args:
        host_label: Label prefix for console output.
        seconds: Total countdown duration.

    Returns:
        Summary string describing what happened.
    """
    stop = threading.Event()

    print(f"{host_label} Pausing for {seconds}s...")

    elapsed = 0
    while elapsed < seconds and not stop.is_set():
        remaining = seconds - elapsed
        mins, secs = divmod(remaining, 60)
        print(f"\r{host_label} Resuming in {mins:02d}:{secs:02d} ", end="", flush=True)
        stop.wait(timeout=1)
        elapsed += 1

    print()

    return f"Pause completed ({seconds}s)"


def _pause_wait_for_enter(host_label: str) -> str:
    """Block until the user presses Enter.

    Args:
        host_label: Label prefix for console output.

    Returns:
        Summary string.
    """
    input(f"{host_label} Press Enter to continue...")
    return "Resumed by user"


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

    file_path = Path(filename)

    if task.is_dry_run():
        return Result(
            host=task.host,
            result={
                "path": str(file_path),
                "dry_run": True,
                "message": f"Would have created file: {file_path}",
                "operation": "write" if not append else "append",
                "would_create_dirs": mkdir and not file_path.parent.exists(),
                "content_size_bytes": len(str(content)) if content else 0,
            },
            changed=True,
        )

    try:
        # Create directory if it doesn't exist
        if mkdir:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        mode = "a" if append else "w"
        with file_path.open(mode=mode, encoding="utf-8") as f:
            f.write(str(content))

        return Result(host=task.host, result={"path": str(file_path)}, changed=True)

    except Exception as e:
        logger.exception(f"Failed to write file '{filename}': {e}")
        return Result(host=task.host, failed=True, exception=e)