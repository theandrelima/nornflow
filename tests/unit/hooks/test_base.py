# ruff: noqa: SLF001, T201
from unittest.mock import MagicMock

import pytest

from nornflow.hooks.base import Hook, HOOKS_CATALOG
from nornflow.hooks.exceptions import HookRegistrationError
import nornflow.builtins.hooks  # noqa: F401  # ensure builtin hooks are registered


class TestHook:
    """Test suite for base Hook class."""

    def test_init_with_value(self):
        """Test Hook initialization with a value."""
        hook = Hook("test_value")
        assert hook.value == "test_value"

    def test_init_without_value(self):
        """Test Hook initialization without a value."""
        hook = Hook()
        assert hook.value is None

    def test_execution_tracking(self):
        """Test that hooks track execution count."""
        hook = Hook()
        assert hook._execution_count == {}

    def test_current_context_initial(self):
        """Test that initial context is None."""
        hook = Hook()
        assert hook._current_context is None

    def test_should_execute_default(self):
        """Test should_execute returns True by default."""
        hook = Hook()
        hook.run_once_per_task = False
        mock_task = MagicMock()

        assert hook.should_execute(mock_task) is True
        assert hook.should_execute(mock_task) is True

    def test_should_execute_once_per_task(self):
        """Test should_execute with run_once_per_task flag."""
        hook = Hook()
        hook.run_once_per_task = True
        mock_task = MagicMock()

        mock_task_model = MagicMock()
        hook._current_context = {"task_model": mock_task_model}

        assert hook.should_execute(mock_task) is True

        assert hook.should_execute(mock_task) is False
        assert hook.should_execute(mock_task) is False

        mock_task2 = MagicMock()
        mock_task_model2 = MagicMock()
        hook._current_context = {"task_model": mock_task_model2}
        assert hook.should_execute(mock_task2) is True

    def test_get_context_empty(self):
        """Test context property returns empty dict when no context set."""
        hook = Hook()

        context = hook.context
        assert context == {}

    def test_get_context_with_current_context(self):
        """Test context property returns current context when set."""
        hook = Hook()
        hook._current_context = {"key": "value"}

        context = hook.context
        assert context == {"key": "value"}

    def test_processor_methods_are_optional(self):
        """Test that all processor methods have default implementations."""
        hook = Hook()
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()

        hook.task_started(mock_task)
        hook.task_completed(mock_task, mock_result)
        hook.task_instance_started(mock_task, mock_host)
        hook.task_instance_completed(mock_task, mock_host, mock_result)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)

    def test_execute_hook_validations_default(self):
        """Test that execute_hook_validations does nothing by default."""
        hook = Hook()
        mock_task_model = MagicMock()

        hook.execute_hook_validations(mock_task_model)

    def test_exception_handlers_default(self):
        """Test that exception_handlers is empty by default."""
        hook = Hook()
        assert hook.exception_handlers == {}

    def test_auto_registration(self):
        """Test that hooks with hook_name are automatically registered."""
        initial_registry_size = len(HOOKS_CATALOG)

        class TestAutoHook(Hook):
            hook_name = "test_auto_hook"

        assert "test_auto_hook" in HOOKS_CATALOG
        assert HOOKS_CATALOG.resolve("test_auto_hook") is TestAutoHook
        assert len(HOOKS_CATALOG) == initial_registry_size + 1

    def test_no_hook_name_raises_error(self):
        """Test that missing hook_name raises HookRegistrationError."""
        with pytest.raises(HookRegistrationError):
            class NoNameHook(Hook):
                pass

    def test_duplicate_registration_same_class(self):
        """Test that re-importing same class doesn't raise error."""
        class TestDuplicateHook(Hook):
            hook_name = "test_duplicate"

        assert "test_duplicate" in HOOKS_CATALOG
        assert HOOKS_CATALOG.resolve("test_duplicate") is TestDuplicateHook

    def test_duplicate_registration_same_namespace_last_write_wins(self):
        """Test that re-registering the same bare name in local namespace overrides."""
        class FirstHookLWW(Hook):
            hook_name = "conflict_hook_lww"

        assert HOOKS_CATALOG.resolve("conflict_hook_lww") is FirstHookLWW

        class SecondHookLWW(Hook):
            hook_name = "conflict_hook_lww"

        assert HOOKS_CATALOG.resolve("conflict_hook_lww") is SecondHookLWW

    def test_reusing_builtin_name_registers_qualified_local_copy(self):
        """Test that reusing a builtin hook name creates a separate local qualified entry."""
        from nornflow.builtins.hooks import SetToHook

        class FakeSetToHook(Hook):
            hook_name = "set_to"

        assert HOOKS_CATALOG.resolve("set_to") is SetToHook
        assert HOOKS_CATALOG.resolve("local.set_to") is FakeSetToHook

    def test_builtin_hooks_registered(self):
        """Test that built-in hooks are properly registered."""
        from nornflow.builtins.hooks import IfHook, SetToHook, ShushHook

        assert HOOKS_CATALOG.resolve("if") is IfHook
        assert HOOKS_CATALOG.resolve("set_to") is SetToHook
        assert HOOKS_CATALOG.resolve("shush") is ShushHook

    def test_user_hook_is_builtin_defaults_false(self):
        """Test that user-defined hooks get is_builtin=False in catalog sources."""
        class UserDefinedHook(Hook):
            hook_name = "user_defined_for_builtin_check"

        assert HOOKS_CATALOG.sources["local.user_defined_for_builtin_check"]["is_builtin"] is False

    def test_builtin_hooks_have_is_builtin_in_sources(self):
        """Test that builtin hooks are marked is_builtin=True in HOOKS_CATALOG.sources."""
        for hook_name in ("if", "set_to", "shush", "single"):
            assert HOOKS_CATALOG.sources[f"nornflow.{hook_name}"]["is_builtin"] is True
