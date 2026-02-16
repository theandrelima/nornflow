# ruff: noqa: T201, SLF001
import threading
from datetime import datetime

from colorama import Back, Fore, init, Style
from nornir.core.inventory import Host
from nornir.core.processor import Processor
from nornir.core.task import Result, Task

from nornflow.builtins.constants import SILENT_SKIP_FLAG

# Initialize colorama
init(autoreset=True)

# Reentrant lock that serializes all console output across concurrent Nornir
# worker threads.  Prevents interleaving when multiple threads print task
# result blocks, workflow banners, or execution summaries simultaneously.
# Built-in tasks that perform interactive I/O (e.g. pause) may also acquire
# this lock to coordinate their output with the processor's result printing.
# Reentrant (RLock) so the same thread can safely acquire it multiple times
# without deadlocking — necessary when a task holds the lock across its
# return boundary into task_instance_completed on the same thread.
output_lock = threading.RLock()


class DefaultNornFlowProcessor(Processor):
    """Default processor for NornFlow that tracks execution time and statistics."""

    supports_shush_hook = True

    def __init__(self):
        """Initialize processor with tracking variables for timing and statistics."""
        super().__init__()

        # Dictionary to track start times for each (task_name, host) pair for timing calculations
        self.start_times = {}

        # Timestamp when the entire workflow started, used for overall duration
        self.workflow_start_time = None

        # Number of unique tasks that have started (incremented once per task in task_started)
        self.task_count = 0

        # Total number of task-host executions
        # (incremented for each host that actually runs a task, excluding predicate-skipped hosts)
        self.task_executions = 0

        # Number of unique tasks that have completed (incremented once per task in task_completed/task_failed)
        self.tasks_completed = 0

        # Number of successful task-host executions (hosts that completed without failure)
        self.successful_executions = 0

        # Number of failed task-host executions (hosts that failed during execution)
        self.failed_executions = 0

        # Number of skipped task-host executions (hosts skipped due to predicates or result.skipped)
        self.skipped_executions = 0

        # Total number of hosts in the inventory (set once from the first task)
        self.total_hosts = None

        # Flag to enable printing workflow summary after each task completion
        self.print_summary_after_each_task = False

        # Tracks (task_name, host_name) pairs where pause() acquired output_lock
        # and deferred release to task_instance_completed. Entries are added by
        # pause() and removed by task_instance_completed after printing the result
        # block. _cleanup_pause_lock_holders provides a safety net in task_completed
        # / task_failed for any orphaned entries that survived due to framework errors.
        self._pause_lock_holders: set[tuple[str, str]] = set()

    def _is_output_suppressed(self, task: Task) -> bool:
        """Check if output should be suppressed for the given task.

        Args:
            task: The Nornir task to check

        Returns:
            True if output should be suppressed, False otherwise
        """
        if not hasattr(task.nornir, "_nornflow_suppressed_tasks"):
            return False

        for proc in task.nornir.processors:
            if hasattr(proc, "task_specific_context"):
                nornflow_task_model = proc.task_specific_context.get("task_model")
                return nornflow_task_model.canonical_id in task.nornir._nornflow_suppressed_tasks

        return False

    def _format_task_output(self, result: Result, suppress_output: bool) -> str:
        """Format the output section of a task result.

        Args:
            result: The task result containing output data
            suppress_output: Whether to suppress the actual output content

        Returns:
            Formatted output string with appropriate styling
        """
        if not suppress_output and result.result:
            return f"\n{Fore.WHITE}Output:\n{result.result}"
        if suppress_output:
            return f"\n{Fore.WHITE}Output: {Style.DIM}[Shushed!]{Style.RESET_ALL}"
        return ""

    def _is_silent_skip(self, host: Host) -> bool:
        """Check if a host is flagged for silent skip by the single hook.

        Args:
            host: The host to check.

        Returns:
            True if the host should be silently skipped.
        """
        return host.data.get(SILENT_SKIP_FLAG, False)

    def task_started(self, task: Task) -> None:
        """Record task start time and print header information."""
        if not self.workflow_start_time:
            self.workflow_start_time = datetime.now()
            with output_lock:
                print(
                    f"\n{Fore.GREEN}{Style.BRIGHT}Execution started at: "
                    f"{self.workflow_start_time.strftime('%H:%M:%S.%f')[:-3]}{Style.RESET_ALL}"
                )

        if self.total_hosts is None:
            self.total_hosts = len(task.nornir.inventory.hosts)

        self.task_count += 1
        # Print task header only once per task, not per host
        with output_lock:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}Running task: {task.name}{Style.RESET_ALL}")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Record start time for a specific task on a specific host."""
        if self._is_silent_skip(host):
            return

        start_time = datetime.now()
        with output_lock:
            self.start_times[(task.name, host)] = start_time
        self.task_executions += 1

    def task_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        """Process task completion and print results for a specific host.

        Silent-skip flag cleanup is owned by SingleHook.task_completed,
        not this processor. We only check the flag to skip output/stats.
        """
        if self._is_silent_skip(host):
            return

        pause_key = (task.name, host.name)
        held_by_pause = pause_key in self._pause_lock_holders

        finish_time = datetime.now()

        # Determine status based on result attributes
        if getattr(result, "skipped", False):
            status = "Skipped"
            status_color = Fore.YELLOW
            self.skipped_executions += 1
        elif result.failed is False:
            status = "Success"
            status_color = Fore.GREEN
            self.successful_executions += 1
        else:
            status = "Failed"
            status_color = Fore.RED
            self.failed_executions += 1

        start_time = self.start_times.get((task.name, host), finish_time)
        start_str = start_time.strftime("%H:%M:%S.%f")[:-3]
        finish_str = finish_time.strftime("%H:%M:%S.%f")[:-3]

        # Calculate duration
        duration = finish_time - start_time
        duration_ms = duration.total_seconds() * 1000

        suppress_output = self._is_output_suppressed(task)
        output_section = self._format_task_output(result, suppress_output)

        if held_by_pause:
            self._print_task_result(
                task, host, status, status_color, start_str, finish_str, duration_ms, output_section
            )
            self._pause_lock_holders.discard(pause_key)
            output_lock.release()
        else:
            with output_lock:
                self._print_task_result(
                    task, host, status, status_color, start_str, finish_str, duration_ms, output_section
                )

    def _print_task_result(
        self,
        task: Task,
        host: Host,
        status: str,
        status_color: str,
        start_str: str,
        finish_str: str,
        duration_ms: float,
        output_section: str,
    ) -> None:
        """Print the formatted task result block.

        Args:
            task: The Nornir task.
            host: The host the task ran on.
            status: Status string (Success/Failed/Skipped).
            status_color: Colorama color for the status.
            start_str: Formatted start time string.
            finish_str: Formatted finish time string.
            duration_ms: Duration in milliseconds.
            output_section: Pre-formatted output section string.
        """
        print(f"{Fore.WHITE}{'-' * 80}")
        print(
            f"{Style.BRIGHT}{Fore.CYAN}Task: {task.name} "
            f"{Fore.WHITE}| {Fore.YELLOW}Host: {host} "
            f"{Fore.WHITE}| {Fore.MAGENTA}Hostname: {task.host.hostname or 'N/A'} "
            f"{Fore.WHITE}| {status_color}Status: {status}"
        )
        print(f"{Fore.BLUE}{start_str} - {finish_str} ({duration_ms:.0f}ms)")

        if output_section:
            print(output_section)

        print(f"{Fore.WHITE}{'-' * 80}")

        if (task.name, host) in self.start_times:
            del self.start_times[(task.name, host)]

    def _cleanup_pause_lock_holders(self, task_name: str) -> None:
        """Remove any orphaned pause lock entries for the given task and release the lock.

        Under normal operation, task_instance_completed handles cleanup per host.
        This method acts as a safety net: if any (task_name, host_name) entries
        survive to task_completed/task_failed (e.g. due to a framework-level error
        that prevented task_instance_completed from firing), we discard them here
        and release the lock once per orphaned entry to avoid permanent deadlock.

        Args:
            task_name: Name of the task that just finished across all hosts.
        """
        orphaned = {key for key in self._pause_lock_holders if key[0] == task_name}
        for key in orphaned:
            self._pause_lock_holders.discard(key)
            try:
                output_lock.release()
            except RuntimeError:
                pass

    def task_instance_failed(self, task: Task, host: Host, result: Result) -> None:
        self.task_instance_completed(task, host, result)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        # Don't track subtasks for simplicity
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: Result) -> None:
        pass

    def subtask_instance_failed(self, task: Task, host: Host, result: Result) -> None:
        pass

    def task_completed(self, task: Task, result: Result) -> None:
        self.tasks_completed += 1
        self._cleanup_pause_lock_holders(task.name)

        # Only print summary at the end if this setting is enabled
        if self.print_summary_after_each_task:
            self.print_workflow_summary()

    def task_failed(self, task: Task, result: Result) -> None:
        """Handle task failure across all hosts and update statistics."""
        self.tasks_completed += 1
        self._cleanup_pause_lock_holders(task.name)

        # Only print summary at the end if this setting is enabled
        if self.print_summary_after_each_task:
            self.print_workflow_summary()

    def print_final_workflow_summary(self) -> None:
        """Print the final workflow summary when explicitly called at the end of all workflow tasks."""
        self.print_workflow_summary()

    def print_workflow_summary(self) -> None:
        """
        Generate and print a summary of the workflow execution with timing, statistics and success metrics.
        """
        if not self.workflow_start_time:
            return

        end_time = datetime.now()
        duration = end_time - self.workflow_start_time
        duration_ms = duration.total_seconds() * 1000

        success_percent = (
            (self.successful_executions / self.task_executions * 100) if self.task_executions > 0 else 0
        )
        failure_percent = (
            (self.failed_executions / self.task_executions * 100) if self.task_executions > 0 else 0
        )
        skipped_percent = (
            (self.skipped_executions / self.task_executions * 100) if self.task_executions > 0 else 0
        )

        # Create a visual progress bar
        bar_length = 40
        success_bars = int(bar_length * success_percent / 100)
        failure_bars = int(bar_length * failure_percent / 100)
        skipped_bars = int(bar_length * skipped_percent / 100)

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
            if self.skipped_executions > 0:
                print(
                    f"  {Fore.YELLOW}Skipped:     {Style.BRIGHT}"
                    f"{self.skipped_executions} ({skipped_percent:.1f}%)"
                )
            print()

            # VISUAL GREEN/RED STATUS BAR
            bar = (
                f"{Back.GREEN}{' ' * success_bars}"
                f"{Back.RED}{' ' * failure_bars}"
                f"{Back.YELLOW}{' ' * skipped_bars}"
                f"{Style.RESET_ALL}"
            )
            print(f"  {bar}")
            print()