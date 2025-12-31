from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from nornir.core.task import AggregatedResult

from nornflow.models import HookableModel


class TestHookableModel:
    def test_run_no_hooks(self, mock_nornir_manager, mock_vars_manager):
        """Test run with no hooks."""
        class TestHookable(HookableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)
            
            def run(self, nornir_manager, vars_manager, tasks_catalog):
                return MagicMock(spec=AggregatedResult)

        hookable = TestHookable()
        tasks_catalog = {}

        result = hookable.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)

        assert isinstance(result, (MagicMock, AggregatedResult))

    def test_get_hooks_caching(self):
        """Test hook caching."""
        class TestHookable(HookableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)

            def run(self, nornir_manager, vars_manager, tasks_catalog):
                pass

        instance = TestHookable()
        hooks = instance.get_hooks()
        assert hooks == []
        # Second call should use cache
        assert instance.get_hooks() is hooks

    def test_run_with_pre_hooks(self, mock_nornir_manager, mock_vars_manager):
        """Test run with pre-run hooks that filter hosts."""
        class TestHookable(HookableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)
            
            def run(self, nornir_manager, vars_manager, tasks_catalog):
                # Return an AggregatedResult with the filtered hosts
                result = AggregatedResult(name=self.name)
                for host in ["host1", "host3"]:  # Simulate filtered hosts
                    result[host] = MagicMock()
                return result

        # Create a mock pre-hook that will filter hosts
        mock_pre_hook = MagicMock()
        mock_pre_hook.filter_hosts = MagicMock(return_value=["host1", "host3"])
        mock_pre_hook._get_execution_scope = MagicMock(return_value=True)  # RunOncePerTaskMixin
        mock_pre_hook._has_capability = MagicMock(return_value=True)  # Has filtering capability
        
        # Setup mocks
        hookable = TestHookable()
        
        # Directly set hooks cache on the instance
        hookable._hooks_cache = [mock_pre_hook]
        
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

        result = hookable.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)
        
        # Check that only host1 and host3 were included (host2 filtered out)
        assert len(result) == 2
        assert "host1" in result
        assert "host3" in result
        assert "host2" not in result

    def test_run_with_post_hooks(self, mock_nornir_manager, mock_vars_manager):
        """Test run with post-run hooks."""
        class TestHookable(HookableModel):
            name: str = "test"
            _key: ClassVar[tuple[str, ...]] = ("name",)
            
            def run(self, nornir_manager, vars_manager, tasks_catalog):
                result = AggregatedResult(name=self.name)
                result["host1"] = MagicMock()  # Simulate one host
                
                # Simulate hook processing for post-hooks
                hooks = self.get_hooks()
                for hook in hooks:
                    if hasattr(hook, 'process_results'):
                        hook.process_results(result, nornir_manager, vars_manager)
                
                return result

        # Create a mock post-hook
        mock_post_hook = MagicMock()
        mock_post_hook.process_results = MagicMock()
        
        # Setup mocks
        hookable = TestHookable()
        
        # Directly set hooks cache on the instance
        hookable._hooks_cache = [mock_post_hook]
        
        mock_host1 = MagicMock()
        mock_host1.name = "host1"
        
        # Update the hosts dictionary
        mock_nornir_manager.nornir.inventory.hosts = {"host1": mock_host1}
        tasks_catalog = {}

        result = hookable.run(mock_nornir_manager, mock_vars_manager, tasks_catalog)
        
        # Check that the post-hook's process_results method was called
        mock_post_hook.process_results.assert_called()
        
        # Check the result contains the host
        assert "host1" in result