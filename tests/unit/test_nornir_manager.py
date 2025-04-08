import pytest

from nornflow.constants import NONRFLOW_SETTINGS_OPTIONAL
from nornflow.exceptions import ProcessorError
from nornflow.nornir_manager import NornirManager


class TestNornirManager:
    """Test suite for the NornirManager class."""

    def test_init_with_minimal_params(self, mock_init_nornir, mock_nornir):
        """Test initialization with minimal parameters."""
        manager = NornirManager(nornir_settings="dummy_config.yaml", dry_run=False)

        # Verify InitNornir was called with correct params
        mock_init_nornir.assert_called_once_with(config_file="dummy_config.yaml", dry_run=False)

        # Verify properties were set correctly
        assert manager.nornir_settings == "dummy_config.yaml"
        assert manager.dry_run is False
        assert manager.nornir == mock_nornir
        # Removed check for _local_tasks_nornir which was unused and has been removed

    def test_init_with_additional_params(self, mock_init_nornir):
        """Test initialization with additional parameters."""
        additional_params = {"runner": "threaded", "num_workers": 10}
        manager = NornirManager(nornir_settings="dummy_config.yaml", dry_run=True, **additional_params)

        # Verify InitNornir was called with correct params including additional ones
        mock_init_nornir.assert_called_once_with(
            config_file="dummy_config.yaml", dry_run=True, runner="threaded", num_workers=10
        )

    def test_init_filters_out_nornflow_params(self, mock_init_nornir):
        """Test that NornFlow-specific params are filtered out of kwargs."""
        # Create a dict with both Nornir and NornFlow params
        params = {
            "runner": "threaded",  # Valid Nornir param
            "local_workflows_dirs": ["/tmp/workflows"],  # NornFlow-specific param that should be filtered
            "local_tasks_dirs": ["/tmp/tasks"],  # Another NornFlow-specific param
        }

        # Add all optional NornFlow settings to test they're filtered
        for param in NONRFLOW_SETTINGS_OPTIONAL:
            params[param] = f"value_{param}"

        manager = NornirManager(nornir_settings="dummy_config.yaml", **params)

        # Verify InitNornir was called without NornFlow-specific params
        _, call_kwargs = mock_init_nornir.call_args

        # Check that all NornFlow params were removed (except dry_run, which is special)
        for param in NONRFLOW_SETTINGS_OPTIONAL:
            if param != "dry_run":  # Special case: dry_run is passed to InitNornir
                assert param not in call_kwargs

        # Check that valid Nornir params remain
        assert "runner" in call_kwargs
        assert call_kwargs["runner"] == "threaded"

        # Special case: verify dry_run is present and has the right value
        assert "dry_run" in call_kwargs
        assert call_kwargs["dry_run"] == "value_dry_run"

    def test_remove_optional_nornflow_settings_from_kwargs(self, mock_init_nornir):
        """Test the _remove_optional_nornflow_settings_from_kwargs method."""
        manager = NornirManager(nornir_settings="dummy_config.yaml", dry_run=False)

        # Create test kwargs with some NornFlow settings
        kwargs = {
            "runner": "threaded",
            "local_workflows_dirs": ["/tmp/workflows"],
            "another_setting": "value",
        }

        # Call the method
        manager._remove_optional_nornflow_settings_from_kwargs(kwargs)

        # Verify NornFlow settings were removed
        assert "runner" in kwargs
        assert "local_workflows_dirs" not in kwargs
        assert "another_setting" in kwargs

    def test_apply_filters_with_valid_filters(self, mock_nornir, mock_init_nornir):
        """Test applying valid filters."""
        manager = NornirManager(nornir_settings="dummy_config.yaml", dry_run=False)

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
        manager = NornirManager(nornir_settings="dummy_config.yaml", dry_run=False)

        # Verify calling apply_filters with no args raises an error
        with pytest.raises(ProcessorError, match="No filters informed."):
            manager.apply_filters()

    def test_apply_processors_with_valid_processors(self, mock_init_nornir, mock_nornir, mock_processor):
        """Test applying valid processors."""
        manager = NornirManager(nornir_settings="dummy_config.yaml", dry_run=False)

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
        manager = NornirManager(nornir_settings="dummy_config.yaml", dry_run=False)

        # Verify calling apply_processors with empty list raises an error
        with pytest.raises(ProcessorError, match="No processors informed."):
            manager.apply_processors([])