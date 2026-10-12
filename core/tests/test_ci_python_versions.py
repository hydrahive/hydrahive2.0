"""CI testet beide unterstützten Python-Versionen (Spec python-314-umstieg).

Ubuntu 24.04 (z. B. hydratest) bleibt auf 3.12, Ubuntu 26.04 (Prod) läuft
auf 3.14. Der Job-Name ist Pflicht-Check im Branch-Schutz von main — eine
Matrix mit eigenen Namen ließe jeden PR auf einen Check warten, der nie kommt.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "pytest.yml"


def _backend() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["backend"]


def test_required_check_name_unchanged() -> None:
    job = _backend()

    assert job["name"] == "Backend (pytest + ruff)"
    assert "strategy" not in job  # keine Matrix: die erzeugt neue Check-Namen


def test_both_python_versions_set_up_and_tested() -> None:
    steps = _backend()["steps"]
    setups = [s for s in steps if str(s.get("uses", "")).startswith("actions/setup-python")]
    versions = {str(s["with"]["python-version"]) for s in setups}

    assert {"3.12", "3.14"} <= versions
    runs = " ".join(str(s.get("run", "")) for s in steps)
    assert runs.count("pytest tests/") >= 2
    assert "python3.12 -m venv" in runs and "python3.14 -m venv" in runs
