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
