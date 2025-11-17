# ruff: noqa: PERF203

import logging
from typing import Any, TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Result, Task

from nornflow.hooks import Hook
from nornflow.hooks.exceptions import HookValidationError

if TYPE_CHECKING:
    from nornflow.models import TaskModel

logger = logging.getLogger(__name__)


class SetToHook(Hook):
    """
    Store task execution results as runtime variables with optional data extraction.

    Captures task results and stores them in NornFlow's runtime variable system.
    Supports both simple variable storage and selective data extraction from results.

    Usage modes:
    1. Simple: set_to: "var_name" - stores complete result object
    2. Extraction: set_to: {var_name: "extraction_path"} - extracts specific data

    For extraction paths, directly reference the keys in the result data:
    - "vendor" - gets vendor from the result dict
    - "hostname" - gets hostname from the result dict
    - "environment.cpu.usage" - nested dict access
    - "var_list[2]" - access indexes in lists
    - "dict.nested_list[1].another_dict.another_list[10]" - any combination of nested structures
    - Special attributes from Result object:
      - "_failed" - gets the failed boolean
      - "_changed" - gets the changed boolean
      - "_result" - gets the entire result data dict

    Examples:
        # Store complete result
        set_to: "device_facts"

        # Extract specific data (NO 'result.' prefix needed!)
        set_to:
          device_hostname: "hostname"
          device_vendor: "vendor"
          cpu_usage: "environment.cpu.0.%usage"
          task_failed: "_failed"

    Attributes:
        hook_name: "set_to"
        run_once_per_task: False (executes per host)
    """

    hook_name = "set_to"
    run_once_per_task = False

    def execute_hook_validations(self, task_model: "TaskModel") -> None:
        """
        Validate hook configuration and task compatibility before execution.

        Ensures the hook's value is properly configured and compatible with the
        associated task. Raises HookValidationError for invalid setups to prevent
        runtime failures.

        Args:
            task_model: The task model to validate against, including its name and config.

        Raises:
            HookValidationError: If validation fails, with details on the specific issue.
        """
        invalid_tasks = {"set", "echo", "set_to"}

        if task_model.name in invalid_tasks:
            raise HookValidationError(
                "SetToHook",
                [
                    (
                        "task_compatibility",
                        f"Hook 'SetToHook' cannot be used with task '{task_model.name}'. "
                        f"Incompatible tasks: {invalid_tasks}",
                    )
                ],
            )

        if self.value is None:
            raise HookValidationError(
                "SetToHook",
                [
                    (
                        "value_required",
                        "set_to hook requires a value (variable name or extraction specification)",
                    )
                ],
            )

        if isinstance(self.value, str):
            if not self.value.strip():
                raise HookValidationError(
                    "SetToHook", [("empty_variable_name", "Variable name cannot be empty")]
                )
        elif isinstance(self.value, dict):
            if not self.value:
                raise HookValidationError(
                    "SetToHook",
                    [("empty_extraction_spec", "Extraction specification cannot be empty")],
                )

            for var_name, extraction_path in self.value.items():
                if not isinstance(var_name, str) or not var_name.strip():
                    raise HookValidationError(
                        "SetToHook",
                        [
                            (
                                "invalid_variable_name",
                                f"Variable name must be a non-empty string, got: {var_name}",
                            )
                        ],
                    )

                if not isinstance(extraction_path, str) or not extraction_path.strip():
                    raise HookValidationError(
                        "SetToHook",
                        [
                            (
                                "invalid_extraction_path",
                                f"Extraction path for '{var_name}' must be a non-empty string",
                            )
                        ],
                    )
        else:
            raise HookValidationError(
                "SetToHook",
                [
                    (
                        "invalid_value_type",
                        f"set_to value must be a string or dict, got {type(self.value).__name__}",
                    )
                ],
            )

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """
        Process task results and store them as runtime variables for the host.

        Extracts data from the task's MultiResult based on the hook's configuration
        and stores it in the runtime variable manager. Handles both simple storage
        and complex extraction paths. Logs warnings/errors for missing components
        or extraction failures.

        Args:
            task: The completed task instance.
            host: The host for which the task was executed.
            result: The MultiResult containing outcomes for all hosts.

        Raises:
            Exception: Propagates any unhandled errors during processing.
        """
        if self.value is None or result is None:
            return

        if result.failed:
            return

        vars_manager = self.context.get("vars_manager")
        if not vars_manager:
            logger.warning(f"No vars_manager available for set_to hook on host '{host.name}'")
            return

        try:
            host_result = None
            for individual_result in result:
                if individual_result.host.name == host.name:
                    host_result = individual_result
                    break

            if host_result is None:
                logger.error(f"Could not find result for host '{host.name}' in MultiResult")
                return

            if hasattr(host_result, "skipped") and host_result.skipped:
                logger.debug(f"Host {host.name} was skipped by predicate, not setting variables")
                return

            if isinstance(self.value, str):
                vars_manager.set_runtime_variable(self.value, host_result.result, host.name)
                logger.debug(f"Stored result in variable '{self.value}' for host '{host.name}'")
            else:
                for var_name, extraction_path in self.value.items():
                    try:
                        extracted_value = self._extract_data_from_result(host_result, extraction_path)
                        vars_manager.set_runtime_variable(var_name, extracted_value, host.name)
                        logger.debug(
                            f"Extracted '{extraction_path}' and stored as '{var_name}' "
                            f"for host '{host.name}'"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to extract '{extraction_path}' for variable '{var_name}' "
                            f"on host '{host.name}': {e}"
                        )
        except Exception as e:
            logger.error(f"Error in set_to hook for host '{host.name}': {e}")
            raise

    def _extract_data_from_result(self, result: Result, extraction_path: str) -> Any:
        """
        Extract data from Result object using dotted notation and bracket indexing.

        Special prefixes:
        - "_failed" - returns result.failed
        - "_changed" - returns result.changed
        - "_result" - returns the entire result.result dict
        - Otherwise, extracts from result.result dict

        Args:
            result: The Result object to extract from
            extraction_path: The path specification

        Returns:
            The extracted data

        Raises:
            HookValidationError: If extraction fails
        """
        try:
            current_obj = self._handle_special_prefixes(result, extraction_path)
            if current_obj is not None:
                return current_obj

            current_obj = result.result

            if current_obj is None:
                raise HookValidationError(
                    "SetToHook",
                    [("null_result", f"Task result is None for extraction path '{extraction_path}'")],
                )

            segments = self._parse_extraction_path(extraction_path)
            return self._extract_from_segments(current_obj, segments, extraction_path)

        except HookValidationError:
            raise
        except Exception as e:
            raise HookValidationError(
                "SetToHook", [("extraction_error", f"Failed to extract '{extraction_path}': {e}")]
            ) from e

    def _handle_special_prefixes(self, result: Result, extraction_path: str) -> Any | None:
        """Handle special extraction path prefixes."""
        if extraction_path == "_failed":
            return result.failed
        if extraction_path == "_changed":
            return result.changed
        if extraction_path == "_result":
            return result.result
        return None

    def _extract_from_segments(
        self, current_obj: Any, segments: list[dict[str, str]], extraction_path: str
    ) -> Any:
        """Extract data by iterating through path segments."""
        for segment in segments:
            if segment["type"] == "key":
                current_obj = self._handle_key_segment(current_obj, segment["value"], extraction_path)
            elif segment["type"] == "index":
                current_obj = self._handle_index_segment(current_obj, segment["value"], extraction_path)
        return current_obj

    def _handle_key_segment(self, current_obj: Any, key: str, extraction_path: str) -> Any:
        """Handle key access for dict objects."""
        if not isinstance(current_obj, dict):
            available = self._get_available_keys(current_obj)
            raise HookValidationError(
                "SetToHook",
                [
                    (
                        "extraction_key_error",
                        f"Cannot access key '{key}' on non-dict object in path '{extraction_path}'. "
                        f"Object type: {type(current_obj).__name__}. Available: {available}",
                    )
                ],
            )

        if key in current_obj:
            return current_obj[key]

        if key.isdigit() and int(key) in current_obj:
            return current_obj[int(key)]

        available = self._get_available_keys(current_obj)
        raise HookValidationError(
            "SetToHook",
            [
                (
                    "extraction_key_error",
                    f"Key '{key}' not found in extraction path '{extraction_path}'. "
                    f"Available: {available}",
                )
            ],
        )

    def _handle_index_segment(self, current_obj: Any, index_str: str, extraction_path: str) -> Any:
        """Handle index access for lists, tuples, or dicts."""
        try:
            index = int(index_str)
            return current_obj[index]
        except (IndexError, TypeError, KeyError) as e:
            try:
                return current_obj[index_str]
            except Exception:
                length = len(current_obj) if hasattr(current_obj, "__len__") else "unknown"
                raise HookValidationError(
                    "SetToHook",
                    [
                        (
                            "extraction_index_error",
                            f"Index [{index_str}] not accessible in extraction path "
                            f"'{extraction_path}'. Length: {length}",
                        )
                    ],
                ) from e

    def _parse_extraction_path(self, path: str) -> list[dict[str, str]]:
        """
        Parse an extraction path into key and index segments.

        Breaks down a dotted/bracketed path string into a list of dictionaries,
        each representing either a 'key' (for dict access) or 'index' (for list/dict access).
        Handles nested structures by alternating between keys and indices.

        Args:
            path: The extraction path string to parse (e.g., "dict.key[0].nested").

        Returns:
            A list of segment dictionaries, each with 'type' ('key' or 'index')
            and 'value' (the segment string).

        Examples:
            - "hostname" -> [{'type': 'key', 'value': 'hostname'}]
            - "interfaces[0]" -> [
                    {'type': 'key', 'value': 'interfaces'},
                    {'type': 'index', 'value': '0'}
                ]
            - "dict.nested_list[1].another_dict" -> [
                    {'type': 'key', 'value': 'dict'},
                    {'type': 'key', 'value': 'nested_list'},
                    {'type': 'index', 'value': '1'},
                    {'type': 'key', 'value': 'another_dict'}
                ]
        """
        segments = []
        current_segment = ""
        in_brackets = False

        for char in path:
            if char == "[":
                if current_segment:
                    segments.append({"type": "key", "value": current_segment})
                    current_segment = ""
                in_brackets = True
            elif char == "]":
                if in_brackets and current_segment:
                    segments.append({"type": "index", "value": current_segment})
                    current_segment = ""
                in_brackets = False
            elif char == "." and not in_brackets:
                if current_segment:
                    segments.append({"type": "key", "value": current_segment})
                    current_segment = ""
            else:
                current_segment += char

        if current_segment:
            segments.append({"type": "key", "value": current_segment})

        return segments

    def _get_available_keys(self, obj: Any) -> str:
        """Generate a string of available keys or attributes for error reporting.

        Inspects the given object and returns a comma-separated string of its
        accessible keys (for dicts) or attributes (for objects), limited to the
        first 10 for brevity. Used in error messages to help diagnose extraction failures.

        Args:
            obj: The object to inspect (dict, list, or arbitrary object).

        Returns:
            A formatted string of available keys/attributes, truncated if over 10.
        """
        available = []

        if isinstance(obj, dict):
            available.extend(str(k) for k in obj)
        elif hasattr(obj, "__dict__"):
            available.extend([attr for attr in dir(obj) if not attr.startswith("_")])

        return ", ".join(sorted(available)[:10]) + ("..." if len(available) > 10 else "")  # noqa: PLR2004
