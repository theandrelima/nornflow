"""Integration test: store_as failure flag enables conditional follow-up task."""

import nornflow.builtins.hooks  # noqa: F401
import nornflow.builtins.tasks  # noqa: F401
import pytest

from nornflow.j2 import Jinja2Service
from nornflow.nornflow import NornFlow

from tests.integration.fixtures.constants import STORE_AS_FAILURE_MARKER
from tests.integration.store_as_lab import (
    STORE_AS_HOST_NAME,
    WORKFLOW_FAILURE_PATH,
    StoreAsIntegrationLab,
    build_store_as_integration_lab,
)


@pytest.fixture(scope="module")
def store_as_lab(tmp_path_factory: pytest.TempPathFactory) -> StoreAsIntegrationLab:
    """Module-scoped project bootstrapped via nornflow init + static fixtures."""
    lab_root = tmp_path_factory.mktemp("store_as_failure_integration")
    return build_store_as_integration_lab(lab_root)


def _reset_jinja2_singleton() -> None:
    """Reset Jinja2Service singleton between NornFlow runs."""
    Jinja2Service._instance = None
    Jinja2Service._initialized = False


def test_store_as_failure_path_enables_conditional_echo(store_as_lab: StoreAsIntegrationLab) -> None:
    """write_file fails, store_as saves step_failed, if-hook echo runs and stores rollback_msg."""
    _reset_jinja2_singleton()
    nornflow = NornFlow(nornflow_settings=store_as_lab.settings, workflow=WORKFLOW_FAILURE_PATH)
    nornflow.run()

    vars_manager = nornflow.var_processor.vars_manager
    assert vars_manager.get_nornflow_variable("step_failed", STORE_AS_HOST_NAME) is True
    assert vars_manager.get_nornflow_variable("rollback_msg", STORE_AS_HOST_NAME) == STORE_AS_FAILURE_MARKER
