"""Fixtures für „lokale Kopie löschen“ (Spec archiv-system.md, Etappe 3b).

Eingebunden per `pytest_plugins = ["tests._delete_env", "tests._remote_env", "tests._drop_env"]`.
`drop_jobs`: Auftrags-Reihe nur einreihen, im Test selbst abarbeiten. `on_server(n)`: n Pakete, die geprüft
auf dem Server liegen.
"""
from __future__ import annotations

import pytest

from tests._delete_fixtures import make_agent, packages


@pytest.fixture
def drop_jobs(monkeypatch):
    from hydrahive.archive import jobs
    monkeypatch.setattr(jobs, "_start_worker", lambda: None)
    jobs.reset_for_tests()
    yield jobs
    jobs.reset_for_tests()


@pytest.fixture
def on_server(archive_root, remote_on, remote_queue):
    """Erzeugt Pakete und lädt sie hoch. Gibt die Pfade relativ zum Archiv zurück (z. B. agents/…tar.gz)."""
    from hydrahive.archive import deletion

    def make(n: int = 1) -> list[str]:
        before = set(packages(archive_root, "agents"))
        for i in range(n):
            a = make_agent(f"Server {i}")
            assert deletion.run("agent", a["id"], "archive", actor="admin")["state"] == "done"
        remote_queue.process_queue()
        new = sorted(set(packages(archive_root, "agents")) - before)
        return [f"agents/{p.name}" for p in new]

    return make
