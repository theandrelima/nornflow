from unittest.mock import MagicMock

import pytest

from nornflow.builtins.hooks import SetPrintOutputHook


class TestSetPrintOutputHook:
    """Test suite for SetPrintOutputHook."""

    def test_hook_name_registration(self):
        """Test that hook has correct name for registration."""
        assert SetPrintOutputHook.hook_name == "output"

    def test_run_once_per_task_flag(self):
        """Test that hook runs once per task."""
        assert SetPrintOutputHook.run_once_per_task is True

    def test_init_with_value(self):
        """Test hook initialization with a value."""
        hook = SetPrintOutputHook(True)
        assert hook.value is True

    def test_init_with_false_value(self):
        """Test hook initialization with False value."""
        hook = SetPrintOutputHook(False)
        assert hook.value is False

    def test_init_without_value(self):
        """Test hook initialization without a value."""
        hook = SetPrintOutputHook()
        assert hook.value is None

    def test_task_started_sets_print_output_true(self):
        """Test task_started sets print_output to True when value is True."""
        hook = SetPrintOutputHook(True)
        mock_task = MagicMock()
        mock_task.params = {}

        hook.task_started(mock_task)

        assert mock_task.params["print_output"] is True

    def test_task_started_sets_print_output_false(self):
        """Test task_started sets print_output to False when value is False."""
        hook = SetPrintOutputHook(False)
        mock_task = MagicMock()
        mock_task.params = {}

        hook.task_started(mock_task)

        assert mock_task.params["print_output"] is False

    def test_task_started_preserves_existing_params(self):
        """Test task_started preserves existing task parameters."""
        hook = SetPrintOutputHook(True)
        mock_task = MagicMock()
        mock_task.params = {"existing_param": "value"}

        hook.task_started(mock_task)

        assert mock_task.params["existing_param"] == "value"
        assert mock_task.params["print_output"] is True

    def test_task_started_overwrites_existing_print_output(self):
        """Test task_started overwrites existing print_output parameter."""
        hook = SetPrintOutputHook(False)
        mock_task = MagicMock()
        mock_task.params = {"print_output": True}

        hook.task_started(mock_task)

        assert mock_task.params["print_output"] is False

    def test_task_started_does_nothing_when_value_none(self):
        """Test task_started does nothing when value is None."""
        hook = SetPrintOutputHook(None)
        mock_task = MagicMock()
        mock_task.params = {"existing": "value"}

        hook.task_started(mock_task)

        assert "print_output" not in mock_task.params
        assert mock_task.params["existing"] == "value"

    def test_task_started_with_string_value(self):
        """Test task_started works with string values."""
        hook = SetPrintOutputHook("yes")
        mock_task = MagicMock()
        mock_task.params = {}

        hook.task_started(mock_task)

        assert mock_task.params["print_output"] == "yes"

    def test_task_started_with_numeric_value(self):
        """Test task_started works with numeric values."""
        hook = SetPrintOutputHook(1)
        mock_task = MagicMock()
        mock_task.params = {}

        hook.task_started(mock_task)

        assert mock_task.params["print_output"] == 1

    def test_other_processor_methods_do_nothing(self):
        """Test that other processor methods have no implementation."""
        hook = SetPrintOutputHook(True)
        mock_task = MagicMock()
        mock_host = MagicMock()
        mock_result = MagicMock()

        # These should not raise any exceptions
        hook.task_completed(mock_task, mock_result)
        hook.task_instance_started(mock_task, mock_host)
        hook.task_instance_completed(mock_task, mock_host, mock_result)
        hook.subtask_instance_started(mock_task, mock_host)
        hook.subtask_instance_completed(mock_task, mock_host, mock_result)

    def test_should_execute_respects_run_once_per_task(self):
        """Test that hook respects run_once_per_task setting."""
        hook = SetPrintOutputHook(True)
        mock_task = MagicMock()

        # First call should return True
        assert hook.should_execute(mock_task) is True

        # Second call with same task should return False
        assert hook.should_execute(mock_task) is False

        # Different task should return True
        mock_task2 = MagicMock()
        assert hook.should_execute(mock_task2) is True