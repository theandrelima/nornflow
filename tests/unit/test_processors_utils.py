from nornir.core.processor import Processor
from nornir.core.task import Result, Task


class TestProcessor(Processor):
    """Simple processor for testing with configurable attributes."""
    
    def __init__(self, name="TestProcessor", verbose=False, priority=0):
        self.name = name
        self.verbose = verbose
        self.priority = priority
        self.tasks_started = []
        
    def task_started(self, task: Task) -> None:
        self.tasks_started.append(task.name)
        
    def __eq__(self, other):
        if not isinstance(other, TestProcessor):
            return False
        return (self.name == other.name and 
                self.verbose == other.verbose and 
                self.priority == other.priority)


class TestProcessor2(Processor):
    """Second test processor to test multiple processor loading."""
    
    def __init__(self, name="TestProcessor2"):
        self.name = name
        self.tasks_started = []
        
    def task_started(self, task: Task) -> None:
        self.tasks_started.append(task.name)