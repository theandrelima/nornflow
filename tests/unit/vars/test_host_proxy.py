from unittest.mock import MagicMock

import pytest

from nornflow.vars.exceptions import VariableError
from nornflow.vars.proxy import NornirHostProxy


class TestNornirHostProxyBasic:
    def test_current_host_name_clear_on_none(self):
        proxy = NornirHostProxy()
        # start with a host set, then clear
        host = MagicMock()
        proxy._current_host = host
        proxy.current_host_name = None
        assert proxy.current_host is None
        assert proxy.current_host_name is None

    def test_current_host_name_cleared_if_nornir_not_set(self):
        proxy = NornirHostProxy()
        # Ensure no nornir instance
        proxy.nornir = None
        # Attempt to set a host name when no Nornir available -> should clear and not raise
        proxy.current_host = MagicMock()  # pre-populate to ensure clearing happens
        proxy.current_host_name = "somehost"
        assert proxy.current_host is None

    def test_current_host_name_sets_when_host_found_in_inventory(self):
        proxy = NornirHostProxy()
        mock_host = MagicMock()
        mock_host.name = "host1"
        mock_nornir = MagicMock()
        mock_nornir.inventory.hosts = {"host1": mock_host}
        proxy.nornir = mock_nornir
        proxy.current_host_name = "host1"
        assert proxy.current_host is mock_host
        assert proxy.current_host_name == "host1"

    def test_current_host_name_cleared_when_host_not_found(self):
        proxy = NornirHostProxy()
        mock_nornir = MagicMock()
        mock_nornir.inventory.hosts = {}
        proxy.nornir = mock_nornir
        proxy.current_host_name = "missing"
        assert proxy.current_host is None


class TestNornirHostProxyAttributeAccess:
    def test___getattr___raises_when_nornir_missing(self):
        proxy = NornirHostProxy()
        proxy._nornir = None
        proxy._current_host = None
        with pytest.raises(VariableError) as exc:
            _ = proxy.some_attr  # triggers __getattr__
        assert "Nornir instance not set" in str(exc.value)

    def test___getattr___raises_when_current_host_missing(self):
        proxy = NornirHostProxy()
        proxy._nornir = MagicMock()
        proxy._current_host = None
        with pytest.raises(VariableError) as exc:
            _ = proxy.some_attr
        assert "No active host context" in str(exc.value)

    def test__get_host_value_returns_value_when_present(self):
        proxy = NornirHostProxy()
        mock_host = MagicMock()
        # Host.get should return the value when present
        mock_host.get.return_value = "the-value"
        proxy._current_host = mock_host
        proxy._nornir = MagicMock()
        # Access via __getattr__
        assert proxy.some_key == "the-value"
        mock_host.get.assert_called_once_with("some_key")

    def test__get_host_value_raises_when_value_missing(self):
        proxy = NornirHostProxy()
        mock_host = MagicMock()
        mock_host.name = "hostX"
        mock_host.get.return_value = None
        proxy._current_host = mock_host
        proxy._nornir = MagicMock()
        with pytest.raises(VariableError) as exc:
            _ = proxy.missing_key
        assert "Attribute or key 'missing_key' not found" in str(exc.value)