from unittest.mock import MagicMock

import pytest

from nornflow.builtins import SetToHook
from nornflow.vars.manager import NornFlowVariablesManager
from nornir.core.inventory import Host
from nornir.core.task import MultiResult


class TestSetToHook:
    """Test suite for SetToHook operations."""

    def test_run_success(self):
        """Test successful execution of SetToHook."""
        hook = SetToHook("test_var")
        mock_task_model = MagicMock()
        mock_task_model.name = "test_task"
        mock_host = MagicMock(spec=Host)
        mock_host.name = "test_host"
        mock_result = MagicMock(spec=MultiResult)
        mock_nornir_mgr = MagicMock()
        mock_vars_mgr = MagicMock(spec=NornFlowVariablesManager)

        # Mock the inventory hosts
        mock_nornir_mgr.nornir.inventory.hosts = {"test_host": mock_host}

        # Execute the hook using the framework's execute_all_hooks method
        from nornflow.hooks import PostRunHook
        PostRunHook.execute_all_hooks([hook], mock_task_model, {"test_host": mock_result}, mock_nornir_mgr, mock_vars_mgr)

        mock_vars_mgr.set_runtime_variable.assert_called_once_with("test_var", mock_result, "test_host")

    def test_run_no_result(self):
        """Test SetToHook when result is None."""
        hook = SetToHook("test_var")
        mock_task_model = MagicMock()
        mock_host = MagicMock(spec=Host)
        mock_host.name = "test_host"
        mock_nornir_mgr = MagicMock()
        mock_vars_mgr = MagicMock(spec=NornFlowVariablesManager)

        # Mock the inventory hosts
        mock_nornir_mgr.nornir.inventory.hosts = {"test_host": mock_host}

        # Execute the hook using the framework's execute_all_hooks method
        from nornflow.hooks import PostRunHook
        PostRunHook.execute_all_hooks([hook], mock_task_model, None, mock_nornir_mgr, mock_vars_mgr)

        mock_vars_mgr.set_runtime_variable.assert_not_called()

    def test_run_no_value(self):
        """Test SetToHook when hook value is None."""
        hook = SetToHook(None)
        mock_task_model = MagicMock()
        mock_host = MagicMock(spec=Host)
        mock_host.name = "test_host"
        mock_result = MagicMock(spec=MultiResult)
        mock_nornir_mgr = MagicMock()
        mock_vars_mgr = MagicMock(spec=NornFlowVariablesManager)

        # Mock the inventory hosts
        mock_nornir_mgr.nornir.inventory.hosts = {"test_host": mock_host}

        # Execute the hook using the framework's execute_all_hooks method
        from nornflow.hooks import PostRunHook
        PostRunHook.execute_all_hooks([hook], mock_task_model, {"test_host": mock_result}, mock_nornir_mgr, mock_vars_mgr)

        mock_vars_mgr.set_runtime_variable.assert_not_called()

    def test_hook_name(self):
        """Test that SetToHook has the correct hook_name."""
        assert SetToHook.hook_name == "set_to"