"""Welche Auftragsart läuft wie, und wie wird sie nach einem Neustart zurückgerollt (ausgelagert aus jobs.py).

Arten: Löschen (agent/project/user/instance/orphan_agent), Waisen-Ordner (orphans), lokale Kopie löschen
(drop_local, Etappe 3b).
"""
from __future__ import annotations


def run(job: dict) -> dict:
    from hydrahive.archive import _orphan_run, deletion, drop_local
    if job["kind"] == "orphans":
        return _orphan_run.execute(job)
    if job["kind"] == drop_local.TARGET:
        return drop_local.execute(job)
    return deletion.execute(job)


def rollback(job: dict) -> None:
    """Auftrag vor dem endgültigen Löschen unterbrochen: alles wie vorher (fertige Teile bleiben)."""
    from hydrahive.archive import _orphan_run, deletion, drop_local
    if job.get("kind") == "orphans":
        _orphan_run.rollback(job)                  # fertig entfernte Ordner bleiben im Archiv
    elif job.get("kind") == drop_local.TARGET:
        drop_local.rollback(job)                   # schon gelöschte Kopien bleiben gelöscht
    else:
        deletion.rollback_lock(job)
