"""Shared fixtures for integration tests."""

import sys
from collections.abc import Iterator
from unittest.mock import patch

import pytest

import nornflow.builtins.hooks  # noqa: F401 — populate builtin hooks in HOOKS_CATALOG
from nornflow.j2 import Jinja2Service
from nornflow.nornflow import NornFlow

from tests.integration.catalog_namespaces.lab_builder import IntegrationLab, build_integration_lab


@pytest.fixture(scope="session")
def integration_lab(tmp_path_factory: pytest.TempPathFactory) -> Iterator[IntegrationLab]:
    """Build a session-scoped lab and expose fixture packages on sys.path.

    Yields:
        IntegrationLab with generated local resources and two importable packages.
    """
    lab_root = tmp_path_factory.mktemp("nornflow_integration_lab")
    lab = build_integration_lab(lab_root)
    packages_path = str(lab.root / "packages")
    sys.path.insert(0, packages_path)
    yield lab
    if packages_path in sys.path:
        sys.path.remove(packages_path)


@pytest.fixture
def nornflow_lab(integration_lab: IntegrationLab) -> NornFlow:
    """Initialize NornFlow against the integration lab with Nornir startup mocked.

    Args:
        integration_lab: Session-scoped lab fixture.

    Returns:
        Initialized NornFlow instance with all catalogs loaded.
    """
    Jinja2Service._instance = None
    Jinja2Service._initialized = False

    with patch("nornflow.nornflow.NornFlow._initialize_nornir"):
        return NornFlow(nornflow_settings=integration_lab.settings)
