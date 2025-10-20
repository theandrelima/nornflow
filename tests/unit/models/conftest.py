"""Test fixtures for models tests."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from nornir.core.inventory import Inventory

from nornflow.nornir_manager import NornirManager
from nornflow.vars.manager import NornFlowVariablesManager


@pytest.fixture
def mock_nornir_manager():
    """Create a properly configured NornirManager mock with nested attributes."""
    mock_manager = MagicMock(spec=NornirManager)
    
    # Create a mock nornir attribute with proper nested structure
    mock_nornir = MagicMock()
    mock_inventory = MagicMock(spec=Inventory)
    mock_inventory.hosts = {}
    
    # Set up the chain: nornir_manager.nornir.inventory.hosts
    mock_nornir.inventory = mock_inventory
    
    # Attach the nornir mock to the manager
    type(mock_manager).nornir = PropertyMock(return_value=mock_nornir)
    
    return mock_manager


@pytest.fixture
def mock_vars_manager():
    """Create a properly configured NornFlowVariablesManager mock."""
    return MagicMock(spec=NornFlowVariablesManager)


@pytest.fixture(autouse=True)
def patch_onetomany():
    """
    Patch the OneToMany class to allow empty collections and return proper instances.
    
    This is needed because some tests attempt to create models with empty collections,
    but the actual OneToMany implementation rejects empty collections.
    """
    from pydantic_serdes.custom_collections import OneToMany
    
    original_new = OneToMany.__new__
    
    def patched_new(cls, iterable):
        # Allow empty collections for testing
        if not iterable:
            # Create an empty OneToMany instance
            instance = super(OneToMany, cls).__new__(cls, ())
            return instance
        else:
            # Use original behavior for non-empty collections
            return original_new(cls, iterable)
    
    with patch.object(OneToMany, '__new__', patched_new):
        yield