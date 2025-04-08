from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from nornflow.exceptions import WorkflowInventoryFilterError
from nornflow.workflow import Workflow


def filter_by_platform(host, platform):
    """Filter by platform."""
    return host.platform == platform


def filter_by_location(host, city, building):
    """Filter by location (city and building)."""
    return host.city == city and host.building == building


def filter_parameterless(host):
    """Filter that takes no additional parameters."""
    return host.is_active


class TestWorkflowFiltering:
    @pytest.fixture
    def filters_catalog(self):
        """Create a filters catalog for testing."""
        # Format: {filter_name: (filter_func, param_names)}
        return {
            "platform": (filter_by_platform, ["platform"]),
            "location": (filter_by_location, ["city", "building"]),
            "active": (filter_parameterless, []),
        }

    def test_no_inventory_filters(self, filters_catalog):
        """Test with no inventory filters."""
        # Create our test instance with empty inventory_filters
        inventory_filters = {}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert result == []

    def test_direct_attribute_filtering(self, filters_catalog):
        """Test direct attribute filtering for keys not in filters_catalog."""
        # Create our test instance with direct attribute filters
        inventory_filters = {"name": "device1", "groups": ["group1", "group2"]}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        # Should have two filter dicts
        assert len(result) == 2
        # Check that both filters are in the result (order may vary)
        assert {"name": "device1"} in result
        assert {"groups": ["group1", "group2"]} in result

    # Case 1: No additional parameters needed (parameter-less filter)
    def test_parameterless_filter(self, filters_catalog):
        """Test a filter function with no parameters besides host."""
        # Create our test instance with a parameterless filter
        inventory_filters = {"active": None}  # This is how it would appear when parsed from YAML

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_parameterless
        # Should not have additional parameters
        assert len(result[0]) == 1

    # Case 2: Parameters provided as a dictionary
    def test_dictionary_parameters(self, filters_catalog):
        """Test a filter with parameters provided as a dictionary."""
        # Create our test instance with dictionary parameters
        inventory_filters = {"location": {"city": "New York", "building": "HQ"}}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_location
        assert result[0]["city"] == "New York"
        assert result[0]["building"] == "HQ"

    # Case 2: Test dictionary parameters with missing required param
    def test_dictionary_parameters_missing_param(self, filters_catalog):
        """Test handling of missing parameters in dictionary format."""
        # Create our test instance with incomplete dictionary parameters
        inventory_filters = {"location": {"city": "New York"}}  # Missing 'building' parameter

        # Should raise WorkflowInventoryFilterError
        with pytest.raises(WorkflowInventoryFilterError) as excinfo:
            self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert "missing" in str(excinfo.value)
        assert "building" in str(excinfo.value)

    # Case 3: Single parameter expecting a list/tuple
    def test_single_parameter_filter_list(self, filters_catalog):
        """Test a filter function with a single parameter and list value."""
        # Create our test instance with a list parameter for a single-param filter
        inventory_filters = {"platform": ["ios", "nxos"]}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_platform
        assert result[0]["platform"] == ["ios", "nxos"]

    # Case 4: Multiple parameters provided as a list in the correct order
    def test_multi_parameter_filter_list(self, filters_catalog):
        """Test a filter with multiple parameters using a positional list."""
        # Create our test instance with a parameter list in same order as function expects
        inventory_filters = {"location": ["New York", "HQ"]}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_location
        assert result[0]["city"] == "New York"
        assert result[0]["building"] == "HQ"

    # Case 5: Single parameter with a scalar value
    def test_single_parameter_filter_scalar(self, filters_catalog):
        """Test a filter function with a single parameter and scalar value."""
        # Create our test instance with a scalar parameter
        inventory_filters = {"platform": "ios"}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_platform
        assert result[0]["platform"] == "ios"

    # Case 6: Parameter mismatch - incompatible values format
    def test_incompatible_parameter_format(self, filters_catalog):
        """Test handling of incompatible parameter formats."""
        # Create our test instance with mismatched parameters
        # Location expects 2 parameters but we're providing just one string
        inventory_filters = {"location": "New York"}  # Scalar for multi-param function

        # Should raise WorkflowInventoryFilterError
        with pytest.raises(WorkflowInventoryFilterError) as excinfo:
            self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert "expects 2 parameters" in str(excinfo.value)
        assert "incompatible value" in str(excinfo.value)

    def test_tuple_handling(self, filters_catalog):
        """Test that tuples in filter values are handled properly."""
        # Create our test instance with a tuple filter value
        inventory_filters = {"platform": ("ios", "nxos")}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_platform
        # Tuples should be handled like lists
        assert result[0]["platform"] == ("ios", "nxos")

    def test_mixed_filters(self, filters_catalog):
        """Test with a mix of direct and function-based filters."""
        # Create our test instance with mixed filters
        inventory_filters = {
            "platform": "ios",  # Case 5: filter function with scalar value
            "name": ["router1", "router2"],  # Direct attribute filter with list
            "active": None,  # Case 1: Parameterless filter
        }

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        # Should have three filter dicts
        assert len(result) == 3

        # Check for each type of filter (in any order)
        platform_filter = next(
            (r for r in result if "filter_func" in r and r["filter_func"] == filter_by_platform), None
        )
        active_filter = next(
            (r for r in result if "filter_func" in r and r["filter_func"] == filter_parameterless), None
        )
        name_filter = next((r for r in result if "name" in r), None)

        assert platform_filter is not None
        assert active_filter is not None
        assert name_filter is not None
        assert name_filter["name"] == ["router1", "router2"]

    def _get_filtering_kwargs_impl(self, inventory_filters, filters_catalog):
        """
        Implementation of _get_filtering_kwargs for testing.

        This properly patches the inventory_filters property to return our test values.
        """
        # Create a workflow instance and patch its inventory_filters property
        with patch(
            "nornflow.workflow.Workflow.inventory_filters",
            new_callable=PropertyMock,
            return_value=inventory_filters,
        ):
            # Create a workflow instance
            workflow = Workflow.__new__(Workflow)

            # Call the method we want to test
            return workflow._get_filtering_kwargs(filters_catalog)
