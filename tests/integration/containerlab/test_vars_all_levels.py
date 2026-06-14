"""Phase B/C: variable levels and Jinja2 filters via echo-only workflow."""

import pytest

from tests.integration.containerlab.conftest import run_nornflow_cli
from tests.integration.containerlab.constants import (
    LAB_VARS_ALL_LEVELS_WORKFLOW,
    LAB_VARS_ENV_VALUE,
    LAB_VARS_ENV_VAR,
)
from tests.integration.containerlab.lab_project import LabEnvironment
from tests.integration.fixtures.constants import (
    VARS_CLI_MARKER,
    VARS_DOMAIN_MARKER,
    VARS_GLOBAL_MARKER,
    VARS_RUNTIME_MARKER,
    VARS_WORKFLOW_MARKER,
)


def test_vars_all_levels_and_j2_filters(lab_environment: LabEnvironment, monkeypatch: pytest.MonkeyPatch) -> None:
    """Echo workflow resolves env, global, domain, workflow, CLI, runtime vars and j2 filters."""
    monkeypatch.setenv(f"NORNFLOW_VAR_{LAB_VARS_ENV_VAR}", LAB_VARS_ENV_VALUE)

    result = run_nornflow_cli(
        lab_environment,
        [
            "run",
            LAB_VARS_ALL_LEVELS_WORKFLOW,
            "--vars",
            f"cli_marker={VARS_CLI_MARKER}",
        ],
        stream=False,
    )
    output = f"{result.stdout or ''}{result.stderr or ''}"
    assert result.returncode == 0, output

    for needle in (
        f"env={LAB_VARS_ENV_VALUE}",
        f"global={VARS_GLOBAL_MARKER}",
        f"domain={VARS_DOMAIN_MARKER}",
        f"workflow={VARS_WORKFLOW_MARKER}",
        f"cli={VARS_CLI_MARKER}",
        f"runtime={VARS_RUNTIME_MARKER}",
        "override=RUNTIME_OK",
        "j2_package=10-20",
        "j2_builtin=True",
        "j2_local=LAB:vars",
    ):
        assert needle in output, f"Expected {needle!r} in workflow output"
