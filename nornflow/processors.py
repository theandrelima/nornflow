from nornir.core.task import Task, Result
from nornir.core.processor import Processor
from colorama import init, Fore, Style
from datetime import datetime

# Initialize colorama
init(autoreset=True)

class DefaultNornFlowProcessor(Processor):
    def task_started(self, task: Task) -> None:
        pass

    def task_instance_started(self, task: Task, host: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Fore.MAGENTA}{'-' * 80}")
        print(f"\n{Style.BRIGHT}{Fore.BLUE}Started: {timestamp}\n")

    def task_instance_completed(self, task: Task, host: str, result: Result) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Success" if result.failed is False else "Failed"
        status_color = Fore.GREEN if result.failed is False else Fore.RED
        print(f"{Style.BRIGHT}{Fore.CYAN}Task: {task.name} {Fore.WHITE}| {Fore.YELLOW}Host: {host} {Fore.WHITE}| {status_color}Status: {status}")
        print(f"{Fore.WHITE}Output:\n{result.result}")
        print(f"{Style.BRIGHT}{Fore.BLUE}\nFinished: {timestamp}")

        print(f"\n{Fore.MAGENTA}{'-' * 80}")

    def task_instance_failed(self, task: Task, host: str, result: Result) -> None:
        self.task_instance_completed(task, host, result)

    def subtask_instance_started(self, task: Task, host: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Style.BRIGHT}{Fore.BLUE}Subtask Started: {timestamp}\n")

    def subtask_instance_completed(self, task: Task, host: str, result: Result) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Success" if result.failed is False else "Failed"
        status_color = Fore.GREEN if result.failed is False else Fore.RED
        print(f"{Style.BRIGHT}{Fore.CYAN}Subtask: {task.name} {Fore.WHITE}| {Fore.YELLOW}Host: {host} {Fore.WHITE}| {status_color}Status: {status}")
        print(f"{Fore.WHITE}Output:\n{result.result}")
        print(f"{Style.BRIGHT}{Fore.BLUE}\nSubtask Finished: {timestamp}")

        print(f"\n{Fore.MAGENTA}{'-' * 80}")

    def subtask_instance_failed(self, task: Task, host: str, result: Result) -> None:
        self.subtask_instance_completed(task, host, result)

    def task_completed(self, task: Task, result: Result) -> None:
        pass

    def task_failed(self, task: Task, result: Result) -> None:
        pass
