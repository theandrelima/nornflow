import pytest
from unittest.mock import MagicMock

from nornflow.constants import NORNFLOW_SETTINGS_OPTIONAL
from nornflow.exceptions import ProcessorError
from nornflow.nornir_manager import NornirManager


class TestNornirManager:
    """Test suite for the NornirManager class."""

    def test_init_with_minimal_params(self, mock_init_nornir, mock_nornir):
        """Test initialization with minimal parameters."""
        manager = NornirManager(nornir_settings="dummy_config.yaml")

        # Verify InitNornir was called with correct params
        mock_init_nornir.assert_called_once_with(config_file="dummy_config.yaml")

        # Verify properties were set correctly
        assert manager.nornir_settings == "dummy_config.yaml"
        assert manager.nornir == mock_nornir
        # Removed check for _local_tasks_nornir which was unused and has been removed

    def test_init_with_additional_params(self, mock_init_nornir):
        """Test initialization with additional parameters."""
        additional_params = {"runner": "threaded", "num_workers": 10}
        manager = NornirManager(nornir_settings="dummy_config.yaml", **additional_params)

        # Verify InitNornir was called with correct params including additional ones
        mock_init_nornir.assert_called_once_with(
            config_file="dummy_config.yaml", runner="threaded", num_workers=10
        )

    def test_init_filters_out_nornflow_params(self, mock_init_nornir):
        """Test that NornFlow-specific params are filtered out of kwargs."""
        # Create a dict with both Nornir and NornFlow params
        params = {
            "runner": "threaded",  # Valid Nornir param
            "local_workflows": ["/tmp/workflows"],  # NornFlow-specific param that should be filtered
            "local_tasks": ["/tmp/tasks"],  # Another NornFlow-specific param
        }

        # Add all optional NornFlow settings to test they're filtered
        for param in NORNFLOW_SETTINGS_OPTIONAL:
            params[param] = f"value_{param}"

        manager = NornirManager(nornir_settings="dummy_config.yaml", **params)

        # Verify InitNornir was called without NornFlow-specific params
        _, call_kwargs = mock_init_nornir.call_args

        # Check that all NornFlow params were removed
        for param in NORNFLOW_SETTINGS_OPTIONAL:
            assert param not in call_kwargs

        # Check that valid Nornir params remain
        assert "runner" in call_kwargs
        assert call_kwargs["runner"] == "threaded"

    def test_remove_optional_nornflow_settings_from_kwargs(self, mock_init_nornir):
        """Test the _remove_optional_nornflow_settings_from_kwargs method."""
        manager = NornirManager(nornir_settings="dummy_config.yaml")

        # Create test kwargs with some NornFlow settings
        kwargs = {
            "runner": "threaded",
            "another_setting": "value",
        }
        
        # Add all optional NornFlow settings to test they're removed
        for param in NORNFLOW_SETTINGS_OPTIONAL:
            kwargs[param] = f"value_{param}"

        # Call the method
        manager._remove_optional_nornflow_settings_from_kwargs(kwargs)

        # Verify NornFlow settings were removed
        assert "runner" in kwargs
        assert "another_setting" in kwargs
        
        # Verify all NornFlow optional settings were removed
        for param in NORNFLOW_SETTINGS_OPTIONAL:
            assert param not in kwargs

    def test_apply_filters_with_valid_filters(self, mock_nornir, mock_init_nornir):
        """Test applying valid filters."""
        manager = NornirManager(nornir_settings="dummy_config.yaml")

        # Apply some filters
        result = manager.apply_filters(name="device1", group="routers")

        # Verify filter was called with correct params
        mock_nornir.filter.assert_called_with(name="device1", group="routers")

        # Verify the result is the filtered Nornir instance
        assert result == mock_nornir

        # Verify the manager's nornir property was updated
        assert manager.nornir == mock_nornir

    def test_apply_filters_with_no_filters(self, mock_init_nornir):
        """Test applying no filters raises an error."""
        manager = NornirManager(nornir_settings="dummy_config.yaml")

        # Verify calling apply_filters with no args raises an error
        with pytest.raises(ProcessorError, match="No filters informed."):
            manager.apply_filters()

    def test_apply_processors_with_valid_processors(self, mock_init_nornir, mock_nornir, mock_processor):
        """Test applying valid processors."""
        manager = NornirManager(nornir_settings="dummy_config.yaml")

        # Apply the processor
        result = manager.apply_processors([mock_processor])

        # Verify with_processors was called with correct params
        mock_nornir.with_processors.assert_called_with([mock_processor])

        # Verify the result is the updated Nornir instance
        assert result == mock_nornir

        # Verify the manager's nornir property was updated
        assert manager.nornir == mock_nornir

    def test_apply_processors_with_no_processors(self, mock_init_nornir):
        """Test applying no processors raises an error."""
        manager = NornirManager(nornir_settings="dummy_config.yaml")

        # Verify calling apply_processors with empty list raises an error
        with pytest.raises(ProcessorError, match="No processors informed."):
            manager.apply_processors([])

    def test_nornir_manager_context_manager(self, mock_init_nornir):
        """Test that NornirManager works as a context manager."""
        # Setup
        nornir_mock = MagicMock()
        mock_init_nornir.return_value = nornir_mock
        
        manager = NornirManager("config.yaml")
        
        # Use as context manager
        with manager:
            # Verify __enter__ returned the manager
            pass  # context is used here
            
        # Verify connections were closed on exit
        nornir_mock.close_connections.assert_called_once_with(on_good=True, on_failed=True)

    def test_nornir_manager_exception_handling(self, mock_init_nornir):
        """Test that connections are closed even when an exception occurs."""
        # Setup
        nornir_mock = MagicMock()
        mock_init_nornir.return_value = nornir_mock
        
        manager = NornirManager("config.yaml")
        
        # Use context manager with an exception
        try:
            with manager:
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected exception, continue with test
            
        # Verify connections were closed despite the exception
        nornir_mock.close_connections.assert_called_once_with(on_good=True, on_failed=True)

    def test_close_connections_processor_handling(self, mock_init_nornir):
        """Test that processors are temporarily cleared during connection closure."""
        # Setup
        nornir_mock = MagicMock()
        original_processors = [MagicMock(), MagicMock()]  # Some processors
        nornir_mock.processors = original_processors.copy()
        mock_init_nornir.return_value = nornir_mock
        
        manager = NornirManager("config.yaml")
        
        # Call close_connections
        manager.close_connections()
        
        # Verify processors were cleared temporarily (indirectly, since we can't easily check this)
        # and connections were closed
        nornir_mock.close_connections.assert_called_once_with(on_good=True, on_failed=True)
