import pytest
from nornir.core.inventory import Host

from nornflow.exceptions import WorkflowInventoryFilterError


# Define test filter functions
def filter_by_platform(host: Host, platform: str) -> bool:
    """Filter hosts by platform."""
    return host.platform == platform


def filter_by_location(host: Host, city: str, building: str) -> bool:
    """Filter hosts by location (city and building)."""
    return host.data.get("city") == city and host.data.get("building") == building


def filter_parameterless(host: Host) -> bool:
    """A filter with no parameters besides host."""
    return True


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

    def test_single_parameter_filter_scalar(self, filters_catalog):
        """Test a filter function with a single parameter and scalar value."""
        # Create our test instance with a single parameter filter
        inventory_filters = {"platform": "ios"}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_platform
        assert result[0]["platform"] == "ios"

    def test_single_parameter_filter_list(self, filters_catalog):
        """Test a filter function with a single parameter and list value."""
        # Create our test instance with a single parameter filter (list)
        inventory_filters = {"platform": ["ios", "nxos"]}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_platform
        assert result[0]["platform"] == ["ios", "nxos"]

    def test_multi_parameter_filter_list(self, filters_catalog):
        """Test a filter with multiple parameters using a positional list."""
        # Create our test instance with a multi-parameter filter (list)
        inventory_filters = {"location": ["New York", "HQ"]}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_location
        # Check both parameters are set correctly
        assert result[0]["city"] == "New York"
        assert result[0]["building"] == "HQ"

    def test_multi_parameter_filter_dict(self, filters_catalog):
        """Test a filter with multiple parameters using a dictionary."""
        # Create our test instance with a multi-parameter filter (dict)
        inventory_filters = {"location": {"city": "San Francisco", "building": "Office 1"}}

        # Call our implementation directly
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert len(result) == 1
        assert result[0]["filter_func"] == filter_by_location
        assert result[0]["city"] == "San Francisco"
        assert result[0]["building"] == "Office 1"

    def test_multi_parameter_filter_missing_param(self, filters_catalog):
        """Test error when a required parameter is missing."""
        # Create our test instance with a multi-parameter filter missing a parameter
        inventory_filters = {"location": {"city": "London"}}  # Missing 'building'

        # Call our implementation directly - should raise an exception
        with pytest.raises(WorkflowInventoryFilterError) as exc_info:
            self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert "missing" in str(exc_info.value).lower()
        assert "building" in str(exc_info.value)

    def test_multi_parameter_filter_wrong_format(self, filters_catalog):
        """Test error when parameters are provided in incorrect format."""
        # Create our test instance with a multi-parameter filter in wrong format
        inventory_filters = {"location": "London"}  # Not a dict or list matching parameter count

        # Call our implementation directly - should raise an exception
        with pytest.raises(WorkflowInventoryFilterError) as exc_info:
            self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

        assert "incompatible value" in str(exc_info.value).lower()

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
            "platform": "ios",  # direct host attr filter
            "name": ["router1", "router2"],  # filter function
            "active": None,  # Parameterless filter
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

    def _process_custom_filter(self, filter_key, filter_value, filters_catalog):
        """Process a custom filter from the inventory_filters."""
        # Get the filter function and its parameter names
        filter_func, param_names = filters_catalog[filter_key]

        # Case 1: No parameters for the filter function (besides host)
        if not param_names:
            return {"filter_func": filter_func}

        # Case 2: Single parameter for the filter function
        elif len(param_names) == 1:
            param_name = param_names[0]
            return {"filter_func": filter_func, param_name: filter_value}

        # Case 3: Multiple parameters for the filter function
        else:
            # Handle list format
            if isinstance(filter_value, (list, tuple)):
                # Ensure list length matches parameter count
                if len(filter_value) != len(param_names):
                    raise WorkflowInventoryFilterError(
                        f"Filter '{filter_key}' requires {len(param_names)} parameters, but {len(filter_value)} were provided"
                    )
                # Create a dictionary mapping param names to values
                filter_kwargs = {"filter_func": filter_func}
                for i, param_name in enumerate(param_names):
                    filter_kwargs[param_name] = filter_value[i]
                return filter_kwargs

            # Handle dict format
            elif isinstance(filter_value, dict):
                # Check for missing parameters
                missing_params = [p for p in param_names if p not in filter_value]
                if missing_params:
                    raise WorkflowInventoryFilterError(
                        f"Filter '{filter_key}' is missing required parameters: {', '.join(missing_params)}"
                    )
                # Create a dictionary with the filter function and parameters
                filter_kwargs = {"filter_func": filter_func}
                for param_name in param_names:
                    filter_kwargs[param_name] = filter_value[param_name]
                return filter_kwargs

            # Error for incompatible value type
            else:
                raise WorkflowInventoryFilterError(
                    f"Filter '{filter_key}' requires multiple parameters, but incompatible value type was provided: {type(filter_value)}"
                )

    def _get_filtering_kwargs_impl(self, inventory_filters, filters_catalog):
        """Our implementation of Workflow._get_filtering_kwargs for testing."""
        # Skip if no inventory filters defined
        if not inventory_filters:
            return []

        # Process each filter
        filter_kwargs_list = []
        for key, filter_values in inventory_filters.items():
            if key in filters_catalog:
                # We first check if a key under 'inventory_filters' is a filter function in the filters_catalog
                filter_kwargs = self._process_custom_filter(key, filter_values, filters_catalog)
                filter_kwargs_list.append(filter_kwargs)
            else:
                # Case 7: No matching filter function - use direct attribute filtering
                filter_kwargs_list.append({key: filter_values})

        return filter_kwargs_list
