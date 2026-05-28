"""Phase B: in-process catalog validation (no device I/O)."""

from tests.integration.containerlab.conftest import run_lab_phase
from tests.integration.containerlab.lab_project import LabEnvironment


def test_catalogs_load_nornflow_and_arista_assets(lab_environment: LabEnvironment) -> None:
    """Temp venv loads nornflow + nornflow_arista and all catalog types resolve."""
    result = run_lab_phase(lab_environment, "phase-b")
    assert result.returncode == 0, result.stderr.strip() or result.stdout.strip()
