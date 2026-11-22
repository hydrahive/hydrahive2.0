"""G3/P2 — ctx.catalog_foreign_list: fremde Einträge mit Projektzuordnung, nur eigener
Nutzername (AK G12), Filter, stale, leer ohne Gemeinsame Taskpflege, wirft nie.
"""
from __future__ import annotations

import uuid

import pytest

from hydrahive.db import federation_catalog_mirror as mirror_db
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from hydrahive.modules.context import ModuleContext
from tests._delete_fixtures import make_project

FP = "fp-hydrahive-master"
CTX = ModuleContext("tasks")


def _m(item_id, *, owner="testuser", project_id="o-dev", project_name=None, status="open", title=None,
       kind="task", fp=FP, updated="2026-11-22T10:00:00Z"):
    return {"origin_fp": fp, "kind": kind, "item_id": item_id, "origin_name": "hydrahive-master", "owner": owner,
            "title": title or f"Titel {item_id}", "status": status, "priority": None, "project_id": project_id,
            "project_name": project_name, "created_at": updated, "updated_at": updated}


@pytest.fixture
def client_mode(client):
    """Diese Instanz ist Client mit aktivem Hub und Gemeinsamer Taskpflege."""
    tag = uuid.uuid4().hex[:6]
    dev = make_project(f"Hydrahive DEV {tag}", created_by="admin", members=["testuser"])
    with db() as conn:
        conn.execute("INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at, is_hub)"
                     " VALUES ('fl-hub', 'hub', 'https://h.example', 'pk-fl', 'fp-hub', 'active', ?, 1)", (now_iso(),))
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute("UPDATE federation_catalog_settings SET enabled = 1, shared = 1 WHERE id = 1")
        conn.execute("DELETE FROM federation_catalog_project_map WHERE username IN ('testuser', 'admin', 'anna')")
    mirror_db.clear()
    rows = [_m("t-1", project_name=dev["name"], updated="2026-11-22T10:00:03Z"),
            _m("t-2", project_name=dev["name"], status="done", title="Steuer abgeben"),
            _m("t-3", project_id="o-only", project_name="Nur auf .2"),
            _m("t-4", project_id=None),
            _m("t-5", owner="admin", project_name=dev["name"]),
            _m("i-1", kind="idea", status="new", project_name=dev["name"])]
    mirror_db.apply_page(rows, [], 1, {"task": None, "idea": None}, now_iso())
    mirror_db.save_instances([{"origin_fp": FP, "origin_name": "hydrahive-master", "last_seen": "2026-11-22T10:05:00Z",
                               "stale": False}], now_iso())
    yield dev
    mirror_db.clear()
    with db() as conn:
        conn.execute("DELETE FROM federation_peers WHERE id = 'fl-hub'")
        conn.execute("UPDATE federation_catalog_settings SET enabled = 0, shared = 0 WHERE id = 1")
        conn.execute("DELETE FROM federation_catalog_project_map WHERE username IN ('testuser', 'admin', 'anna')")


def _ids(rows):
    return [r["item_id"] for r in rows]


def test_projekt_filter_mit_zuordnung_und_felder(client_mode):
    rows = CTX.catalog_foreign_list("task", "testuser", client_mode["id"])
    assert _ids(rows) == ["t-1", "t-2"]                                   # neueste zuerst
    r = rows[0]
    assert r["foreign"] is True and r["origin_name"] == "hydrahive-master" and r["origin_fp"] == FP
    assert r["project_id"] == "o-dev" and r["local_project_id"] == client_mode["id"]
    assert r["stale"] is False and r["origin_last_seen"] == "2026-11-22T10:05:00Z" and r["pending_edits"] == 0


def test_none_nur_ohne_projekt_und_stern_ohne_nicht_zugeordnete(client_mode):
    assert _ids(CTX.catalog_foreign_list("task", "testuser", None)) == ["t-4"]
    assert sorted(_ids(CTX.catalog_foreign_list("task", "testuser", "*"))) == ["t-1", "t-2", "t-4"]   # t-3 fehlt


