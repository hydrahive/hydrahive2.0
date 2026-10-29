"""Testreihe auf mehreren Kernen (Spec docs/specs/pytest-parallel.md).

Nacheinander dauert die Reihe 8:20 min auf dem Server und 13–14 min je CI-Job. Mit pytest-xdist sind es 1:20 min bzw.
ein Bruchteil. Die Jobnamen sind Pflicht-Checks im Branch-Schutz – sie dürfen sich nicht ändern.
"""
from __future__ import annotations

import re
import shlex
import tomllib
from pathlib import Path

import yaml

CORE = Path(__file__).resolve().parents[1]
WORKFLOW = CORE.parent / ".github" / "workflows" / "pytest.yml"
JOB_NAMES = {"backend": "Backend (pytest + ruff)", "backend-py312": "Backend (pytest, Python 3.12)"}


def _pytest_args(job: dict) -> list[str]:
    runs = [str(s.get("run", "")) for s in job["steps"] if "pytest tests/" in str(s.get("run", ""))]
    assert len(runs) == 1, runs
    line = next(x for x in runs[0].splitlines() if "pytest tests/" in x)
    args = shlex.split(line)
    return args[args.index("pytest"):]


def test_xdist_steht_mit_deckel_in_den_abhaengigkeiten() -> None:
    deps = tomllib.loads((CORE / "pyproject.toml").read_text())["project"]["dependencies"]
    xdist = [d for d in deps if re.match(r"pytest-xdist\b", d)]
    assert xdist == ["pytest-xdist>=3.6,<4"], deps


def test_beide_ci_jobs_laufen_parallel_mit_gleichen_namen() -> None:
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    for key, name in JOB_NAMES.items():
        assert jobs[key]["name"] == name
        args = _pytest_args(jobs[key])
        assert "-n" in args and args[args.index("-n") + 1] == "auto", (key, args)


def test_lokal_ohne_n_bleibt_ein_einzelner_prozess() -> None:
    """Ein einzelner Test soll nicht erst 16 Prozesse starten – -n nur dort, wo die volle Reihe läuft."""
    opts = tomllib.loads((CORE / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert not re.search(r"(^|\s)(-n|--numprocesses)\b", str(opts.get("addopts", ""))), opts
