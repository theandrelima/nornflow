from nornir.core.task import Result, Task


def hello_world(task: Task) -> Result:
    """Hello World task."""
    return Result(
        host=task.host,
        result="Hi there. NornFlow is working!"
    )