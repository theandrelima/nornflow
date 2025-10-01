# ruff: noqa: T201
import threading  # noqa: I001
from datetime import datetime

from colorama import Back, Fore, Style, init
from nornir.core.processor import Processor
from nornir.core.task import Result, Task
from nornir.core.inventory import Host
from tabulate import tabulate

from nornflow.constants import FailureStrategy

# Initialize colorama
init(autoreset=True)

# Create a global lock for synchronizing output only
# No impact on actual task execution performance.
# Prevents garbled output when multiple threads try to print simultaneously
# Ensures each task's output is printed completely before the next one starts
# Safely tracks task statistics across multiple threads
# Protects the start_times dictionary from concurrent modifications
output_lock = threading.Lock()


class DefaultNornFlowProcessor(Processor):
    """Default processor for NornFlow that tracks execution time and statistics."""

    def __init__(self):
        """Initialize processor with tracking variables for timing and statistics."""
        super().__init__()
        self.start_times = {}  # Dictionary to track start times by (task_name, host)
        self.workflow_start_time = None  # Track the overall workflow start time
        self.task_count = 0  # Count of unique tasks processed
        self.task_executions = 0  # Count of total task executions (tasks * hosts)
        self.tasks_completed = 0  # Count of unique tasks completed
        self.successful_executions = 0  # Count of successfully completed task executions
        self.failed_executions = 0  # Count of failed task executions
        self.total_workflow_tasks = 0  # Total number of workflow tasks (set externally)
        self.print_summary_after_each_task = False  # Default to only print at end

    def task_started(self, task: Task) -> None:
        """Record task start time and print header information."""
        # Track the first task as the start of the workflow
        if not self.workflow_start_time:
            self.workflow_start_time = datetime.now()
            with output_lock:
                print(
                    f"\n{Fore.GREEN}{Style.BRIGHT}Execution started at: "
                    f"{self.workflow_start_time.strftime('%H:%M:%S.%f')[:-3]}{Style.RESET_ALL}"
                )

        self.task_count += 1
        # Print task header only once per task, not per host
        with output_lock:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}Running task: {task.name}{Style.RESET_ALL}")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Record start time for a specific task on a specific host."""
        # Record the start time with high precision
        start_time = datetime.now()
        with output_lock:
            self.start_times[(task.name, host)] = start_time
        self.task_executions += 1  # Count each task execution

    def task_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        """Process task completion and print results for a specific host."""
        finish_time = datetime.now()
        status = "Success" if result.failed is False else "Failed"
        status_color = Fore.GREEN if result.failed is False else Fore.RED

        # Update execution statistics
        if result.failed is False:
            self.successful_executions += 1
        else:
            self.failed_executions += 1

        # Get the start time from our dictionary
        start_time = self.start_times.get(
            (task.name, host), finish_time
        )  # Default to finish time if not found

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

    def task_instance_failed(self, task: Task, host: Host, result: Result) -> None:
        self.task_instance_completed(task, host, result)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        # Don't track subtasks for simplicity
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        # Only print task results if you really need them
        pass

    def subtask_instance_failed(self, task: Task, host: Host, result: Result) -> None:
        # Print failed subtasks for debugging purposes
        finish_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        with output_lock:
            print(f"{Fore.RED}{'-' * 80}")
            print(f"{Style.BRIGHT}{Fore.RED}SUBTASK FAILED: {task.name} on {host} at {finish_time}")
            print(f"{Fore.WHITE}Error:\n{result.result}")
            print(f"{Fore.RED}{'-' * 80}")

    def task_completed(self, task: Task, result: Result) -> None:
        self.tasks_completed += 1

        # Only print summary at the end if this setting is enabled
        if self.print_summary_after_each_task:
            self.print_workflow_summary()

    def task_failed(self, task: Task, result: Result) -> None:
        """Handle task failure across all hosts and update statistics."""
        self.tasks_completed += 1

        # Only print summary at the end if this setting is enabled
        if self.print_summary_after_each_task:
            self.print_workflow_summary()

    def print_final_workflow_summary(self) -> None:
        """Print the final workflow summary when explicitly called at the end of all workflow tasks."""
        self.print_workflow_summary()

    def print_workflow_summary(self) -> None:
        """
        Generate and print a summary of the workflow execution with timing,
        statistics and success metrics.
        """
        if not self.workflow_start_time:
            return

        end_time = datetime.now()
        duration = end_time - self.workflow_start_time
        duration_ms = duration.total_seconds() * 1000

        # Calculate success/failure percentages based on task executions
        success_percent = (
            (self.successful_executions / self.task_executions * 100) if self.task_executions > 0 else 0
        )
        failure_percent = (
            (self.failed_executions / self.task_executions * 100) if self.task_executions > 0 else 0
        )

        # Create a visual progress bar
        bar_length = 40
        success_bars = int(bar_length * success_percent / 100)
        failure_bars = int(bar_length * failure_percent / 100)

        # Add extra space before summary
        with output_lock:
            print("\n\n")

            # WORKFLOW SUMMARY HEADER
            print(f"{Fore.YELLOW}{Style.BRIGHT}━━━ EXECUTION SUMMARY ━━━{Style.RESET_ALL}")
            print()

            # TIMING INFORMATION
            print(f"{Fore.WHITE}{Style.BRIGHT}Time Statistics:{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Started at:  {self.workflow_start_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"  {Fore.WHITE}Finished at: {end_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"  {Fore.WHITE}Duration:    {duration_ms:.0f}ms ({duration.total_seconds():.2f} seconds)")
            print()

            # TASK STATISTICS
            print(f"{Fore.WHITE}{Style.BRIGHT}Task Statistics:{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Unique Tasks:    {Style.BRIGHT}{self.tasks_completed}")
            print(f"  {Fore.WHITE}Task Executions: {Style.BRIGHT}{self.task_executions}")
            print()

            # EXECUTION RESULTS
            print(f"{Fore.WHITE}{Style.BRIGHT}Execution Results:{Style.RESET_ALL}")
            print(
                f"  {Fore.GREEN}Successful:  {Style.BRIGHT}"
                f"{self.successful_executions} ({success_percent:.1f}%)"
            )
            print(f"  {Fore.RED}Failed:      {Style.BRIGHT}{self.failed_executions} ({failure_percent:.1f}%)")
            print()

            # VISUAL GREEN/RED STATUS BAR
            bar = f"{Back.GREEN}{' ' * success_bars}{Back.RED}{' ' * failure_bars}{Style.RESET_ALL}"
            print(f"  {bar}")
            print()


class NornFlowFailureStrategyProcessor(Processor):
    """Processor for implementing failure strategies during Nornir task execution.

    This processor applies the specified failure strategy to control workflow behavior
    when tasks fail:
    - SKIP_FAILED: Nornir's default behavior - failed hosts are automatically removed
      from subsequent tasks
    - FAIL_FAST: Signals all threads to stop by adding all hosts to failed_hosts when
      a failure is detected. Already-running threads will complete before stopping.
    - RUN_ALL: Resets failed_hosts before each task to ensure all hosts run all tasks
      regardless of previous failures

    Args:
        failure_strategy: The failure handling strategy to apply.
    """

    def __init__(self, failure_strategy: FailureStrategy) -> None:
        self.failure_strategy = failure_strategy
        self.collected_errors = []
        self.fail_fast_triggered = False
        self.nornir = None

    def task_started(self, task: Task) -> None:
        # Capture the nornir instance only once, on first task
        if not self.nornir and hasattr(task, "nornir"):
            self.nornir = task.nornir

        # For RUN_ALL, reset failed hosts before each task
        # This ensures all hosts run all tasks regardless of previous failures
        if self.failure_strategy == FailureStrategy.RUN_ALL and self.nornir:
            self.nornir.data.reset_failed_hosts()

        elif self.fail_fast_triggered:
            with output_lock:
                print(
                    f"{Fore.RED}{Style.BRIGHT}Execution is halting because a task "
                    f"failed and FAIL_FAST is enabled.{Style.RESET_ALL}"
                )

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass

    def task_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        """Called after each host completes for a task."""
        if result.failed:
            self.collected_errors.append((task.name, host.name, result))

            if self.failure_strategy == FailureStrategy.FAIL_FAST and not self.fail_fast_triggered:
                self.fail_fast_triggered = True

                # Add ALL hosts to failed_hosts immediately
                # This causes Nornir to skip them in all running threads
                if self.nornir:
                    with output_lock:
                        print(
                            f"\n{Fore.RED}{Style.BRIGHT}━━━ FAILURE DETECTED: HALTING WORKFLOW ━━━{Style.RESET_ALL}"  # noqa: E501
                        )
                        print(f"{Fore.RED}Task '{task.name}' failed on host '{host.name}'")
                        if result.exception:
                            print(f"{Fore.RED}Error: {result.exception}")
                        print(f"{Fore.RED}Signaling all threads to stop...")
                        print(
                            f"{Fore.RED}NOTE: Tasks already started will continue "
                            f"to completion.{Style.RESET_ALL}"
                        )
                        print()

                    # Add all hosts to failed_hosts
                    for hostname in self.nornir.inventory.hosts:
                        self.nornir.data.failed_hosts.add(hostname)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        pass

    def task_completed(self, task: Task, result: Result) -> None:
        pass

    def print_final_workflow_summary(self) -> None:
        """Print collected error summary for all strategies."""
        if self.collected_errors:
            with output_lock:
                print("\n\n")
                print(f"{Fore.RED}{Style.BRIGHT}━━━ FAILURE SUMMARY ━━━{Style.RESET_ALL}")
                print()
                error_table = []
                for task_name, host_name, host_result in self.collected_errors:
                    error_msg = str(host_result.exception) if host_result.exception else "Unknown error"
                    error_table.append([task_name, host_name, error_msg])
                if error_table:
                    print(tabulate(error_table, headers=["Task", "Host", "Error"], tablefmt="simple"))
                print()
