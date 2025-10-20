from unittest.mock import MagicMock

import pytest

from nornflow.hooks.exceptions import HookRegistrationError
from nornflow.hooks.registry import HOOK_REGISTRY, register_hook


class TestHookRegistry:
    """Test suite for hook registry operations."""

    def test_register_hook_success(self):
        """Test successful hook registration."""
        # Define a mock hook class
        class MockHook:
            hook_name = "mock_hook"

        # Register the hook
        result = register_hook(MockHook)

        # Verify registration
        assert result == MockHook
        assert HOOK_REGISTRY["mock_hook"] == MockHook

    def test_register_hook_missing_hook_name(self):
        """Test registration failure when hook_name is missing."""
        class MockHook:
            pass  # No hook_name

        with pytest.raises(HookRegistrationError, match="must define a hook_name"):
            register_hook(MockHook)

    def test_register_hook_empty_hook_name(self):
        """Test registration failure when hook_name is empty."""
        class MockHook:
            hook_name = ""

        with pytest.raises(HookRegistrationError, match="must define a hook_name"):
            register_hook(MockHook)

    def test_register_hook_overwrite(self):
        """Test that registering the same hook_name overwrites the previous entry."""
        class MockHook1:
            hook_name = "test_hook"

        class MockHook2:
            hook_name = "test_hook"

        register_hook(MockHook1)
        assert HOOK_REGISTRY["test_hook"] == MockHook1

        register_hook(MockHook2)
        assert HOOK_REGISTRY["test_hook"] == MockHook2