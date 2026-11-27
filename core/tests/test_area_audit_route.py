"""Agenten-Bereiche, Aufgabe 7 (AB8, Backend): ``GET /api/admin/area-audit`` – das Protokoll in Bereichssprache (Spec 4.7).

Nur Admin. Gefiltert wird nach ``action`` (Review #789 M5), nie nach ``target``: ein ``user_purge``- oder Gruppen-Eintrag darf
nicht erscheinen. Die Tool-Namen im ``detail`` werden auf Bereichsnamen abgebildet; Tool-Namen stehen nur in ``tools``.
"""
from __future__ import annotations

import pytest

from hydrahive.access.store import audit
from hydrahive.db.connection import db
from tests._own_rows import only_own_rows

ACTIONS = ("tool_pool_set", "tool_grants_set", "tool_category_approve", "tool_category_revoke")


@pytest.fixture(autouse=True)
def _sauber(setup_test_env):
    from hydrahive.db import init_db
    init_db()
    with only_own_rows("access_audit"):
        yield


def _eintrag(action: str, target: str, detail: str = "", actor: str = "u-test") -> None:
    with db() as conn:
        audit(conn, actor, action, target, detail)


def _get(client, headers, **q):
    qs = "&".join(f"{k}={v}" for k, v in q.items())
    return client.get(f"/api/admin/area-audit{'?' + qs if qs else ''}", headers=headers)


def test_area_audit_nur_admin(client, auth_headers, admin_headers):
    _eintrag("tool_pool_set", "agent:a1", "file_read")
    assert client.get("/api/admin/area-audit").status_code == 401
    assert _get(client, auth_headers).status_code == 403
    r = _get(client, admin_headers)
    assert r.status_code == 200 and "entries" in r.json()


def test_area_audit_filtert_nach_action(client, admin_headers):
    """Ein user_purge-Eintrag (und andere Aktionen) erscheint nicht – auch wenn das target nach Pool aussieht."""
    _eintrag("user_purge", "user:geheim", "alles weg")
    _eintrag("user_purge", "agent:a1", "file_read")                               # target wie ein Pool-Eintrag
    _eintrag("group_create", "group:g1", "Gruppe")
    for a in ACTIONS:
        _eintrag(a, "agent:a1", "file_read")
    got = _get(client, admin_headers).json()["entries"]
    actions = {e["action"] for e in got}
    assert actions == set(ACTIONS)
    assert "user_purge" not in actions and "group_create" not in actions
    assert "geheim" not in str(got) and "alles weg" not in str(got)


def test_area_audit_uebersetzt_bereiche(client, admin_headers):
    _eintrag("tool_pool_set", "agent:a1", "file_read, read_document, web_search, shell_exec")
    e = _get(client, admin_headers).json()["entries"][0]
    assert e["areas"] == ["Dateien lesen", "Im Internet suchen", "Befehle ausführen"]      # Bereichsnamen, je einmal, stabil
    assert e["tools"] == ["file_read", "read_document", "web_search", "shell_exec"]         # Tool-Namen nur hier (Expertenansicht)
    assert e["action"] == "tool_pool_set" and e["target"] == "agent:a1"
    en = _get(client, admin_headers, lang="en").json()["entries"][0]
    assert en["areas"] == ["Read files", "Search the internet", "Run commands"]


def test_area_audit_unbekanntes_tool_ohne_bereich(client, admin_headers):
    _eintrag("tool_grants_set", "user:anna", "gibt_es_nicht, file_read")
    e = _get(client, admin_headers).json()["entries"][0]
    assert e["areas"] == ["Dateien lesen"] and e["unknown"] == ["gibt_es_nicht"]


def test_area_audit_kategorie_wird_als_bereichsnamen_der_tools_gezeigt(client, admin_headers):
    _eintrag("tool_category_approve", "tool_category:files", "file_read")
    e = _get(client, admin_headers).json()["entries"][0]
    assert e["areas"] == ["Dateien lesen"] and e["target"] == "tool_category:files"


def test_area_audit_leer_und_kaputtes_detail(client, admin_headers):
    _eintrag("tool_pool_set", "agent:a1", "(leer)")
    _eintrag("tool_pool_set", "agent:a2", "")
    _eintrag("tool_pool_set", "agent:a3", " , ,, ")
    got = _get(client, admin_headers).json()["entries"]
    assert len(got) == 3 and all(e["areas"] == [] and e["tools"] == [] for e in got)


def test_area_audit_neueste_zuerst_und_limit(client, admin_headers):
    for i in range(7):
        _eintrag("tool_pool_set", f"agent:a{i}", "file_read")
    got = _get(client, admin_headers, limit=3).json()["entries"]
    assert [e["target"] for e in got] == ["agent:a6", "agent:a5", "agent:a4"]
    assert len(_get(client, admin_headers).json()["entries"]) == 7


def test_area_audit_limit_begrenzt(client, admin_headers):
    assert _get(client, admin_headers, limit=0).status_code == 422
    assert _get(client, admin_headers, limit=501).status_code == 422
    assert _get(client, admin_headers, limit="x").status_code == 422
    assert _get(client, admin_headers, limit=500).status_code == 200


def test_area_audit_zeigt_den_akteur_als_namen(client, admin_headers):
    from hydrahive.api.middleware.users import get_by_username
    uid = get_by_username("admin")["user_id"]
    _eintrag("tool_pool_set", "agent:a1", "file_read", actor=uid)
    _eintrag("tool_pool_set", "agent:a2", "file_read", actor="u-weg")
    by_target = {e["target"]: e for e in _get(client, admin_headers).json()["entries"]}
    assert by_target["agent:a1"]["actor"] == "admin"
    assert by_target["agent:a2"]["actor"] == ""                                           # unbekannte ID wird nicht durchgereicht


def test_area_audit_ist_nur_lesend(client, admin_headers):
    _eintrag("tool_pool_set", "agent:a1", "file_read")
    for method in (client.post, client.put, client.patch, client.delete):
        assert method("/api/admin/area-audit", headers=admin_headers).status_code in (404, 405)
    assert len(_get(client, admin_headers).json()["entries"]) == 1


def test_echter_pfad_schreibt_ins_protokoll(client, admin_headers):
    """Ein echtes Setzen der Besitzer-Freigabe taucht im Protokoll auf (Aktion tool_grants_set, Ziel user:…)."""
    r = client.put("/api/admin/tool-grants/testuser", headers=admin_headers, json={"items": ["file_read"]})
    assert r.status_code == 200, r.text
    got = _get(client, admin_headers).json()["entries"]
    mine = [e for e in got if e["action"] == "tool_grants_set" and e["target"] == "user:testuser"]
    assert mine and mine[0]["areas"] == ["Dateien lesen"] and mine[0]["actor"] == "admin"
