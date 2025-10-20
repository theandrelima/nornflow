from unittest.mock import MagicMock

import pytest

from nornflow.hooks.base import Hook, PostRunHook, PreRunHook
from nornflow.hooks.exceptions import HookConfigurationError


class TestHook:
    """Test suite for base Hook class."""

    def test_init_with_value(self):
        """Test Hook initialization with a value."""
        hook = Hook("test_value")
        assert hook.value == "test_value"

    def test_init_without_value(self):
        """Test Hook initialization without a value."""
        hook = Hook()
        assert hook.value is None

    def test_str(self):
        """Test string representation of Hook."""
        hook = Hook("test_value")
        assert str(hook) == "test_value"

    def test_hash(self):
        """Test Hook hashing."""
        hook1 = Hook("value")
        hook2 = Hook("value")
        hook3 = Hook("different")

        assert hash(hook1) == hash(hook2)
        assert hash(hook1) != hash(hook3)

    def test_eq(self):
        """Test Hook equality."""
        hook1 = Hook("value")
        hook2 = Hook("value")
        hook3 = Hook("different")

        assert hook1 == hook2
        assert hook1 != hook3
        assert hook1 != "not_a_hook"


class TestPreRunHook:
    """Test suite for PreRunHook."""

    def test_abstract_method(self):
        """Test that PreRunHook requires implementation of run."""
        # This should raise HookConfigurationError because of mixin validation
        with pytest.raises(HookConfigurationError):
            PreRunHook()


class TestPostRunHook:
    """Test suite for PostRunHook."""

    def test_abstract_method(self):
        """Test that PostRunHook requires implementation of run."""
        # This should raise HookConfigurationError because of mixin validation
        with pytest.raises(HookConfigurationError):
            PostRunHook()