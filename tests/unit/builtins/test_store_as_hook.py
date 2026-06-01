from unittest.mock import MagicMock, call

import pytest
from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Result, Task

from nornflow.builtins.hooks import StoreAsHook
from nornflow.hooks.exceptions import HookError, HookValidationError


def _make_host(name: str = "router1") -> Host:
    """Create a minimal Nornir Host for store_as tests."""
    return Host(name=name, hostname=name, data={})


def _multiresult_for(host: Host, host_result: Result, task_name: str = "test_task") -> MultiResult:
    """Build a per-host MultiResult containing a single host Result."""
    multi = MultiResult(task_name)
    multi.append(host_result)
    return multi


def _run_store_as(
    hook_value,
    host: Host,
    host_result: Result,
    vars_manager: MagicMock | None = None,
) -> tuple[StoreAsHook, MagicMock]:
    """Run task_instance_completed with vars_manager wired into hook context."""
    hook = StoreAsHook(hook_value)
    manager = vars_manager or MagicMock()
    hook._current_context = {"vars_manager": manager}
    hook.task_instance_completed(
        MagicMock(spec=Task),
        host,
        _multiresult_for(host, host_result),
    )
    return hook, manager


class TestStoreAsHook:
    """Test suite for StoreAsHook."""

    def test_hook_name_registration(self):
        """Test that hook has correct name for registration."""
        assert StoreAsHook.hook_name == "store_as"

    def test_run_once_per_task_flag(self):
        """Test that hook runs per host, not once per task."""
        assert StoreAsHook.run_once_per_task is False

    def test_init_with_value(self):
        """Test hook initialization with a variable name."""
        hook = StoreAsHook("my_variable")
        assert hook.value == "my_variable"

    def test_init_without_value(self):
        """Test hook initialization without a value."""
        hook = StoreAsHook()
        assert hook.value is None

    def test_execute_hook_validations_valid_task(self):
        """Test validation passes for compatible tasks."""
        hook = StoreAsHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "ping"

        # Should not raise
        hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_invalid_set_task(self):
        """Test validation fails for 'set' task."""
        hook = StoreAsHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "set"

        with pytest.raises(HookValidationError, match="Hook 'StoreAsHook' cannot be used with task 'set'"):
            hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_invalid_echo_task(self):
        """Test validation fails for 'echo' task."""
        hook = StoreAsHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "echo"

        with pytest.raises(HookValidationError, match="Hook 'StoreAsHook' cannot be used with task 'echo'"):
            hook.execute_hook_validations(mock_task_model)

    def test_execute_hook_validations_invalid_store_as_task(self):
        """Test validation fails for 'store_as' task."""
        hook = StoreAsHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "store_as"

        with pytest.raises(HookValidationError, match="Hook 'StoreAsHook' cannot be used with task 'store_as'"):
            hook.execute_hook_validations(mock_task_model)

    def test_task_instance_completed_stores_result(self):
        """Test that task_instance_completed stores result in runtime variable."""
        hook = StoreAsHook("test_variable")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        
        # Create a MultiResult with a result for the host
        mock_result = MultiResult("test_task")
        host_result = Result(host=mock_host, result="test_data")
        mock_result.append(host_result)
        
        mock_vars_manager = MagicMock()
        
        # Set up the context
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_called_once_with("test_variable", "test_data", "router1")

    def test_task_instance_completed_no_value_does_nothing(self):
        """Test that task_instance_completed does nothing when value is None."""
        hook = StoreAsHook(None)
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_result = MagicMock(spec=MultiResult)
        mock_vars_manager = MagicMock()
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_not_called()

    def test_task_instance_completed_no_result_does_nothing(self):
        """Test that task_instance_completed does nothing when result is None."""
        hook = StoreAsHook("test_variable")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_vars_manager = MagicMock()
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, None)

        mock_vars_manager.set_runtime_variable.assert_not_called()

    def test_task_instance_completed_no_vars_manager_raises(self):
        """Test that missing vars_manager raises HookError."""
        hook = StoreAsHook("test_variable")

        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_result = MagicMock(spec=MultiResult)

        hook._current_context = {}

        with pytest.raises(HookError, match="Variables manager not available"):
            hook.task_instance_completed(mock_task, mock_host, mock_result)

    def test_task_instance_completed_no_host_result_raises(self):
        """Test that empty per-host MultiResult raises HookError."""
        hook = StoreAsHook("test_variable")

        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_result = MultiResult("test_task")

        mock_vars_manager = MagicMock()
        hook._current_context = {"vars_manager": mock_vars_manager}

        with pytest.raises(HookError, match="No Result for host 'router1'"):
            hook.task_instance_completed(mock_task, mock_host, mock_result)

    def test_task_instance_completed_no_context_raises(self):
        """Test that missing hook context raises HookError."""
        hook = StoreAsHook("test_variable")

        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "router1"
        mock_result = MagicMock(spec=MultiResult)

        hook._current_context = None

        with pytest.raises(HookError, match="Variables manager not available"):
            hook.task_instance_completed(mock_task, mock_host, mock_result)

    def test_context_property_returns_empty_when_no_context(self):
        """Test context property returns empty dict when no context is set."""
        hook = StoreAsHook("test_variable")
        
        context = hook.context
        assert context == {}

    def test_task_instance_completed_with_complex_result(self):
        """Test storing complex result objects."""
        hook = StoreAsHook("complex_var")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "switch1"
        
        # Create a more realistic MultiResult
        mock_result = MultiResult("test_task")
        host_result = Result(host=mock_host, result={"config": "data"}, changed=True)
        mock_result.append(host_result)
        
        mock_vars_manager = MagicMock()
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_called_once_with("complex_var", {"config": "data"}, "switch1")

    def test_other_processor_methods_do_nothing(self):
        """Test that other processor methods have no implementation."""
        hook = StoreAsHook("test_var")
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()

        # These should not raise any exceptions
        hook.task_started(mock_task)
        hook.task_completed(mock_task, mock_result)
        hook.task_instance_started(mock_task, mock_host)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)

    def test_should_execute_always_returns_true(self):
        """Test that hook executes for every host (run_once_per_task=False)."""
        hook = StoreAsHook("test_var")
        mock_task = MagicMock()

        # Should always return True since run_once_per_task is False
        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True

    def test_task_instance_completed_handles_string_host_name(self):
        """Test that hook works correctly with string host names."""
        hook = StoreAsHook("host_result")
        
        mock_task = MagicMock(spec=Task)
        mock_host = MagicMock(spec=Host)
        mock_host.name = "complex-host-name.domain.com"
        
        # Create a MultiResult with a result for the host
        mock_result = MultiResult("test_task")
        host_result = Result(host=mock_host, result="host_data")
        mock_result.append(host_result)
        
        mock_vars_manager = MagicMock()
        
        hook._current_context = {"vars_manager": mock_vars_manager}

        hook.task_instance_completed(mock_task, mock_host, mock_result)

        mock_vars_manager.set_runtime_variable.assert_called_once_with(
            "host_result", "host_data", "complex-host-name.domain.com"
        )

    def test_execute_hook_validations_error_message_includes_incompatible_tasks(self):
        """Test that validation error message lists all incompatible tasks."""
        hook = StoreAsHook("var_name")
        mock_task_model = MagicMock()
        mock_task_model.name = "set"

        with pytest.raises(HookValidationError) as exc_info:
            hook.execute_hook_validations(mock_task_model)

        error_message = str(exc_info.value)
        assert "set" in error_message
        assert "echo" in error_message
        assert "store_as" in error_message

    def test_failed_task_stores_failed_flag_true(self):
        """Failed task stores Result.failed via wrapper path."""
        host = _make_host()
        host_result = Result(host=host, result=None, failed=True)
        _, manager = _run_store_as({"flag": "failed"}, host, host_result)

        manager.set_runtime_variable.assert_called_once_with("flag", True, host.name)

    def test_successful_task_stores_failed_flag_false(self):
        """Successful task stores Result.failed as false."""
        host = _make_host()
        host_result = Result(host=host, result={"ok": True}, failed=False)
        _, manager = _run_store_as({"flag": "failed"}, host, host_result)

        manager.set_runtime_variable.assert_called_once_with("flag", False, host.name)

    def test_multi_host_failure_is_per_host(self):
        """Each host gets its own stored failed flag from its Result."""
        host_failed = _make_host("failed-host")
        host_ok = _make_host("ok-host")
        manager_failed = MagicMock()
        manager_ok = MagicMock()

        _run_store_as(
            {"flag": "failed"},
            host_failed,
            Result(host=host_failed, result=None, failed=True),
            manager_failed,
        )
        _run_store_as(
            {"flag": "failed"},
            host_ok,
            Result(host=host_ok, result={"ok": True}, failed=False),
            manager_ok,
        )

        manager_failed.set_runtime_variable.assert_called_once_with("flag", True, "failed-host")
        manager_ok.set_runtime_variable.assert_called_once_with("flag", False, "ok-host")

    def test_failed_task_stores_changed_and_result_paths(self):
        """Failed task still stores wrapper paths changed and result."""
        host = _make_host()
        payload = {"partial": True}
        host_result = Result(host=host, result=payload, failed=True, changed=True)
        _, manager = _run_store_as({"was_changed": "changed", "payload": "result"}, host, host_result)

        assert manager.set_runtime_variable.call_args_list == [
            call("was_changed", True, host.name),
            call("payload", payload, host.name),
        ]

    def test_failed_task_stores_simple_mode_on_failure(self):
        """Simple mode stores Result.result even when the task failed."""
        host = _make_host()
        payload = {"partial": True}
        host_result = Result(host=host, result=payload, failed=True)
        _, manager = _run_store_as("capture_var", host, host_result)

        manager.set_runtime_variable.assert_called_once_with("capture_var", payload, host.name)

    def test_failed_task_stores_simple_mode_none_result(self):
        """Simple mode stores None when failed task has Result.result is None."""
        host = _make_host()
        host_result = Result(host=host, result=None, failed=True)
        _, manager = _run_store_as("capture_var", host, host_result)

        manager.set_runtime_variable.assert_called_once_with("capture_var", None, host.name)

    @pytest.mark.parametrize(
        "task_result",
        [
            "show run output...",
            {"output": "timeout", "vendor": "cisco"},
            None,
        ],
    )
    def test_simple_mode_equivalent_to_result_path(self, task_result):
        """Simple mode stores the same value as extraction path result."""
        host = _make_host()
        host_result = Result(host=host, result=task_result, failed=task_result is None)

        manager_simple = MagicMock()
        _run_store_as("running_config", host, host_result, manager_simple)

        manager_path = MagicMock()
        _run_store_as({"running_config": "result"}, host, host_result, manager_path)

        assert manager_simple.set_runtime_variable.call_args == manager_path.set_runtime_variable.call_args

    def test_failed_task_payload_shorthand_stores_when_present(self):
        """Payload shorthand works on failed tasks when the key exists."""
        host = _make_host()
        host_result = Result(host=host, result={"output": "timeout"}, failed=True)
        _, manager = _run_store_as({"detail": "output"}, host, host_result)

        manager.set_runtime_variable.assert_called_once_with("detail", "timeout", host.name)

    def test_extraction_missing_key_raises(self):
        """Missing extraction key raises HookValidationError from task_instance_completed."""
        host = _make_host()
        host_result = Result(host=host, result={"vendor": "cisco"}, failed=False)
        hook = StoreAsHook({"bad": "missing_key"})
        manager = MagicMock()
        hook._current_context = {"vars_manager": manager}

        with pytest.raises(HookValidationError):
            hook.task_instance_completed(
                MagicMock(spec=Task),
                host,
                _multiresult_for(host, host_result),
            )

        manager.set_runtime_variable.assert_not_called()

    def test_extract_wrapper_attribute_name(self):
        """Path name reads Result.name when set on the Result object."""
        host = _make_host()
        host_result = Result(host=host, result={"ignored": True}, name="deploy")
        _, manager = _run_store_as({"task_name": "name"}, host, host_result)

        manager.set_runtime_variable.assert_called_once_with("task_name", "deploy", host.name)

    def test_extract_wrapper_attribute_severity_level(self):
        """Path severity_level reads Result.severity_level."""
        host = _make_host()
        host_result = Result(host=host, result={}, severity_level=20)
        _, manager = _run_store_as({"level": "severity_level"}, host, host_result)

        manager.set_runtime_variable.assert_called_once_with("level", 20, host.name)

    def test_extract_invalid_path_raises(self):
        """Unknown shorthand path raises HookValidationError."""
        host = _make_host()
        host_result = Result(host=host, result={}, failed=False)
        hook = StoreAsHook({"x": "this_key_definitely_does_not_exist"})
        manager = MagicMock()
        hook._current_context = {"vars_manager": manager}

        with pytest.raises(HookValidationError):
            hook.task_instance_completed(
                MagicMock(spec=Task),
                host,
                _multiresult_for(host, host_result),
            )

    def test_payload_shorthand_equals_result_dot_key(self):
        """Shorthand vendor and explicit result.vendor store the same value."""
        host = _make_host()
        host_result = Result(host=host, result={"vendor": "arista"})
        manager_shorthand = MagicMock()
        _run_store_as({"vendor_a": "vendor"}, host, host_result, manager_shorthand)

        manager_explicit = MagicMock()
        _run_store_as({"vendor_b": "result.vendor"}, host, host_result, manager_explicit)

        assert manager_shorthand.set_runtime_variable.call_args == call("vendor_a", "arista", host.name)
        assert manager_explicit.set_runtime_variable.call_args == call("vendor_b", "arista", host.name)

    def test_wrapper_wins_on_collision(self):
        """Bare vendor follows Result attribute; result.vendor follows payload key."""
        host = _make_host()
        host_result = Result(
            host=host,
            result={"vendor": "payload"},
            vendor="wrapper",
        )
        manager_bare = MagicMock()
        _run_store_as({"from_wrapper": "vendor"}, host, host_result, manager_bare)

        manager_explicit = MagicMock()
        _run_store_as({"from_payload": "result.vendor"}, host, host_result, manager_explicit)

        manager_bare.set_runtime_variable.assert_called_once_with("from_wrapper", "wrapper", host.name)
        manager_explicit.set_runtime_variable.assert_called_once_with("from_payload", "payload", host.name)

    def test_wrapper_paths_processed_before_payload_raises(self):
        """Wrapper path stores before shorthand path hard-fails (YAML order irrelevant)."""
        host = _make_host()
        host_result = Result(host=host, result=None, failed=True)
        hook = StoreAsHook({"bad": "missing_payload_key", "flag": "failed"})
        manager = MagicMock()
        hook._current_context = {"vars_manager": manager}

        with pytest.raises(HookValidationError):
            hook.task_instance_completed(
                MagicMock(spec=Task),
                host,
                _multiresult_for(host, host_result),
            )

        manager.set_runtime_variable.assert_called_once_with("flag", True, host.name)

    def test_failed_mixed_dict_stores_failed_before_payload_raises(self):
        """Alias: failed flag stored before bad payload path aborts."""
        self.test_wrapper_paths_processed_before_payload_raises()

    def test_failed_multiresult_does_not_block_successful_host(self):
        """Aggregate MultiResult.failed does not skip store_as for a successful host."""
        host_ok = _make_host("ok-host")
        host_failed = _make_host("failed-host")
        multi = MultiResult("test_task")
        multi.append(Result(host=host_ok, result="ok", failed=False))
        multi.append(Result(host=host_failed, result="err", failed=True))
        assert multi.failed is True

        hook = StoreAsHook("capture_var")
        manager = MagicMock()
        hook._current_context = {"vars_manager": manager}
        hook.task_instance_completed(MagicMock(spec=Task), host_ok, multi)

        manager.set_runtime_variable.assert_called_once_with("capture_var", "ok", "ok-host")

    def test_skipped_host_does_not_store_on_failure(self):
        """Skipped hosts do not store variables even when other paths would apply."""
        host = _make_host()
        host_result = Result(host=host, result={"output": "x"}, failed=True, skipped=True)
        _, manager = _run_store_as({"flag": "failed"}, host, host_result)

        manager.set_runtime_variable.assert_not_called()