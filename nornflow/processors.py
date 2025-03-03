# ruff: noqa: T201
from datetime import datetime  # noqa: I001
import threading

from colorama import Fore, Style, init
from nornir.core.processor import Processor
from nornir.core.task import Result, Task

# Initialize colorama
init(autoreset=True)

# Create a global lock for synchronizing output
output_lock = threading.Lock()


class DefaultNornFlowProcessor(Processor):
    def __init__(self):
        super().__init__()
        self.start_times = {}  # Dictionary to track start times by (task_name, host)
    
    def task_started(self, task: Task) -> None:
        # Print task header only once per task, not per host
        with output_lock:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}Running task: {task.name}{Style.RESET_ALL}")

    def task_instance_started(self, task: Task, host: str) -> None:
        # Record the start time with high precision
        start_time = datetime.now()
        with output_lock:
            self.start_times[(task.name, host)] = start_time
    
        # Update to task_instance_completed method
    def task_instance_completed(self, task: Task, host: str, result: Result) -> None:
        finish_time = datetime.now()
        status = "Success" if result.failed is False else "Failed"
        status_color = Fore.GREEN if result.failed is False else Fore.RED
        
        # Get the start time from our dictionary
        start_time = self.start_times.get((task.name, host), finish_time)  # Default to finish time if not found
        
        # Format times to show hours:minutes:seconds.milliseconds
        start_str = start_time.strftime("%H:%M:%S.%f")[:-3]  # Trim microseconds to milliseconds
        finish_str = finish_time.strftime("%H:%M:%S.%f")[:-3]
        
        # Calculate duration
        duration = finish_time - start_time
        duration_ms = duration.total_seconds() * 1000
        
        # Use the lock to ensure this entire block prints together
        with output_lock:
            print(f"{Fore.WHITE}{'-' * 80}")
            print(
                f"{Style.BRIGHT}{Fore.CYAN}Task: {task.name} "
                f"{Fore.WHITE}| {Fore.YELLOW}Host: {host} "
                f"{Fore.WHITE}| {Fore.MAGENTA}Hostname: {task.host.hostname or 'N/A'} "
                f"{Fore.WHITE}| {status_color}Status: {status}"
            )
            print(f"{Fore.BLUE}{start_str} - {finish_str} ({duration_ms:.0f}ms)")
            print(f"\n{Fore.WHITE}Output:\n{result.result}")
            print(f"{Fore.WHITE}{'-' * 80}")
            
            # Clean up our dictionary
            if (task.name, host) in self.start_times:
                del self.start_times[(task.name, host)]

    def task_instance_failed(self, task: Task, host: str, result: Result) -> None:
        self.task_instance_completed(task, host, result)

    def subtask_instance_started(self, task: Task, host: str) -> None:
        # Don't track subtasks for simplicity
        pass

    def subtask_instance_completed(self, task: Task, host: str, result: Result) -> None:
        # Only print subtask results if you really need them
        pass

    def subtask_instance_failed(self, task: Task, host: str, result: Result) -> None:
        # Print failed subtasks for debugging purposes
        finish_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with output_lock:
            print(f"{Fore.RED}{'-' * 80}")
            print(f"{Style.BRIGHT}{Fore.RED}SUBTASK FAILED: {task.name} on {host} at {finish_time}")
            print(f"{Fore.WHITE}Error:\n{result.result}")
            print(f"{Fore.RED}{'-' * 80}")

    def task_completed(self, task: Task, result: Result) -> None:
        pass

    def task_failed(self, task: Task, result: Result) -> None:
        pass