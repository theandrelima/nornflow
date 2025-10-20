"""Tests for RunnableModel."""

from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest
from nornir.core.task import AggregatedResult

from nornflow.models import RunnableModel
from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager


class TestRunnableModel:
    def test_run_no_hooks(self, mock_nornir_manager, mock_vars_manager):
        """Test run with no hooks."""
        class TestRunnable(RunnableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)
            
            def _run(self, *args, **kwargs):
                return MagicMock(spec=AggregatedResult)

        runnable = TestRunnable()
        tasks_catalog = {}

        result = runnable.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        assert isinstance(result, (MagicMock, AggregatedResult))

    def test_get_pre_hooks_caching(self):
        """Test pre-hook caching."""
        class TestRunnable(RunnableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)

            def _run(self, *args, **kwargs):
                pass

        instance = TestRunnable()
        hooks = instance.get_pre_hooks()
        assert hooks == []
        # Second call should use cache
        assert instance.get_pre_hooks() is hooks

    def test_get_post_hooks_caching(self):
        """Test post-hook caching."""
        class TestRunnable(RunnableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)

            def _run(self, *args, **kwargs):
                pass

        instance = TestRunnable()
        hooks = instance.get_post_hooks()
        assert hooks == []
        # Second call should use cache
        assert instance.get_post_hooks() is hooks

    def test_run_with_pre_hooks(self, mock_nornir_manager, mock_vars_manager):
        """Test run with pre-run hooks that filter hosts."""
        class TestRunnable(RunnableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)
            
            def _run(self, nornir_manager, vars_manager, tasks_catalog, hosts_to_run):
                # Return an AggregatedResult with the filtered hosts
                result = AggregatedResult(name=self.name)
                for host in hosts_to_run:
                    result[host] = MagicMock()
                return result

        # Create a mock pre-hook that will filter hosts
        mock_pre_hook = MagicMock()
        mock_pre_hook.filter_hosts = MagicMock(return_value=["host1", "host3"])
        mock_pre_hook._get_execution_scope = MagicMock(return_value=True)  # RunOncePerTaskMixin
        mock_pre_hook._has_capability = MagicMock(return_value=True)  # Has filtering capability
        
        # Setup mocks
        runnable = TestRunnable()
        
        # Directly set pre_hooks on the instance
        runnable._pre_hooks_cache = [mock_pre_hook]
        
        # Create mock hosts
        mock_host1 = MagicMock()
        mock_host1.name = "host1"
        mock_host2 = MagicMock()
        mock_host2.name = "host2"
        mock_host3 = MagicMock()
        mock_host3.name = "host3"
        
        # Update the hosts dictionary
        mock_nornir_manager.nornir.inventory.hosts = {
            "host1": mock_host1,
            "host2": mock_host2,
            "host3": mock_host3
        }
        
        tasks_catalog = {}

        result = runnable.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)
        
        # Check that only host1 and host3 were included (host2 filtered out)
        assert len(result) == 2
        assert "host1" in result
        assert "host3" in result
        assert "host2" not in result

    def test_run_with_post_hooks(self, mock_nornir_manager, mock_vars_manager):
        """Test run with post-run hooks."""
        class TestRunnable(RunnableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)
            
            def _run(self, nornir_manager, vars_manager, tasks_catalog, hosts_to_run):
                result = AggregatedResult(name=self.name)
                for host in hosts_to_run:
                    result[host] = MagicMock()
                return result

        # Create a mock post-hook
        mock_post_hook = MagicMock()
        mock_post_hook.process_results = MagicMock()
        
        # Setup mocks
        runnable = TestRunnable()
        
        # Directly set post_hooks on the instance
        runnable._post_hooks_cache = [mock_post_hook]
        
        mock_host1 = MagicMock()
        mock_host1.name = "host1"
        
        # Update the hosts dictionary
        mock_nornir_manager.nornir.inventory.hosts = {"host1": mock_host1}
        tasks_catalog = {}

        result = runnable.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)
        
        # Check that the post-hook's process_results method was called
        mock_post_hook.process_results.assert_called()
        
        # Check the result contains the host
        assert "host1" in result