from nornflow.packages.constants import VALID_RESOURCE_TYPES


class TestValidResourceTypes:
    """Sanity checks for the VALID_RESOURCE_TYPES constant."""

    def test_contains_all_expected_types(self):
        expected = {"tasks", "workflows", "blueprints", "filters", "hooks", "j2_filters", "processors"}
        assert set(VALID_RESOURCE_TYPES) == expected

    def test_is_a_tuple(self):
        assert isinstance(VALID_RESOURCE_TYPES, tuple)

    def test_no_duplicates(self):
        assert len(VALID_RESOURCE_TYPES) == len(set(VALID_RESOURCE_TYPES))
