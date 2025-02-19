# noqa: INP001

from nornir.core.task import Result, Task


def greet_user(task: Task, greeting: str = "Hello", name: str = "User") -> Result:
    """
    A simple Nornir task that greets a user.

    Args:
        task (Task): The Nornir Task object
        greeting (str): The greeting to use (default: "Hello")
        name (str): The name to greet (default: "User")

    Returns:
        Result: Nornir Result object containing the greeting message
    """
    message = f"{greeting}, {name}! Greeting from {task.host.name}"

    return Result(host=task.host, result=message, changed=False)  # Task doesn't modify anything
