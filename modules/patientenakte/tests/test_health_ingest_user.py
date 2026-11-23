"""Tests H2: /ingest legt Daten unter dem konfigurierten User ab, nicht unter ?user=."""
from __future__ import annotations


def test_ingest_ignoriert_user_query_param(client, monkeypatch):
    """Regression H2: ein angreifergesteuerter ?user= darf user_id NICHT bestimmen."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "till")

    captured: dict = {}
    import backend.health_routes as mod

    def fake_insert(**kwargs):
        captured.update(kwargs)
        return "rec1"

    monkeypatch.setattr(mod.health_db, "insert", fake_insert)

    r = client.post(
        "/api/modules/patientenakte/health-data/ingest?user=angreifer",
        json={"data": {"metrics": [], "workouts": []}},
        headers={"X-HH-Health-Key": "k"},
    )

    assert r.status_code == 200
    assert captured["user_id"] == "till"


def test_ingest_nutzt_konfigurierten_user(client, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "alice")

    captured: dict = {}
    import backend.health_routes as mod

    def fake_insert(**kwargs):
        captured.update(kwargs)
        return "rec1"

    monkeypatch.setattr(mod.health_db, "insert", fake_insert)

    r = client.post(
        "/api/modules/patientenakte/health-data/ingest",
        json={"data": {"metrics": [], "workouts": []}},
        headers={"X-HH-Health-Key": "k"},
    )

    assert r.status_code == 200
    assert captured["user_id"] == "alice"


def test_ingest_falscher_key_401(client, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")

    r = client.post(
        "/api/modules/patientenakte/health-data/ingest",
        json={"data": {"metrics": [], "workouts": []}},
        headers={"X-HH-Health-Key": "falsch"},
    )

    assert r.status_code == 401


# --- #207 Schritt 2: ?key=-Query entfernt — Secret darf nicht in Access-Logs --

def test_ingest_query_key_wird_abgelehnt(client, monkeypatch):
    """#207: Der ?key=-Query-Pfad ist entfernt. Ein Key im Query authentifiziert
    nicht mehr → 401 (verhindert Secret-Leak in Access-/Proxy-Logs)."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "till")
    import backend.health_routes as mod
    monkeypatch.setattr(mod.health_db, "insert", lambda **kw: "rec1")

    r = client.post(
        "/api/modules/patientenakte/health-data/ingest?key=k",
        json={"data": {"metrics": [], "workouts": []}},
    )
    assert r.status_code == 401


def test_ingest_header_key_funktioniert_weiter(client, monkeypatch):
    """#207: Der etablierte Header-Weg bleibt unverändert funktionsfähig."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "till")
    import backend.health_routes as mod
    monkeypatch.setattr(mod.health_db, "insert", lambda **kw: "rec1")

    r = client.post(
        "/api/modules/patientenakte/health-data/ingest",
        json={"data": {"metrics": [], "workouts": []}},
        headers={"X-HH-Health-Key": "k"},
    )
    assert r.status_code == 200


def test_ingest_bearer_key_funktioniert_weiter(client, monkeypatch):
    """#207: Der Bearer-Weg (Authorization-Header) bleibt als Alternative erhalten."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "till")
    import backend.health_routes as mod
    monkeypatch.setattr(mod.health_db, "insert", lambda **kw: "rec1")

    r = client.post(
        "/api/modules/patientenakte/health-data/ingest",
        json={"data": {"metrics": [], "workouts": []}},
        headers={"Authorization": "Bearer k"},
    )
    assert r.status_code == 200


def test_ohne_ingest_nutzer_wird_nichts_abgelegt(client, monkeypatch):
    """Befund 23.11.2026: früher Standard-Nutzer 'till' – auf fremden Installationen landeten Daten unter
    einem Namen, den es dort nicht gibt. Jetzt: ohne Eintrag 409, kein Schreiben."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "")
    import backend.health_routes as mod
    called = []
    monkeypatch.setattr(mod.health_db, "insert", lambda **kw: called.append(kw) or "x")
    r = client.post("/api/modules/patientenakte/health-data/ingest",
                    json={"data": {"metrics": [], "workouts": []}}, headers={"X-HH-Health-Key": "k"})
    assert r.status_code == 409 and r.json()["detail"] == "health_ingest_user_missing"
    assert called == []