def test_hidden_und_manuelle_zuordnung(client_mode):
    with db() as conn:
        conn.execute("INSERT INTO federation_catalog_project_map VALUES ('testuser', ?, 'o-dev', 'hidden', 'x')", (FP,))
        conn.execute("INSERT INTO federation_catalog_project_map VALUES ('testuser', ?, 'o-only', ?, 'x')",
                     (FP, client_mode["id"]))
    assert _ids(CTX.catalog_foreign_list("task", "testuser", client_mode["id"])) == ["t-3"]
    assert "t-1" not in _ids(CTX.catalog_foreign_list("task", "testuser", "*"))


def test_nur_eigener_nutzername_auch_fuer_admins(client_mode):
    assert _ids(CTX.catalog_foreign_list("task", "admin", "*")) == ["t-5"]          # AK G12
    assert "t-5" not in _ids(CTX.catalog_foreign_list("task", "testuser", "*"))
    assert CTX.catalog_foreign_list("task", "anna", "*") == []


def test_filter_status_suche_art_seiten(client_mode):
    pid = client_mode["id"]
    assert _ids(CTX.catalog_foreign_list("task", "testuser", pid, statuses=["done"])) == ["t-2"]
    assert _ids(CTX.catalog_foreign_list("task", "testuser", pid, q="steuer")) == ["t-2"]
    assert _ids(CTX.catalog_foreign_list("idea", "testuser", pid)) == ["i-1"]
    assert _ids(CTX.catalog_foreign_list("task", "testuser", pid, limit=1, offset=1)) == ["t-2"]
    assert CTX.catalog_foreign_list("ticket", "testuser", pid) == []


def test_stale_wenn_ursprung_nicht_aktuell_oder_unbekannt(client_mode):
    mirror_db.save_instances([{"origin_fp": FP, "stale": True, "last_seen": "2026-11-01T00:00:00Z"}], now_iso())
    assert CTX.catalog_foreign_list("task", "testuser", client_mode["id"])[0]["stale"] is True
    mirror_db.save_instances([], now_iso())                                       # Ursprung nicht mehr gemeldet
    assert CTX.catalog_foreign_list("task", "testuser", client_mode["id"])[0]["stale"] is True


def test_ohne_gemeinsame_taskpflege_leer(client_mode):
    with db() as conn:
        conn.execute("UPDATE federation_catalog_settings SET shared = 0 WHERE id = 1")
    assert CTX.catalog_foreign_list("task", "testuser", "*") == []


def test_wirft_nie(client_mode, monkeypatch):
    from hydrahive.db import federation_catalog_foreign as foreign_db

    def boom(*a, **kw):
        raise RuntimeError("DB weg")
    monkeypatch.setattr(foreign_db, "mirror_rows", boom)
    assert CTX.catalog_foreign_list("task", "testuser", "*") == []


def test_auf_dem_hub_aus_dem_katalog_nur_sichtbare_partner(client):
    tag = uuid.uuid4().hex[:6]
    proj = make_project(f"Garten {tag}", created_by="admin", members=["testuser"])
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO federation_catalog_settings (id) VALUES (1)")
        conn.execute("UPDATE federation_catalog_settings SET enabled = 0, shared = 1 WHERE id = 1")
        for pid, shared in (("fl-o", 1), ("fl-x", 0)):
            conn.execute("INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at, "
                         "catalog_accept) VALUES (?, ?, 'https://o.example', ?, ?, 'active', ?, 1)",
                         (pid, pid, f"pk-{pid}", f"fp-{pid}", now_iso()))
            conn.execute("INSERT INTO federation_catalog_sources (peer_id, last_seq, shared, last_push_at, "
                         "interval_seconds) VALUES (?, 1, ?, ?, 300)", (pid, shared, now_iso()))
            conn.execute("INSERT INTO federation_catalog_items (peer_id, kind, item_id, owner, title, status, "
                         "project_id, project_name, updated_at, received_at) VALUES (?, 'task', ?, 'testuser', 'T', "
                         "'open', 'o-g', ?, 'x', 'x')", (pid, f"h-{pid}", proj["name"]))
    try:
        rows = CTX.catalog_foreign_list("task", "testuser", proj["id"])
        assert _ids(rows) == ["h-fl-o"]                                    # fl-x teilt nicht
        assert rows[0]["origin_fp"] == "fp-fl-o" and rows[0]["stale"] is False
    finally:
        with db() as conn:
            conn.execute("DELETE FROM federation_peers WHERE id IN ('fl-o', 'fl-x')")
            conn.execute("UPDATE federation_catalog_settings SET shared = 0 WHERE id = 1")
