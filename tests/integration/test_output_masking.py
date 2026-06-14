"""Integration tests for output masking during workflow execution."""

from pathlib import Path

import nornflow.builtins.hooks  # noqa: F401 — populate builtin hooks in HOOKS_CATALOG
import nornflow.builtins.tasks  # noqa: F401 — populate builtin tasks in TASKS_CATALOG
import pytest

from nornflow.j2 import Jinja2Service
from nornflow.logger import logger
from nornflow.masking import REDACTED
from nornflow.nornflow import NornFlow

from tests.integration.fixtures.constants import (
    INTEGRATION_MASKING_CREDENTIAL_SECRET,
    WORKFLOW_MASKING_CREDENTIAL_ECHO,
    WORKFLOW_MASKING_TOKEN_ECHO,
)
from tests.integration.output_masking_lab import (
    OutputMaskingIntegrationLab,
    build_output_masking_integration_lab,
)


@pytest.fixture(scope="module")
def masking_lab(tmp_path_factory: pytest.TempPathFactory) -> OutputMaskingIntegrationLab:
    """Session-scoped minimal NornFlow project with a token-bearing echo workflow."""
    lab_root = tmp_path_factory.mktemp("output_masking_integration_lab")
    return build_output_masking_integration_lab(lab_root)


def _reset_jinja2_singleton() -> None:
    """Reset Jinja2Service singleton between NornFlow runs."""
    Jinja2Service._instance = None
    Jinja2Service._initialized = False


class TestOutputMaskingIntegration:
    """End-to-end masking during workflow stdout and log output."""

    def test_echo_workflow_masks_token_in_stdout(
        self, masking_lab: OutputMaskingIntegrationLab, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Token vars echoed as api_token= must not appear verbatim on stdout."""
        _reset_jinja2_singleton()
        nornflow = NornFlow(
            nornflow_settings=masking_lab.settings,
            workflow=WORKFLOW_MASKING_TOKEN_ECHO,
        )
        exit_code = nornflow.run()
        assert exit_code == 0

        captured = capsys.readouterr()
        assert masking_lab.secret_value not in captured.out
        assert REDACTED in captured.out

    def test_echo_workflow_masks_token_in_log_file(
        self, masking_lab: OutputMaskingIntegrationLab, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Log file written during execution must not contain the raw token value."""
        _reset_jinja2_singleton()
        nornflow = NornFlow(
            nornflow_settings=masking_lab.settings,
            workflow=WORKFLOW_MASKING_TOKEN_ECHO,
        )
        exit_code = nornflow.run()
        assert exit_code == 0
        capsys.readouterr()

        ctx = logger.get_execution_context()
        assert ctx is not None
        log_text = Path(ctx["log_file"]).read_text()
        assert masking_lab.secret_value not in log_text

    def test_echo_workflow_masks_credential_x_in_stdout(
        self, masking_lab: OutputMaskingIntegrationLab, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """User-declared sensitive_names must redact vars not covered by built-ins."""
        _reset_jinja2_singleton()
        nornflow = NornFlow(
            nornflow_settings=masking_lab.settings,
            workflow=WORKFLOW_MASKING_CREDENTIAL_ECHO,
        )
        exit_code = nornflow.run()
        assert exit_code == 0

        captured = capsys.readouterr()
        assert INTEGRATION_MASKING_CREDENTIAL_SECRET not in captured.out
        assert REDACTED in captured.out
        assert "integration-visible" in captured.out
