"""GET /api/system/update/log: Gesamtzahl + Lesen ab Zeile (Update-Fenster wertet nur DIESEN Lauf aus)."""
from __future__ import annotations


def _log(monkeypatch, tmp_path, text: str):
    from hydrahive.api.routes import system_admin
    p = tmp_path / "hydrahive2-update.log"
    p.write_text(text)
    monkeypatch.setattr(system_admin, "UPDATE_LOG", p)
    return p


def test_total_is_reported(client, admin_headers, monkeypatch, tmp_path):
    _log(monkeypatch, tmp_path, "a\nb\nc\n")
    r = client.get("/api/system/update/log", headers=admin_headers).json()
    assert r["total"] == 3 and r["lines"] == ["a\n", "b\n", "c\n"]


def test_since_returns_only_new_lines(client, admin_headers, monkeypatch, tmp_path):
    p = _log(monkeypatch, tmp_path, "alt1\nalt2\n")
    start = client.get("/api/system/update/log", headers=admin_headers).json()["total"]
    p.write_text("alt1\nalt2\nneu1\nHH-UPDATE-ENDE: ok\n")
    r = client.get(f"/api/system/update/log?since={start}", headers=admin_headers).json()
    assert r["lines"] == ["neu1\n", "HH-UPDATE-ENDE: ok\n"] and r["total"] == 4


def test_since_beyond_end_after_rotation_returns_all(client, admin_headers, monkeypatch, tmp_path):
    _log(monkeypatch, tmp_path, "x\n")
    r = client.get("/api/system/update/log?since=50", headers=admin_headers).json()
    assert r["lines"] == ["x\n"]


def test_since_is_capped_by_tail(client, admin_headers, monkeypatch, tmp_path):
    _log(monkeypatch, tmp_path, "".join(f"z{i}\n" for i in range(2000)))
    r = client.get("/api/system/update/log?since=0&tail=50", headers=admin_headers).json()
    assert len(r["lines"]) == 50 and r["lines"][-1] == "z1999\n" and r["total"] == 2000


def test_missing_log(client, admin_headers, monkeypatch, tmp_path):
    from hydrahive.api.routes import system_admin
    monkeypatch.setattr(system_admin, "UPDATE_LOG", tmp_path / "fehlt.log")
    r = client.get("/api/system/update/log", headers=admin_headers).json()
    assert r["exists"] is False and r["lines"] == [] and r["total"] == 0


def test_requires_admin(client, auth_headers):
    assert client.get("/api/system/update/log", headers=auth_headers).status_code in (401, 403)
