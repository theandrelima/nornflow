"""Integration tests for store_as simple mode vs result-path equivalence."""

import nornflow.builtins.hooks  # noqa: F401 — populate builtin hooks in HOOKS_CATALOG
import nornflow.builtins.tasks  # noqa: F401 — populate builtin tasks in TASKS_CATALOG
import pytest

from nornflow.j2 import Jinja2Service
from nornflow.nornflow import NornFlow

from tests.integration.store_as_lab import (
    STORE_AS_ECHO_MESSAGE,
    STORE_AS_HOST_NAME,
    WORKFLOW_RESULT_PATH,
    WORKFLOW_SIMPLE_MODE,
    StoreAsIntegrationLab,
    build_store_as_integration_lab,
)


@pytest.fixture(scope="module")
def store_as_lab(tmp_path_factory: pytest.TempPathFactory) -> StoreAsIntegrationLab:
    """Session-scoped minimal NornFlow project with store_as workflows."""
    lab_root = tmp_path_factory.mktemp("store_as_integration_lab")
    return build_store_as_integration_lab(lab_root)


def _reset_jinja2_singleton() -> None:
    """Reset Jinja2Service singleton between NornFlow runs."""
    Jinja2Service._instance = None
    Jinja2Service._initialized = False


def _run_workflow(lab: StoreAsIntegrationLab, workflow_file: str) -> NornFlow:
    """Execute a workflow file and assert success.

    Args:
        lab: Generated integration lab.
        workflow_file: Workflow filename in the lab workflows directory.

    Returns:
        NornFlow instance after run() completes.

    Raises:
        AssertionError: If run() returns a non-zero exit code.
    """
    _reset_jinja2_singleton()
    nornflow = NornFlow(nornflow_settings=lab.settings, workflow=workflow_file)
    exit_code = nornflow.run()
    assert exit_code == 0, f"Workflow {workflow_file} failed with exit code {exit_code}"
    return nornflow


class TestStoreAsSimpleModeEquivalence:
    """End-to-end store_as: simple mode vs extraction path result."""

    def test_store_as_simple_and_result_path_same_variable(
        self, store_as_lab: StoreAsIntegrationLab
    ) -> None:
        """store_as: var and store_as: {var: result} store identical runtime values."""
        simple_run = _run_workflow(store_as_lab, WORKFLOW_SIMPLE_MODE)
        result_path_run = _run_workflow(store_as_lab, WORKFLOW_RESULT_PATH)

        vars_manager_simple = simple_run.var_processor.vars_manager
        vars_manager_result = result_path_run.var_processor.vars_manager

        payload_a = vars_manager_simple.get_nornflow_variable("payload_a", STORE_AS_HOST_NAME)
        payload_b = vars_manager_result.get_nornflow_variable("payload_b", STORE_AS_HOST_NAME)

        assert payload_a == STORE_AS_ECHO_MESSAGE
        assert payload_b == STORE_AS_ECHO_MESSAGE
        assert payload_a == payload_b

        echo_back_a = vars_manager_simple.get_nornflow_variable("echo_back_a", STORE_AS_HOST_NAME)
        echo_back_b = vars_manager_result.get_nornflow_variable("echo_back_b", STORE_AS_HOST_NAME)

        assert echo_back_a == STORE_AS_ECHO_MESSAGE
        assert echo_back_b == STORE_AS_ECHO_MESSAGE
