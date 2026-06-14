"""Containerlab integration tests for output masking on CLI, logs, and inventory display."""

import os
from pathlib import Path

import pytest

from nornflow.masking import REDACTED

from tests.integration.containerlab.conftest import run_nornflow_cli
from tests.integration.containerlab.constants import (
    LAB_MASKING_CREDENTIAL_SECRET,
    LAB_MASKING_SENSITIVE_NAME,
    LAB_MASKING_VISIBLE_LABEL,
    LAB_OUTPUT_MASKING_WORKFLOW,
    LAB_PREFLIGHT_HOST,
)
from tests.integration.containerlab.lab_project import LabEnvironment


def _combined_output(result: object) -> str:
    proc = result
    return f"{proc.stdout or ''}\n{proc.stderr or ''}"


def _workflow_log_files(lab: LabEnvironment) -> list[Path]:
    """Return log files for the output-masking workflow (most recent last)."""
    log_dir = lab.project_root / ".nornflow" / "logs"
    return sorted(log_dir.glob("Containerlab_output_masking_*.log"))


@pytest.fixture(scope="module")
def lab_password(lab_environment: LabEnvironment) -> str:
    """Device password injected into generated inventory (built-in keyword masking)."""
    password = os.environ.get("NORNFLOW_LAB_PASSWORD", "").strip()
    assert password, "NORNFLOW_LAB_PASSWORD must be set when NORNFLOW_LAB=1"
    return password


class TestContainerlabOutputMasking:
    """Live-lab checks for redaction.sensitive_names and built-in keyword masking."""

    def test_show_nornir_configs_does_not_expose_inventory_credentials(
        self,
        lab_environment: LabEnvironment,
        lab_password: str,
    ) -> None:
        """show --nornir-configs renders config.yaml only, not hosts.yaml secrets."""
        result = run_nornflow_cli(lab_environment, ["show", "--nornir-configs"])
        output = _combined_output(result)

        assert result.returncode == 0, output
        assert lab_password not in output
        assert LAB_MASKING_CREDENTIAL_SECRET not in output
        assert "hosts.yaml" in output
        assert LAB_PREFLIGHT_HOST not in output

    def test_show_settings_lists_sensitive_names_without_secret_values(
        self,
        lab_environment: LabEnvironment,
    ) -> None:
        """Settings display may show identifier names but never secret values."""
        result = run_nornflow_cli(lab_environment, ["show", "--settings"])
        output = _combined_output(result)

        assert result.returncode == 0, output
        assert LAB_MASKING_SENSITIVE_NAME in output
        assert LAB_MASKING_CREDENTIAL_SECRET not in output

    def test_inventory_on_disk_has_credentials_not_shown_by_show(
        self,
        lab_environment: LabEnvironment,
        lab_password: str,
    ) -> None:
        """Hosts inventory contains secrets on disk; show --nornir-configs does not dump them."""
        hosts_path = lab_environment.project_root / "nornir_configs" / "hosts.yaml"
        hosts_text = hosts_path.read_text()

        assert lab_password in hosts_text
        assert LAB_MASKING_CREDENTIAL_SECRET in hosts_text
        assert LAB_PREFLIGHT_HOST in hosts_text

        result = run_nornflow_cli(lab_environment, ["show", "--nornir-configs"])
        output = _combined_output(result)

        assert result.returncode == 0, output
        assert lab_password not in output
        assert LAB_MASKING_CREDENTIAL_SECRET not in output

    def test_run_workflow_masks_sensitive_names_and_password_on_stdout(
        self,
        lab_environment: LabEnvironment,
        lab_password: str,
    ) -> None:
        """Task stdout must redact credential_x vars and password= inventory output."""
        result = run_nornflow_cli(lab_environment, ["run", LAB_OUTPUT_MASKING_WORKFLOW])
        output = _combined_output(result)

        assert result.returncode == 0, output
        assert LAB_MASKING_CREDENTIAL_SECRET not in output
        assert lab_password not in output
        assert REDACTED in output
        assert LAB_MASKING_VISIBLE_LABEL in output
        assert LAB_PREFLIGHT_HOST in output

    def test_run_workflow_masks_sensitive_names_in_log_file(
        self,
        lab_environment: LabEnvironment,
        lab_password: str,
    ) -> None:
        """Log files must not contain raw credential_x or password values."""
        result = run_nornflow_cli(lab_environment, ["run", LAB_OUTPUT_MASKING_WORKFLOW])
        assert result.returncode == 0, _combined_output(result)

        workflow_logs = _workflow_log_files(lab_environment)
        assert workflow_logs, "Expected a workflow log file after run"
        log_text = workflow_logs[-1].read_text()
        assert LAB_MASKING_CREDENTIAL_SECRET not in log_text
        assert lab_password not in log_text

    def test_run_no_redact_reveals_secrets_on_stdout(
        self,
        lab_environment: LabEnvironment,
        lab_password: str,
    ) -> None:
        """--no-redact disables terminal masking for workflow task output."""
        result = run_nornflow_cli(
            lab_environment,
            ["run", LAB_OUTPUT_MASKING_WORKFLOW, "--no-redact"],
        )
        output = _combined_output(result)

        assert result.returncode == 0, output
        assert "Warning: Terminal output redaction is disabled" in output
        assert lab_password in output
        assert LAB_MASKING_CREDENTIAL_SECRET in output
