"""P8 (Review #746, Befunde 2+3): Hub gesperrt/entfernt oder Abholen scheitert dauerhaft →
die Module sehen die Kopie mit ``stale`` bzw. Metadaten mit ``hub_unreachable`` (Spec §Schalter
„Sperrt ein Client seinen Hub …“, AK G14), statt einer leeren Liste. Gemeinsame Taskpflege
selbst ausgeschaltet → Kopie geleert, leer.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hydrahive.db import federation_catalog as catalog_db
from hydrahive.db.connection import db
from hydrahive.modules.context import ModuleContext
from tests.test_federation_catalog_foreign_list import FP, client_mode  # noqa: F401  (Fixture)

CTX = ModuleContext("tasks")


def _ago(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _set(sql: str, *args) -> None:
    with db() as conn:
        conn.execute(sql, args)


def _rows(pid: str) -> list[dict]:
    return CTX.catalog_foreign_list("task", "testuser", pid)


def test_frisch_abgeholt_nicht_stale(client_mode):  # noqa: F811
    assert _rows(client_mode["id"]) and all(r["stale"] is False for r in _rows(client_mode["id"]))


def test_hub_gesperrt_liste_aus_der_kopie_stale(client_mode):  # noqa: F811
    _set("UPDATE federation_peers SET status = 'blocked' WHERE id = 'fl-hub'")
    rows = _rows(client_mode["id"])
    assert [r["item_id"] for r in rows] == ["t-1", "t-2"] and all(r["stale"] is True for r in rows)


def test_hub_entfernt_liste_aus_der_kopie_stale(client_mode):  # noqa: F811
    _set("UPDATE federation_peers SET is_hub = 0 WHERE id = 'fl-hub'")
    rows = _rows(client_mode["id"])
    assert len(rows) == 2 and all(r["stale"] is True for r in rows)


def test_sync_aus_liste_aus_der_kopie_stale(client_mode):  # noqa: F811
    _set("UPDATE federation_catalog_settings SET enabled = 0 WHERE id = 1")
    assert all(r["stale"] is True for r in _rows(client_mode["id"])) and len(_rows(client_mode["id"])) == 2


def test_abholen_scheitert_laenger_als_zwei_intervalle_stale(client_mode):  # noqa: F811
    _set("UPDATE federation_catalog_settings SET interval_seconds = 300, last_pull_at = ? WHERE id = 1", _ago(500))
    assert all(r["stale"] is False for r in _rows(client_mode["id"]))            # < 2 Intervalle
    _set("UPDATE federation_catalog_settings SET last_pull_at = ? WHERE id = 1", _ago(700))
    assert all(r["stale"] is True for r in _rows(client_mode["id"]))             # > 2 Intervalle
    _set("UPDATE federation_catalog_settings SET last_pull_at = NULL WHERE id = 1")
    assert all(r["stale"] is True for r in _rows(client_mode["id"]))             # noch nie abgeholt


def test_taskpflege_selbst_aus_bleibt_leer(client_mode):  # noqa: F811
    _set("UPDATE federation_peers SET status = 'blocked' WHERE id = 'fl-hub'")
    _set("UPDATE federation_catalog_settings SET shared = 0 WHERE id = 1")
    catalog_db.clear_mirror()                                                    # wie die Einstellungs-Route
    assert CTX.catalog_foreign_list("task", "testuser", "*") == []


def test_kopie_leer_ohne_hub_kein_client_modus(client_mode):  # noqa: F811
    from hydrahive.db import federation_catalog_foreign as foreign_db
    _set("UPDATE federation_peers SET is_hub = 0 WHERE id = 'fl-hub'")
    catalog_db.clear_mirror()
    assert foreign_db.mode() is None and CTX.catalog_foreign_list("task", "testuser", "*") == []


async def test_get_hub_gesperrt_metadaten_mit_hinweis(client_mode, monkeypatch):  # noqa: F811
    from hydrahive.federation import catalog_read_client as rc

    async def nie(*a, **kw):
        raise AssertionError("kein Netzverkehr ohne aktiven Hub")
    monkeypatch.setattr(rc, "request_signed", nie)
    _set("UPDATE federation_peers SET status = 'blocked' WHERE id = 'fl-hub'")
    full = await CTX.catalog_foreign_get("task", "testuser", FP, "t-1")
    assert full["hub_unreachable"] is True and full["source"] == "metadata" and full["content"] is None
    assert full["item"]["item_id"] == "t-1" and full["item"]["stale"] is True
    assert await CTX.catalog_foreign_get("task", "admin", FP, "t-1") is None    # fremder Nutzer bleibt draußen


async def test_get_hub_entfernt_metadaten_mit_hinweis(client_mode, monkeypatch):  # noqa: F811
    from hydrahive.federation import catalog_read_client as rc

    async def nie(*a, **kw):
        raise AssertionError("kein Netzverkehr ohne Hub")
    monkeypatch.setattr(rc, "request_signed", nie)
    _set("UPDATE federation_peers SET is_hub = 0 WHERE id = 'fl-hub'")
    full = await CTX.catalog_foreign_get("task", "testuser", FP, "t-1")
    assert full["hub_unreachable"] is True and full["item"]["stale"] is True
