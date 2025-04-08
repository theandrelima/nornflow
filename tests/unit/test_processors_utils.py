from nornir.core.processor import Processor


class TestProcessor(Processor):
    """Test processor for CLI tests."""

    def __init__(self, name="TestProcessor", verbose=False, priority=0):
        """Initialize test processor."""
        self.name = name
        self.verbose = verbose
        self.priority = priority
        self.task_results = {}

    def task_started(self, task):
        """Log when task starts."""
        self.task_results[task.name] = {"status": "started"}

    def task_completed(self, task, result):
        """Log when task completes."""
        self.task_results[task.name] = {"status": "completed", "result": result}

    def task_instance_started(self, task, host):
        """Log when task instance starts."""
        if self.verbose:
            print(f"Task {task.name} started on {host.name}")

    def task_instance_completed(self, task, host, result):
        """Log when task instance completes."""
        if self.verbose:
            print(f"Task {task.name} completed on {host.name} with result: {result}")

    def subtask_instance_started(self, task, host):
        """Log when subtask instance starts."""
        pass

    def subtask_instance_completed(self, task, host, result):
        """Log when subtask instance completes."""
        pass


class TestProcessor2(TestProcessor):
    """Second test processor with different default name."""

    def __init__(self, name="TestProcessor2", verbose=False, priority=0):
        """Initialize with different default name."""
        super().__init__(name=name, verbose=verbose, priority=priority)


class TestProcessor2(TestProcessor):
    """Second test processor with different default name."""

    def __init__(self, name="TestProcessor2", verbose=False):
        """Initialize with different default name."""
        super().__init__(name=name, verbose=verbose)
