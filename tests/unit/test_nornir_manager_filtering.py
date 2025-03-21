from unittest.mock import Mock, patch

import pytest
from nornir.core.inventory import Host

from nornflow.exceptions import ProcessorError
from nornflow.nornir_manager import NornirManager


# Define test filter functions
def filter_by_platform(host: Host, platform: str) -> bool:
    """Filter hosts by platform."""
    return host.platform == platform


class TestNornirManagerFilters:
    @pytest.fixture
    def mock_nornir(self):
        """Create a mock Nornir instance."""
        mock = Mock()
        # Setup .filter() to return the mock itself for chaining
        mock.filter.return_value = mock
        return mock

    @pytest.fixture
    def manager(self, mock_nornir):
        """Create a NornirManager with mocked Nornir instance."""
        with patch("nornflow.nornir_manager.InitNornir", return_value=mock_nornir):
            return NornirManager(nornir_settings="dummy_path.yaml", dry_run=False)

    def test_no_filters_error(self, manager):
        """Test that an error is raised when no filters are provided."""
        with pytest.raises(ProcessorError):
            manager.apply_filters()

    def test_direct_attribute_filtering(self, manager, mock_nornir):
        """Test direct attribute filtering."""
        manager.apply_filters(name="test-device", platform="ios")

        # Verify filter was called with correct args
        mock_nornir.filter.assert_called_with(name="test-device", platform="ios")

    def test_function_based_filtering(self, manager, mock_nornir):
        """Test function-based filtering."""
        manager.apply_filters(filter_func=filter_by_platform, platform="ios")

        # Verify filter was called with correct args
        mock_nornir.filter.assert_called_with(filter_func=filter_by_platform, platform="ios")

    def test_tuple_handling(self, manager, mock_nornir):
        """Test that tuples are passed through correctly."""
        test_tuple = ("host1", "host2")
        manager.apply_filters(hosts=test_tuple)

        # Verify filter was called with tuple intact
        mock_nornir.filter.assert_called_with(hosts=test_tuple)

    def test_multiple_filters(self, manager, mock_nornir):
        """Test multiple filters in one call."""
        filter_kwargs = {
            "name__any": ["device1", "device2"],
            "platform": "ios",
            "filter_func": filter_by_platform,
        }
        manager.apply_filters(**filter_kwargs)

        # Verify filter was called with all kwargs
        mock_nornir.filter.assert_called_with(**filter_kwargs)
