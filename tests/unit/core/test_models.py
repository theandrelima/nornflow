from unittest.mock import MagicMock

import pytest
from nornir.core.task import AggregatedResult

from nornflow.exceptions import TaskError
from nornflow.models import TaskModel
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager


class TestTaskModel:
    def test_task_model_run_success(self):
        """Test the TaskModel.run method successfully executes a task."""
        # Setup
        task_model = TaskModel(name="test_task", args={"arg1": "value1"})

        # Create mock nornir_manager with nornir attribute
        mock_nornir_manager = MagicMock(spec=NornirManager)
        mock_nornir_manager.nornir = MagicMock()  # Add nornir attribute to mock

        # Create mock vars_manager
        mock_vars_manager = MagicMock(spec=NornFlowVariablesManager)
        
        mock_result = MagicMock(spec=AggregatedResult)
        mock_nornir_manager.nornir.run.return_value = mock_result

        # Mock task function and catalog
        mock_task_func = MagicMock()
        tasks_catalog = {"test_task": mock_task_func}

        # Execute
        result = task_model.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        # Verify
        assert result == mock_result
        mock_nornir_manager.nornir.run.assert_called_once_with(task=mock_task_func, arg1="value1")

    def test_task_model_run_task_not_found(self):
        """Test that TaskModel.run raises an error when the task is not in the catalog."""
        # Setup
        task_model = TaskModel(name="missing_task")
        mock_nornir_manager = MagicMock(spec=NornirManager)
        # No need to add nornir attribute here as we won't get that far
        mock_vars_manager = MagicMock(spec=NornFlowVariablesManager)
        empty_catalog = {}

        # Verify the correct exception is raised
        with pytest.raises(
            TaskError, match="Task function for 'missing_task' not found in tasks catalog"
        ):
            task_model.run(mock_nornir_manager, mock_vars_manager, empty_catalog)

    def test_task_model_run_with_no_args(self):
        """Test that TaskModel.run works correctly with no args."""
        # Setup
        task_model = TaskModel(name="test_task", args=None)

        # Create mock nornir_manager with nornir attribute
        mock_nornir_manager = MagicMock(spec=NornirManager)
        mock_nornir_manager.nornir = MagicMock()  # Add nornir attribute to mock

        # Create mock vars_manager
        mock_vars_manager = MagicMock(spec=NornFlowVariablesManager)
        
        mock_result = MagicMock(spec=AggregatedResult)
        mock_nornir_manager.nornir.run.return_value = mock_result

        # Mock task function and catalog
        mock_task_func = MagicMock()
        tasks_catalog = {"test_task": mock_task_func}

        # Execute
        result = task_model.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        # Verify
        assert result == mock_result
        mock_nornir_manager.nornir.run.assert_called_once_with(task=mock_task_func)

    def test_task_model_run_with_empty_args(self):
        """Test that TaskModel.run works correctly with empty args."""
        # Setup
        task_model = TaskModel(name="test_task", args={})

        # Create mock nornir_manager with nornir attribute
        mock_nornir_manager = MagicMock(spec=NornirManager)
        mock_nornir_manager.nornir = MagicMock()  # Add nornir attribute to mock

        # Create mock vars_manager
        mock_vars_manager = MagicMock(spec=NornFlowVariablesManager)
        
        mock_result = MagicMock(spec=AggregatedResult)
        mock_nornir_manager.nornir.run.return_value = mock_result

        # Mock task function and catalog
        mock_task_func = MagicMock()
        tasks_catalog = {"test_task": mock_task_func}

        # Execute
        result = task_model.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        # Verify
        assert result == mock_result
        mock_nornir_manager.nornir.run.assert_called_once_with(task=mock_task_func)