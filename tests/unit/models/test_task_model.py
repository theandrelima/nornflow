"""Tests for TaskModel."""

from unittest.mock import MagicMock, patch

import pytest
from nornir.core.task import AggregatedResult
from pydantic_serdes.custom_collections import HashableDict

from nornflow.exceptions import TaskError
from nornflow.models import TaskModel


class TestTaskModel:
    @patch("nornflow.hooks.loader.load_hooks", return_value=[])
    def test_run_success(self, mock_load_hooks, mock_nornir_manager, mock_vars_manager):
        """Test successful task execution."""
        task = TaskModel(name="test_task", args={"arg1": "value1"})
        
        # Setup the mock for nornir.run
        mock_result = MagicMock(spec=AggregatedResult)
        mock_nornir_manager.nornir.run.return_value = mock_result
        mock_nornir_manager.nornir.inventory.hosts = {"host1": MagicMock()}
        
        tasks_catalog = {"test_task": MagicMock()}

        result = task.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        assert result == mock_result
        mock_nornir_manager.nornir.run.assert_called_once_with(task=tasks_catalog["test_task"], arg1="value1")

    @patch("nornflow.hooks.loader.load_hooks", return_value=[])
    def test_run_task_not_found(self, mock_load_hooks, mock_nornir_manager, mock_vars_manager):
        """Test error when task not in catalog."""
        task = TaskModel(name="missing_task")
        mock_nornir_manager.nornir.inventory.hosts = {"host1": MagicMock()}

        with pytest.raises(TaskError, match="Task function for 'missing_task' not found"):
            task.run(mock_nornir_manager, mock_vars_manager, {})

    @patch("nornflow.hooks.loader.load_hooks", return_value=[])
    def test_run_with_no_args(self, mock_load_hooks, mock_nornir_manager, mock_vars_manager):
        """Test execution with no args."""
        task = TaskModel(name="test_task", args=None)
        
        # Setup the mock for nornir.run
        mock_result = MagicMock(spec=AggregatedResult)
        mock_nornir_manager.nornir.run.return_value = mock_result
        mock_nornir_manager.nornir.inventory.hosts = {"host1": MagicMock()}
        
        tasks_catalog = {"test_task": MagicMock()}

        result = task.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        assert result == mock_result
        mock_nornir_manager.nornir.run.assert_called_once_with(task=tasks_catalog["test_task"])

    @patch("nornflow.hooks.loader.load_hooks", return_value=[])
    def test_run_with_empty_args(self, mock_load_hooks, mock_nornir_manager, mock_vars_manager):
        """Test execution with empty args."""
        task = TaskModel(name="test_task", args={})
        
        # Setup the mock for nornir.run
        mock_result = MagicMock(spec=AggregatedResult)
        mock_nornir_manager.nornir.run.return_value = mock_result
        mock_nornir_manager.nornir.inventory.hosts = {"host1": MagicMock()}
        
        tasks_catalog = {"test_task": MagicMock()}

        result = task.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        assert result == mock_result
        mock_nornir_manager.nornir.run.assert_called_once_with(task=tasks_catalog["test_task"])

    def test_validate_args(self):
        """Test args validation converts to hashable."""
        task = TaskModel(name="test_task", args={"key": ["list", "values"]})
        assert isinstance(task.args, dict)
        assert task.args["key"] == ("list", "values")  # Converted to tuple

    def test_validate_set_to(self):
        """Test set_to validation creates SetToHook."""
        from nornflow.builtins.hooks import SetToHook
        
        # In the refactored hook framework, hooks are configured through a hooks dictionary
        # where keys are hook names and values are the hook parameter values
        task = TaskModel(name="test_task", hooks=HashableDict({"set_to": "var_name"}))
        
        # The task's get_hooks method should return the hook instances
        hooks = task.get_hooks()
        
        # Check that a SetToHook was created and is in the hooks
        set_to_hooks = [hook for hook in hooks if isinstance(hook, SetToHook)]
        assert len(set_to_hooks) == 1
        assert set_to_hooks[0].value == "var_name"

    def test_create_auto_increment_id(self):
        """Test create method auto-increments id."""
        # Just test that tasks get different IDs
        task1 = TaskModel.create({"name": "task1"})
        task2 = TaskModel.create({"name": "task2"})
        assert task1.id != task2.id
        assert task1.id is not None
        assert task2.id is not None

    @patch("nornflow.hooks.loader.load_hooks", return_value=[])
    def test_run_with_no_hosts(self, mock_load_hooks, mock_nornir_manager, mock_vars_manager):
        """Test execution when no hosts are available."""
        task = TaskModel(name="test_task")
        mock_nornir_manager.nornir.inventory.hosts = {}
        
        # Setup the mock for nornir.run to return an empty AggregatedResult
        empty_result = AggregatedResult(name="test_task")
        mock_nornir_manager.nornir.run.return_value = empty_result
        
        tasks_catalog = {"test_task": MagicMock()}

        result = task.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        # Should return empty AggregatedResult
        assert isinstance(result, AggregatedResult)
        assert len(result) == 0