from unittest.mock import MagicMock, patch

from nornflow.builtins.hooks import SetToHook
from nornflow.hooks.loader import load_hooks


class TestHookLoader:
    """Test suite for hook loading operations."""

    @patch("nornflow.hooks.loader.HOOK_REGISTRY", {"set_to": SetToHook})
    def test_load_hooks_with_hooks(self):
        """Test loading hooks from a hooks dictionary."""
        # Create hooks configuration dict
        hooks_dict = {
            "set_to": "test_variable"
        }
        
        hooks = load_hooks(hooks_dict)
        
        assert len(hooks) == 1
        assert isinstance(hooks[0], SetToHook)
        assert hooks[0].value == "test_variable"

    def test_load_hooks_empty_dict(self):
        """Test loading hooks from an empty dict."""
        hooks = load_hooks({})
        
        assert hooks == []

    def test_load_hooks_none_dict(self):
        """Test loading hooks when dict is None."""
        hooks = load_hooks(None)
        
        assert hooks == []

    def test_load_hooks_multiple(self):
        """Test loading multiple hooks."""
        # Create hooks configuration dict
        hooks_dict = {
            "hook1": "value1",
            "hook2": "value2"
        }
        
        MockHook1 = MagicMock()
        MockHook2 = MagicMock()
        mock_instance1 = MagicMock()
        mock_instance2 = MagicMock()
        MockHook1.return_value = mock_instance1
        MockHook2.return_value = mock_instance2
        
        with patch("nornflow.hooks.loader.HOOK_REGISTRY") as mock_registry:
            mock_registry.get.side_effect = lambda k: {
                "hook1": MockHook1,
                "hook2": MockHook2
            }.get(k)
            
            hooks = load_hooks(hooks_dict)
            
            assert len(hooks) == 2
            MockHook1.assert_called_once_with("value1")
            MockHook2.assert_called_once_with("value2")

    @patch("nornflow.hooks.loader.HOOK_REGISTRY", {})
    def test_load_hooks_unknown_hook(self):
        """Test loading hooks when hook is not registered."""
        # Create hooks configuration dict with unknown hook
        hooks_dict = {
            "unknown_hook": "value"
        }
        
        hooks = load_hooks(hooks_dict)
        
        # Should silently skip unknown hooks
        assert hooks == []

    def test_load_hooks_with_complex_values(self):
        """Test loading hooks with complex configuration values."""
        # Create hooks configuration with different value types
        hooks_dict = {
            "test_hook": {"key": "value", "nested": {"data": 123}}
        }
        
        MockHook = MagicMock()
        mock_instance = MagicMock()
        MockHook.return_value = mock_instance
        
        with patch("nornflow.hooks.loader.HOOK_REGISTRY") as mock_registry:
            mock_registry.get.return_value = MockHook
            
            hooks = load_hooks(hooks_dict)
            
            assert len(hooks) == 1
            MockHook.assert_called_once_with({"key": "value", "nested": {"data": 123}})