"""Unit test: conditional rollback workflow via store_as failed flag + if hook."""

import shutil
import sys
from pathlib import Path

import nornflow.builtins.hooks  # noqa: F401
import nornflow.builtins.tasks  # noqa: F401
import pytest

from nornflow.j2 import Jinja2Service
from nornflow.nornflow import NornFlow
from nornflow.settings import NornFlowSettings

from tests.integration.fixtures.constants import STORE_AS_FAILURE_MARKER, WORKFLOW_STORE_AS_FAILURE
from tests.integration.project_bootstrap import FIXTURES_COMMON, bootstrap_nornflow_project

HOST_NAME = "localhost"


def _dev_nornflow_cli() -> Path:
    cli = shutil.which("nornflow")
    if cli:
        return Path(cli)
    return Path(sys.executable).parent / "nornflow"


def _write_single_host(hosts_path: Path) -> None:
    hosts_path.write_text(f"{HOST_NAME}:\n  hostname: 127.0.0.1\n  data: {{}}\n")


@pytest.fixture(scope="module")
def rollback_lab(tmp_path_factory: pytest.TempPathFactory) -> NornFlowSettings:
    """Bootstrapped project with static store_as failure-path workflow."""
    lab_root = tmp_path_factory.mktemp("store_as_rollback_unit")
    settings_file = bootstrap_nornflow_project(
        lab_root,
        nornflow_executable=_dev_nornflow_cli(),
        overlay_dirs=[FIXTURES_COMMON],
        write_hosts=_write_single_host,
    )
    return NornFlowSettings.load(str(settings_file), base_dir=lab_root)


def _reset_jinja2_singleton() -> None:
    Jinja2Service._instance = None
    Jinja2Service._initialized = False


class TestStoreAsConditionalRollbackWorkflow:
    """End-to-end workflow: failed write_file -> step_failed -> conditional echo."""

    def test_failure_path_stores_flag_and_runs_rollback_echo(self, rollback_lab: NornFlowSettings) -> None:
        """Matches the documented conditional rollback YAML pattern."""
        _reset_jinja2_singleton()
        nornflow = NornFlow(nornflow_settings=rollback_lab, workflow=WORKFLOW_STORE_AS_FAILURE)
        nornflow.run()

        vars_manager = nornflow.var_processor.vars_manager
        assert vars_manager.get_nornflow_variable("step_failed", HOST_NAME) is True
        assert vars_manager.get_nornflow_variable("rollback_msg", HOST_NAME) == STORE_AS_FAILURE_MARKER
