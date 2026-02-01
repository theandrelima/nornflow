"""Shared fixtures for j2 unit tests."""

import pytest

from nornflow.j2 import Jinja2Service


@pytest.fixture
def jinja2_service():
    """Provide a fresh Jinja2Service instance for testing."""
    # Reset singleton for isolation
    Jinja2Service._instance = None
    service = Jinja2Service()
    yield service
    # Cleanup after test
    Jinja2Service._instance = None
