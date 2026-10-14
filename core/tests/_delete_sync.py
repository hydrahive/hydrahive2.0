"""Lösch-Routen in Tests sofort abarbeiten (Spec archiv-system.md, Etappe 2).

Die vier DELETE-Routen geben seit Etappe 2 nur noch 202 + Auftrag zurück, gelöscht wird im
Hintergrund-Thread. Für Tests, die das Ergebnis prüfen: `delete_now(client, url, name, headers)`
startet „unwiderruflich“ mit dem Namen und arbeitet die Reihe gleich im Test-Thread ab.
"""
from __future__ import annotations


def delete_now(client, url: str, name: str, headers: dict, monkeypatch) -> dict:
    from hydrahive.archive import jobs
    monkeypatch.setattr(jobs, "_start_worker", lambda: None)
    r = client.delete(url, headers=headers, params={"mode": "permanent", "confirm": name})
    assert r.status_code == 202, r.text
    jobs.process_queue()
    [job] = [j for j in jobs.list_jobs()["done"] if j["id"] == r.json()["job_id"]]
    assert job["state"] == "done", job
    return job
