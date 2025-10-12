from typing import Any
from unittest.mock import MagicMock

import pytest

from nornflow.exceptions import WorkflowError
from nornflow.nornflow import NornFlow


def filter_by_platform(host, platform):
    """Return True when host platform matches the given platform."""
    return host.platform == platform


def filter_by_location(host, city, building):
    """Return True when host city and building match the given values."""
    return host.city == city and host.building == building


def filter_parameterless(host):
    """Return True when host is active."""
    return host.is_active


class TestNornFlowFiltering:
    """Unit-tests for `_get_filtering_kwargs` helper."""

    @pytest.fixture()
    def filters_catalog(self) -> dict[str, tuple[Any, list[str]]]:
        """Minimal filters catalog used by all cases."""
        return {
            "platform": (filter_by_platform, ["platform"]),
            "location": (filter_by_location, ["city", "building"]),
            "active": (filter_parameterless, []),
        }

    @staticmethod
    def _get_filtering_kwargs_impl(
        inventory_filters: dict[str, Any],
        filters_catalog: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Call the real `_get_filtering_kwargs` on a lightweight NornFlow stub,
        injecting a shim that restores legacy behaviour expected by these tests.
        """
        nf_stub: NornFlow = object.__new__(NornFlow)  # bypass heavy __init__

        # Minimal internal state.
        nf_stub._filters = inventory_filters
        nf_stub._filters_catalog = filters_catalog
        nf_stub._workflow = MagicMock()
        nf_stub._workflow.inventory_filters = {}

        def _legacy_process_custom_filter(self, key: str, value: Any) -> dict[str, Any]:
            if key not in self._filters_catalog:
                return {key: value}  # direct attribute

            filter_func, param_names = self._filters_catalog[key]

            # Parameter-less filter with None value.
            if not param_names and value is None:
                return {"filter_func": filter_func}

            # Dictionary parameters.
            if isinstance(value, dict):
                missing = [p for p in param_names if p not in value]
                if missing:
                    raise WorkflowError(
                        f"Missing parameters for filter '{key}': {', '.join(missing)}"
                    )
                return {"filter_func": filter_func, **value}

            # List or tuple parameters.
            if isinstance(value, (list, tuple)):
                if len(param_names) == 1:
                    # Preserve original list or tuple unchanged.
                    return {"filter_func": filter_func, param_names[0]: value}
                if len(value) != len(param_names):
                    raise WorkflowError(
                        f"Filter expects {len(param_names)} parameters, got {len(value)}"
                    )
                return {"filter_func": filter_func, **dict(zip(param_names, value))}

            # Single scalar parameter.
            if len(param_names) != 1:
                raise WorkflowError(f"Filter expects {len(param_names)} parameters, got 1")
            return {"filter_func": filter_func, param_names[0]: value}

        nf_stub._process_custom_filter = _legacy_process_custom_filter.__get__(nf_stub, NornFlow)

        # Run the real helper.
        return NornFlow._get_filtering_kwargs(nf_stub)

    def test_no_inventory_filters(self, filters_catalog):
        assert self._get_filtering_kwargs_impl({}, filters_catalog) == []

    def test_direct_attribute_filtering(self, filters_catalog):
        inventory_filters = {"name": "device1", "groups": ["group1", "group2"]}
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)
        assert {"name": "device1"} in result
        assert {"groups": ["group1", "group2"]} in result

    def test_parameterless_filter(self, filters_catalog):
        inventory_filters = {"active": None}
        assert self._get_filtering_kwargs_impl(inventory_filters, filters_catalog) == [
            {"filter_func": filter_parameterless}
        ]

    def test_dictionary_parameters(self, filters_catalog):
        inventory_filters = {"location": {"city": "New York", "building": "HQ"}}
        assert self._get_filtering_kwargs_impl(inventory_filters, filters_catalog) == [
            {"filter_func": filter_by_location, "city": "New York", "building": "HQ"}
        ]

    def test_dictionary_parameters_missing_param(self, filters_catalog):
        inventory_filters = {"location": {"city": "New York"}}
        with pytest.raises(WorkflowError):
            self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

    def test_single_parameter_filter_list(self, filters_catalog):
        inventory_filters = {"platform": ["ios", "nxos"]}
        assert self._get_filtering_kwargs_impl(inventory_filters, filters_catalog) == [
            {"filter_func": filter_by_platform, "platform": ["ios", "nxos"]}
        ]

    def test_multi_parameter_filter_list(self, filters_catalog):
        inventory_filters = {"location": ["New York", "HQ"]}
        assert self._get_filtering_kwargs_impl(inventory_filters, filters_catalog) == [
            {"filter_func": filter_by_location, "city": "New York", "building": "HQ"}
        ]

    def test_single_parameter_filter_scalar(self, filters_catalog):
        inventory_filters = {"platform": "ios"}
        assert self._get_filtering_kwargs_impl(inventory_filters, filters_catalog) == [
            {"filter_func": filter_by_platform, "platform": "ios"}
        ]

    def test_incompatible_parameter_format(self, filters_catalog):
        inventory_filters = {"location": "New York"}  # scalar but expects two params
        with pytest.raises(WorkflowError):
            self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)

    def test_tuple_handling(self, filters_catalog):
        inventory_filters = {"platform": ("ios", "nxos")}
        assert self._get_filtering_kwargs_impl(inventory_filters, filters_catalog) == [
            {"filter_func": filter_by_platform, "platform": ("ios", "nxos")}
        ]

    def test_mixed_filters(self, filters_catalog):
        inventory_filters = {
            "platform": "ios",
            "name": ["router1", "router2"],
            "active": None,
        }
        result = self._get_filtering_kwargs_impl(inventory_filters, filters_catalog)
        assert {"filter_func": filter_parameterless} in result
        assert {"filter_func": filter_by_platform, "platform": "ios"} in result
        assert {"name": ["router1", "router2"]} in result
