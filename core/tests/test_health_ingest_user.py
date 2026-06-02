"""Tests H2: /ingest legt Daten unter dem konfigurierten User ab, nicht unter ?user=."""
from __future__ import annotations


def test_ingest_ignoriert_user_query_param(client, monkeypatch):
    """Regression H2: ein angreifergesteuerter ?user= darf user_id NICHT bestimmen."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "till")

    captured: dict = {}
    import hydrahive.api.routes.health_data as mod

    def fake_insert(**kwargs):
        captured.update(kwargs)
        return "rec1"

    monkeypatch.setattr(mod.health_db, "insert", fake_insert)

    r = client.post(
        "/api/health-data/ingest?user=angreifer",
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
    import hydrahive.api.routes.health_data as mod

    def fake_insert(**kwargs):
        captured.update(kwargs)
        return "rec1"

    monkeypatch.setattr(mod.health_db, "insert", fake_insert)

    r = client.post(
        "/api/health-data/ingest",
        json={"data": {"metrics": [], "workouts": []}},
        headers={"X-HH-Health-Key": "k"},
    )

    assert r.status_code == 200
    assert captured["user_id"] == "alice"


def test_ingest_falscher_key_401(client, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")

    r = client.post(
        "/api/health-data/ingest",
        json={"data": {"metrics": [], "workouts": []}},
        headers={"X-HH-Health-Key": "falsch"},
    )

    assert r.status_code == 401


# --- #207 Schritt 1: ?key=-Query loggt Deprecation, bricht aber nicht --------

def test_ingest_query_key_logs_deprecation_warning(client, monkeypatch, caplog):
    import logging

    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "till")
    import hydrahive.api.routes.health_data as mod
    monkeypatch.setattr(mod.health_db, "insert", lambda **kw: "rec1")

    with caplog.at_level(logging.WARNING, logger="hydrahive.api.routes.health_data"):
        r = client.post(
            "/api/health-data/ingest?key=k",
            json={"data": {"metrics": [], "workouts": []}},
        )
    assert r.status_code == 200  # weiter funktionsfähig — kein Bruch
    assert any("?key=" in rec.message for rec in caplog.records)


def test_ingest_header_key_no_deprecation_warning(client, monkeypatch, caplog):
    import logging

    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "health_api_key", "k")
    monkeypatch.setattr(settings, "health_ingest_user", "till")
    import hydrahive.api.routes.health_data as mod
    monkeypatch.setattr(mod.health_db, "insert", lambda **kw: "rec1")

    with caplog.at_level(logging.WARNING, logger="hydrahive.api.routes.health_data"):
        r = client.post(
            "/api/health-data/ingest",
            json={"data": {"metrics": [], "workouts": []}},
            headers={"X-HH-Health-Key": "k"},
        )
    assert r.status_code == 200
    assert not any("?key=" in rec.message for rec in caplog.records)
