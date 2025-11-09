"""Test fixtures for hooks tests."""

from unittest.mock import MagicMock

import pytest

from nornflow.vars.manager import NornFlowVariablesManager


@pytest.fixture
def mock_vars_manager():
    """Create a properly configured NornFlowVariablesManager mock for hooks testing."""
    return MagicMock(spec=NornFlowVariablesManager)


@pytest.fixture
def mock_task_model():
    """Create a mock task model for hooks testing."""
    mock = MagicMock()
    mock.name = "test_task"
    return mock


@pytest.fixture
def mock_host():
    """Create a mock host for hooks testing."""
    mock = MagicMock()
    mock.name = "test_host"
    return mock


@pytest.fixture
def mock_result():
    """Create a mock result for hooks testing."""
    return MagicMock()