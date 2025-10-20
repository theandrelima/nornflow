from unittest.mock import MagicMock, patch

import pytest

from nornflow.hooks.loader import load_hooks
from nornflow.builtins import SetToHook


class TestHookLoader:
    """Test suite for hook loading operations."""

    @patch("nornflow.hooks.registry.HOOK_REGISTRY", {"set_to": SetToHook})
    def test_load_hooks_with_pre_and_post(self):
        """Test loading hooks from a task model with both pre and post hooks."""
        # Create a mock task model with hooks
        mock_task_model = MagicMock()
        mock_task_model.get_pre_hooks.return_value = []
        mock_task_model.get_post_hooks.return_value = ["set_to"]

        # Mock the set_to attribute
        mock_hook_instance = MagicMock(spec=SetToHook)
        setattr(mock_task_model, "set_to", mock_hook_instance)

        pre_hooks, post_hooks = load_hooks(mock_task_model)

        assert len(pre_hooks) == 0
        assert len(post_hooks) == 1
        assert post_hooks[0] == mock_hook_instance

    def test_load_hooks_no_hooks(self):
        """Test loading hooks from a task model with no hooks."""
        mock_task_model = MagicMock()
        mock_task_model.get_pre_hooks.return_value = []
        mock_task_model.get_post_hooks.return_value = []

        pre_hooks, post_hooks = load_hooks(mock_task_model)

        assert pre_hooks == []
        assert post_hooks == []

    def test_load_hooks_none_values(self):
        """Test loading hooks when hook attributes are None."""
        mock_task_model = MagicMock()
        mock_task_model.get_pre_hooks.return_value = ["pre_hook"]
        mock_task_model.get_post_hooks.return_value = ["post_hook"]

        setattr(mock_task_model, "pre_hook", None)
        setattr(mock_task_model, "post_hook", None)

        pre_hooks, post_hooks = load_hooks(mock_task_model)

        assert pre_hooks == []
        assert post_hooks == []