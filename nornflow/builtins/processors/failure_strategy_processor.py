# ruff: noqa: T201
import threading

from colorama import Fore, init, Style
from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import Result, Task
from tabulate import tabulate

from nornflow.constants import FailureStrategy

# Initialize colorama
init(autoreset=True)

# Create a global lock for synchronizing output only
output_lock = threading.Lock()


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
