"""CI testet beide unterstützten Python-Versionen (Spec python-314-umstieg).

Ubuntu 24.04 (z. B. hydratest) bleibt auf 3.12, Ubuntu 26.04 (Prod) läuft
auf 3.14. Zwei Jobs laufen parallel (die Suite dauert in der CI ~8 Minuten,
nacheinander wären es ~17).

Der Name des Hauptjobs ist Pflicht-Check im Branch-Schutz von main — eine
Matrix hängt die Version an den Namen an, dann wartete jeder PR auf einen
Check, der nie kommt.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "pytest.yml"


def _jobs() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


def _python(job: dict) -> str:
    setups = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/setup-python")]
    assert len(setups) == 1
    return str(setups[0]["with"]["python-version"])


def _runs_pytest(job: dict) -> bool:
    return any("pytest tests/" in str(s.get("run", "")) for s in job["steps"])


def test_required_check_name_unchanged_and_on_314() -> None:
    job = _jobs()["backend"]

    assert job["name"] == "Backend (pytest + ruff)"
    assert "strategy" not in job
    assert _python(job) == "3.14"
    assert _runs_pytest(job)


def test_312_tested_in_parallel_job() -> None:
    tested = {_python(job) for job in _jobs().values() if _runs_pytest(job)}

    assert tested == {"3.12", "3.14"}
