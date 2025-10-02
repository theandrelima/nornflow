import pytest
from unittest.mock import MagicMock

from nornflow.builtins.filters import hosts, groups


class TestHostsFilter:
    def test_hosts_returns_true_when_list_empty(self):
        mock_host = MagicMock()
        mock_host.name = "router1"
        assert hosts(mock_host, []) is True

    @pytest.mark.parametrize(
        "host_name,filter_list,expected",
        [
            ("router1", ["router1"], True),
            ("router1", ["router2"], False),
            ("router1", ["router2", "router1"], True),
        ],
    )
    def test_hosts_matching(self, host_name, filter_list, expected):
        mock_host = MagicMock()
        mock_host.name = host_name
        assert hosts(mock_host, filter_list) is expected


class TestGroupsFilter:
    def test_groups_returns_true_when_list_empty(self):
        mock_host = MagicMock()
        mock_host.groups = []
        assert groups(mock_host, []) is True

    def test_groups_single_match(self):
        mock_host = MagicMock()
        mock_host.groups = ["edge", "core"]
        assert groups(mock_host, ["edge"]) is True

    def test_groups_any_match_in_list(self):
        mock_host = MagicMock()
        mock_host.groups = ["a", "b", "c"]
        assert groups(mock_host, ["x", "b", "z"]) is True

    def test_groups_no_match(self):
        mock_host = MagicMock()
        mock_host.groups = ["one", "two"]
        assert groups(mock_host, ["three", "four"]) is False

    def test_groups_works_with_dict_like_groups(self):
        # host.groups might be a dict-like mapping of group names; membership checks should still work.
        mock_host = MagicMock()
        mock_host.groups = {"alpha": object(), "beta": object()}
        assert groups(mock_host, ["beta"]) is True
        assert groups(mock_host, ["gamma"]) is False