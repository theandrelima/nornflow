
from typing import Any, NoReturn, TYPE_CHECKING

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Result, Task

from nornflow.hooks import Hook
from nornflow.hooks.exceptions import HookError, HookValidationError
from nornflow.logger import logger

if TYPE_CHECKING:
    from nornflow.models import TaskModel

_HOOK_CLASS = "StoreAsHook"
_INCOMPATIBLE_TASKS = frozenset({"set", "echo", "store_as"})


def _raise_validation(
    error_code: str,
    message: str,
    *,
    cause: BaseException | None = None,
) -> NoReturn:
    """Raise HookValidationError for StoreAsHook with a single coded error.

    Args:
        error_code: Short identifier for the validation failure.
        message: Human-readable error detail.
        cause: Optional exception to chain as '__cause__'.

    Raises:
        HookValidationError: Always raised; this function never returns.
    """
    exc = HookValidationError(_HOOK_CLASS, [(error_code, message)])
    if cause is not None:
        raise exc from cause
    raise exc


class StoreAsHook(Hook):
    """
    Store task execution results as runtime variables with optional data extraction.

    Captures task results and stores them in NornFlow's runtime variable system.
    Supports simple variable storage (task's returned 'Result.result') and selective extraction.

    Usage modes:
    1. Simple: store_as: "var_name" - stores the entire 'Result.result' in 'var_name'
    2. Extraction: store_as: {var_name: "dotted.extraction.path"} - extracts specific nested data at 'dotted.extraction.path' into 'var_name'

    Extraction root (first segment — the part before the first '.'):
    - If it is a top-level attribute of Nornir's 'Result' (e.g. 'failed', 'changed', 'result'),
      extraction starts on the 'Result' object at that attribute.
    - Otherwise extraction starts at 'Result.result' and the full path applies (including that
      first segment as a key into the task return value).

    If extraction fails at any step (missing segment, bad index, null 'Result.result' when required),
    the hook raises HookValidationError. That exception propagates uncaught and stops the workflow
    at that point — it is not governed by failure strategy. Use valid, fully qualified paths.

    To avoid ambiguity when a name exists on both 'Result' and inside 'Result.result', use a
    fully qualified path from a top-level 'Result' attribute (e.g. 'result.vendor' for the
    task return value, 'failed' for 'Result.failed').

    For data in 'Result.result' (shorthand — first segment not on 'Result'):
    - "vendor" - gets vendor from the task return value
    - "hostname" - gets hostname from the task return value
    - "environment.cpu.usage" - nested dict access
    - "var_list[2]" - access indexes in lists
    - "dict.nested_list[1].another_dict.another_list[10]" - any combination of nested structures
    - Wrapper attributes: "failed", "changed", "result", etc...

    Examples:
        # Shorthand for store_as: {device_facts: "result"} — stores 'Result.result' in 'device_facts'
        store_as: "device_facts"

        store_as:
          # Shorthand: 'hostname' is not on Result → lookup starts at 'Result.result'
          device_hostname: "hostname"

          # 'Result.result' key 'vendor' (explicit via top-level 'result' attribute)
          device_vendor: "result.vendor"

          # nested value inside 'Result.result'. Here again, 'environment' is not on Result → lookup starts at 'Result.result'
          cpu_usage: "environment.cpu.0.%usage"

          # 'Result.failed' (first segment is a top-level Result attribute)
          task_failed: "failed"

    Attributes:
        hook_name: "store_as"
        run_once_per_task: False (executes per host)
    """  # noqa: E501

    hook_name = "store_as"
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
        invalid_tasks = _INCOMPATIBLE_TASKS

        if task_model.name in invalid_tasks:
            _raise_validation(
                "task_compatibility",
                f"Hook '{_HOOK_CLASS}' cannot be used with task '{task_model.name}'. "
                f"Incompatible tasks: {invalid_tasks}",
            )

        if self.value is None:
            _raise_validation(
                "value_required",
                "store_as hook requires a value (variable name or extraction specification)",
            )

        if isinstance(self.value, str):
            if not self.value.strip():
                _raise_validation("empty_variable_name", "Variable name cannot be empty")
        elif isinstance(self.value, dict):
            if not self.value:
                _raise_validation(
                    "empty_extraction_spec", "Extraction specification cannot be empty"
                )

            for var_name, extraction_path in self.value.items():
                if not isinstance(var_name, str) or not var_name.strip():
                    _raise_validation(
                        "invalid_variable_name",
                        f"Variable name must be a non-empty string, got: {var_name}",
                    )

                if not isinstance(extraction_path, str) or not extraction_path.strip():
                    _raise_validation(
                        "invalid_extraction_path",
                        f"Extraction path for '{var_name}' must be a non-empty string",
                    )
        else:
            _raise_validation(
                "invalid_value_type",
                f"store_as value must be a string or dict, got {type(self.value).__name__}",
            )

    def task_instance_completed(  # noqa: PLR0912
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
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
            HookError: If vars_manager is missing or no Result matches host in MultiResult.
            HookValidationError: If extraction fails.
            Exception: Propagates any unhandled errors during processing.
        """
        if self.value is None or result is None:
            return

        vars_manager = self.context.get("vars_manager")
        if not vars_manager:
            raise HookError("store_as: Variables manager not available in hook context.")

        try:
            # result is a per-host MultiResult (main task + subtasks), not all inventory hosts
            host_result = None
            for individual_result in result:
                if individual_result.host.name == host.name:
                    host_result = individual_result
                    break

            # Nornir inserts a Result before this callback — empty/no match should not happen in practice.
            # if this ever triggers, suspect something is deeply wrong with execution context.
            if host_result is None:
                raise HookError(
                    f"store_as: No Result for host '{host.name}' in MultiResult"
                )

            if hasattr(host_result, "skipped") and host_result.skipped:
                logger.debug(f"Host {host.name} was skipped by predicate, not setting variables")
                return

            # Simple mode: store_as: "var_name" — store Result.result directly (no path parsing).
            # Equivalent to store_as: {var_name: "result"} but skips extraction machinery.
            if isinstance(self.value, str):
                vars_manager.set_runtime_variable(self.value, host_result.result, host.name)
                logger.debug(f"Stored result in variable '{self.value}' for host '{host.name}'")

            # Extraction mode: store_as: {var_name: "dotted.path", ...} — one or more paths.
            else:
                # (var_name, extraction_path) pairs whose first segment is a top-level
                # attribute on Nornir's Result object (not inside Result.result)
                # e.g. task_failed: "failed", full_return: "result", vendor: "result.vendor"
                nornir_result_top_level_attr_items = []

                # (var_name, extraction_path) pairs whose first segment is not on Result —
                # shorthand paths; navigation starts at Result.result
                # e.g. device_hostname: "hostname", cpu_usage: "environment.cpu.0.%usage"
                shorthand_items = []

                for var_name, extraction_path in self.value.items():
                    segments = self._parse_extraction_path(extraction_path)
                    if (
                        segments
                        and segments[0]["type"] == "key"
                        and hasattr(host_result, segments[0]["value"])
                    ):
                        nornir_result_top_level_attr_items.append((var_name, extraction_path))
                    else:
                        shorthand_items.append((var_name, extraction_path))

                for var_name, extraction_path in nornir_result_top_level_attr_items + shorthand_items:
                    extracted_value = self._extract_data_from_result(host_result, extraction_path)
                    vars_manager.set_runtime_variable(var_name, extracted_value, host.name)
                    logger.debug(
                        f"Extracted '{extraction_path}' and stored as '{var_name}' "
                        f"for host '{host.name}'"
                    )

        except Exception as e:
            logger.exception(f"Error in store_as hook for host '{host.name}': {e}")
            raise

    def _extract_data_from_result(self, result: Result, extraction_path: str) -> Any:
        """
        Extract data from Result using hybrid root navigation and dotted/bracket paths.

        If the first path segment is a 'Result' attribute, navigation starts there;
        otherwise it starts at 'Result.result' (when the first segment is not on 'Result').

        Args:
            result: The Result object to extract from.
            extraction_path: The path specification.

        Returns:
            The extracted data.

        Raises:
            HookValidationError: If extraction fails.
        """
        try:
            segments = self._parse_extraction_path(extraction_path)
            if not segments:
                _raise_validation(
                    "invalid_extraction_path", f"Extraction path '{extraction_path}' is empty"
                )

            first = segments[0]
            if first["type"] != "key":
                _raise_validation(
                    "invalid_extraction_path",
                    f"Extraction path '{extraction_path}' must start with a key segment",
                )

            name = first["value"]
            rest = segments[1:]

            # First segment names a top-level Result attribute — start there (e.g. "failed", "result.vendor").
            if hasattr(result, name):
                return self._extract_from_segments(getattr(result, name), rest, extraction_path)

            # Shorthand path into Result.result, but the task returned nothing to traverse.
            if result.result is None:
                _raise_validation(
                    "null_result", f"Task result is None for extraction path '{extraction_path}'"
                )

            # Shorthand: first segment is not on Result — traverse Result.result with the full path.
            return self._extract_from_segments(result.result, segments, extraction_path)

        except HookValidationError:
            raise
        except Exception as e:
            _raise_validation(
                "extraction_error",
                f"Failed to extract '{extraction_path}': {e}",
                cause=e,
            )

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
        """Handle key access for dicts and object attributes."""
        if isinstance(current_obj, dict):
            if key in current_obj:
                return current_obj[key]

            if key.isdigit() and int(key) in current_obj:
                return current_obj[int(key)]
        elif hasattr(current_obj, key):
            return getattr(current_obj, key)

        available = self._get_available_keys(current_obj)
        _raise_validation(
            "extraction_key_error",
            f"Key '{key}' not found in extraction path '{extraction_path}'. "
            f"Object type: {type(current_obj).__name__}. Available: {available}",
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
                _raise_validation(
                    "extraction_index_error",
                    f"Index [{index_str}] not accessible in extraction path "
                    f"'{extraction_path}'. Length: {length}",
                    cause=e,
                )

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
