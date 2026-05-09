"""Regression-Test: literale VM-Pfade dürfen NICHT von /{vm_id} geshadowed werden.

Bug-Historie: vor dem Fix war /api/vms/import-jobs als zweite Route registriert
(nach /{vm_id}), wodurch GET /import-jobs in vm_or_404("import-jobs") landete
und 404 vm_not_found warf. Frontend-Panel pollte ins Nichts, Import-Jobs waren
unsichtbar obwohl die DB-Einträge existierten.
"""
from __future__ import annotations


def test_literal_vms_routes_before_vm_id_param():
    """In app.routes muss jede literale /api/vms/<word>-Route VOR /api/vms/{vm_id} stehen."""
    from hydrahive.api.main import app

    vm_routes = [
        (r.path, getattr(r, "methods", set()))
        for r in app.routes
        if r.path.startswith("/api/vms")
    ]
    paths_in_order = [p for p, _ in vm_routes]

    # Index der Catch-All-Routen — alles davor muss noch literal sein,
    # alles danach darf parametrisiert sein.
    try:
        catchall_idx = paths_in_order.index("/api/vms/{vm_id}")
    except ValueError:
        # Wenn die Catch-All-Route nicht existiert, ist nichts zu prüfen.
        return

    # Alle literalen /api/vms/<wort>-Routen (z. B. /api/vms/import-jobs,
    # /api/vms/isos/list) müssen mit Index < catchall_idx vorkommen.
    literal_paths = [
        "/api/vms/import-jobs",
        "/api/vms/import-jobs/upload",
        "/api/vms/import-jobs/from-path",
        "/api/vms/isos/list",
        "/api/vms/isos/upload",
    ]
    for lit in literal_paths:
        if lit not in paths_in_order:
            continue  # nicht jede Route muss existieren — nur prüfen wenn da
        lit_idx = paths_in_order.index(lit)
        assert lit_idx < catchall_idx, (
            f"Route {lit} (idx {lit_idx}) wird von /api/vms/{{vm_id}} "
            f"(idx {catchall_idx}) geshadowed — Reihenfolge in vms.py kaputt"
        )


def test_get_import_jobs_returns_200_not_404(client, admin_headers):
    """End-to-End: GET /api/vms/import-jobs liefert leere Liste, NICHT 404."""
    r = client.get("/api/vms/import-jobs", headers=admin_headers)
    assert r.status_code == 200, (
        f"Expected 200, got {r.status_code}: {r.text}"
    )
    assert isinstance(r.json(), list)


def test_get_isos_list_returns_200_not_404(client, admin_headers):
    """End-to-End: GET /api/vms/isos/list darf nicht von /{vm_id} geshadowed sein."""
    r = client.get("/api/vms/isos/list", headers=admin_headers)
    assert r.status_code == 200, (
        f"Expected 200, got {r.status_code}: {r.text}"
    )
    assert isinstance(r.json(), list)
