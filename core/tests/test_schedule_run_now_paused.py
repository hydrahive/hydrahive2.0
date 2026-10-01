"""„Jetzt ausführen“ bei pausierter Intervallaufgabe (Befund Bug-Tag 01.10.2026).

Vorher: API antwortete 200 {"queued": true}, claim_due nahm aber nur
enabled=1 → die Aufgabe lief nie, der Nutzer bekam keine Rückmeldung.
Jetzt: ein ausdrücklicher Startwunsch läuft genau EINMAL, auch pausiert;
danach bleibt die Aufgabe pausiert und wird nicht erneut fällig.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hydrahive.db.connection import db as _db
from hydrahive.schedules import db


def _create(client, auth_headers) -> str:
    r = client.post("/api/scheduled-tasks", headers=auth_headers, json={
        "title": "Probe", "prompt": "x", "target_type": "buddy",
        "target_id": "buddy", "interval_seconds": 3600})
    assert r.status_code == 201
    return r.json()["task_id"]


def _claimed_ids() -> list[str]:
    return [t.task_id for t, _run in db.claim_due()]


def test_pausierte_aufgabe_laeuft_auf_wunsch_einmal(client, auth_headers):
    tid = _create(client, auth_headers)
    assert client.post(f"/api/scheduled-tasks/{tid}/pause", headers=auth_headers).status_code == 200
    r = client.post(f"/api/scheduled-tasks/{tid}/run", headers=auth_headers)
    assert r.status_code == 200 and r.json()["queued"] is True
    assert tid in _claimed_ids()
    task = db.get(tid)
    assert task.enabled is False, "bleibt pausiert"


def test_pausiert_ohne_wunsch_wird_nicht_faellig(client, auth_headers):
    tid = _create(client, auth_headers)
    client.post(f"/api/scheduled-tasks/{tid}/pause", headers=auth_headers)
    past = (datetime.now(UTC) - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    with _db() as conn:
        conn.execute("UPDATE scheduled_agent_tasks SET next_run_at = ? WHERE task_id = ?", (past, tid))
    assert tid not in _claimed_ids()


def test_nach_einmal_lauf_nicht_erneut_faellig(client, auth_headers):
    tid = _create(client, auth_headers)
    client.post(f"/api/scheduled-tasks/{tid}/pause", headers=auth_headers)
    client.post(f"/api/scheduled-tasks/{tid}/run", headers=auth_headers)
    assert tid in _claimed_ids()
    with _db() as conn:  # Lauf beendet simulieren
        conn.execute("UPDATE scheduled_agent_tasks SET running = 0, next_run_at = ? WHERE task_id = ?",
                     ("1971-01-01T00:00:00Z", tid))
    assert tid not in _claimed_ids(), "pausiert + überfällig darf nicht wieder laufen"


def test_aktive_aufgabe_jetzt_ausfuehren_unveraendert(client, auth_headers):
    tid = _create(client, auth_headers)
    assert client.post(f"/api/scheduled-tasks/{tid}/run", headers=auth_headers).status_code == 200
    assert tid in _claimed_ids()
