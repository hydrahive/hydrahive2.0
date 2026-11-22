"""G3/P1 — API GET/PUT /api/federation/catalog/project-map: jeder angemeldete Nutzer, nur
eigene Zeilen; Ziel-Projekt muss existieren und der Nutzer Mitglied sein, sonst 404.
GET listet Ursprungsprojekte aus der Kopie (Client) und dem Katalog (Hub).
"""
from __future__ import annotations

import uuid

import pytest

from hydrahive.db import federation_catalog_mirror as mirror_db
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from tests._delete_fixtures import make_project

URL = "/api/federation/catalog/project-map"
FP = "fp-hydrahive-master"


def _mirror_item(item_id, *, owner="testuser", project_id="o-dev", project_name="Hydrahive DEV", fp=FP):
    return {"origin_fp": fp, "kind": "task", "item_id": item_id, "origin_name": "hydrahive-master",
            "owner": owner, "title": "T", "status": "open", "priority": None, "project_id": project_id,
            "project_name": project_name, "created_at": "2026-11-22T10:00:00Z",
            "updated_at": "2026-11-22T10:00:00Z"}


@pytest.fixture
def setup(client):
    mirror_db.clear()
    with db() as conn:
        conn.execute("DELETE FROM federation_catalog_project_map WHERE username IN ('testuser', 'admin', 'anna')")
    tag = uuid.uuid4().hex[:6]          # Projekte früherer Läufe bleiben liegen: Namen je Lauf eindeutig
    dev = make_project(f"Hydrahive DEV {tag}", created_by="admin", members=["testuser"])
    garten = make_project(f"Garten {tag}", created_by="admin", members=["testuser"])
    fremd = make_project(f"Fremdprojekt {tag}", created_by="admin", members=["admin"])
    rows = [_mirror_item("t-1", project_name=dev["name"]), _mirror_item("t-2", project_name=dev["name"]),
            _mirror_item("t-3", project_id="o-only", project_name="Nur auf .2"),
            _mirror_item("t-4", owner="anna"), _mirror_item("t-5", project_id=None, project_name=None)]
    mirror_db.apply_page(rows, [], 1, {"task": None, "idea": None}, now_iso())
    yield {"dev": dev, "garten": garten, "fremd": fremd, "tag": tag}
    mirror_db.clear()
    with db() as conn:
        conn.execute("DELETE FROM federation_catalog_project_map WHERE username IN ('testuser', 'admin', 'anna')")


def _origins(client, headers):
    r = client.get(URL, headers=headers)
    assert r.status_code == 200, r.text
    return {o["origin_project_id"]: o for o in r.json()["origins"]}


def test_listet_eigene_ursprungsprojekte_mit_anzahl_und_zuordnung(client, auth_headers, setup):
    o = _origins(client, auth_headers)
    assert set(o) == {"o-dev", "o-only"}                       # anna-Eintrag und Eintrag ohne Projekt fehlen
    assert o["o-dev"]["count"] == 2 and o["o-dev"]["origin_name"] == "hydrahive-master"
    assert o["o-dev"]["setting"] == "auto" and o["o-dev"]["local_project_id"] == setup["dev"]["id"]
    assert o["o-dev"]["reason"] == "name"
    assert o["o-only"]["local_project_id"] is None and o["o-only"]["reason"] == "no_match"


def test_manuell_zuordnen_hidden_und_zurueck_auf_auto(client, auth_headers, setup):
    body = {"origin_fp": FP, "origin_project_id": "o-only", "target": setup["garten"]["id"]}
    o = {x["origin_project_id"]: x for x in client.put(URL, headers=auth_headers, json=body).json()["origins"]}
    assert o["o-only"]["setting"] == setup["garten"]["id"] and o["o-only"]["reason"] == "manual"
    body["target"] = "hidden"
    o = {x["origin_project_id"]: x for x in client.put(URL, headers=auth_headers, json=body).json()["origins"]}
    assert o["o-only"]["hidden"] is True and o["o-only"]["local_project_id"] is None
    body["target"] = "auto"
    client.put(URL, headers=auth_headers, json=body)
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM federation_catalog_project_map").fetchone()[0] == 0


def test_ziel_unbekannt_oder_nicht_mitglied_ergibt_404(client, auth_headers, setup):
    for target in ("gibt-es-nicht", setup["fremd"]["id"]):
        r = client.put(URL, headers=auth_headers, json={"origin_fp": FP, "origin_project_id": "o-only",
                                                         "target": target})
        assert r.status_code == 404 and r.json()["detail"]["code"] == "project_not_found"
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM federation_catalog_project_map").fetchone()[0] == 0


def test_admin_darf_jedes_projekt_waehlen(client, admin_headers, setup):
    rows = [_mirror_item("a-1", owner="admin", project_id="o-x", project_name="X")]
    mirror_db.apply_page(rows, [], 2, {"task": None, "idea": None}, now_iso())
    r = client.put(URL, headers=admin_headers, json={"origin_fp": FP, "origin_project_id": "o-x",
                                                      "target": setup["fremd"]["id"]})
    assert r.status_code == 200
    o = {x["origin_project_id"]: x for x in r.json()["origins"]}
    assert set(o) == {"o-x"}                                   # Admin sieht nur eigene, nicht testuser
    assert o["o-x"]["local_project_id"] == setup["fremd"]["id"]


def test_zeilen_anderer_nutzer_weder_sichtbar_noch_aenderbar(client, auth_headers, admin_headers, setup):
    with db() as conn:
        conn.execute("INSERT INTO federation_catalog_project_map VALUES ('anna', ?, 'o-dev', 'hidden', 'x')", (FP,))
    o = _origins(client, auth_headers)
    assert o["o-dev"]["setting"] == "auto" and o["o-dev"]["hidden"] is False   # annas „hidden“ wirkt nicht
    client.put(URL, headers=auth_headers, json={"origin_fp": FP, "origin_project_id": "o-dev", "target": "auto"})
    with db() as conn:
        row = conn.execute("SELECT target FROM federation_catalog_project_map WHERE username = 'anna'").fetchone()
    assert row["target"] == "hidden"                           # testuser kann annas Zeile nicht löschen


def test_umbenennung_beim_ursprung(client, auth_headers, setup):
    client.put(URL, headers=auth_headers, json={"origin_fp": FP, "origin_project_id": "o-only",
                                                 "target": setup["garten"]["id"]})
    g = setup["garten"]["name"].upper()                         # Groß/Klein egal
    renamed = [_mirror_item("t-1", project_name=g, project_id="o-dev"),
               _mirror_item("t-2", project_name=g, project_id="o-dev"),
               _mirror_item("t-3", project_id="o-only", project_name="Ganz neu")]
    for r in renamed:
        r["updated_at"] = "2026-11-22T11:00:00Z"
    mirror_db.apply_page(renamed, [], 3, {"task": None, "idea": None}, now_iso())
    o = _origins(client, auth_headers)
    assert o["o-dev"]["local_project_id"] == setup["garten"]["id"] and o["o-dev"]["reason"] == "name"   # wandert mit
    assert o["o-only"]["local_project_id"] == setup["garten"]["id"] and o["o-only"]["reason"] == "manual"  # bleibt


def test_katalog_auf_dem_hub_zaehlt_mit(client, auth_headers, setup):
    with db() as conn:
        conn.execute("INSERT INTO federation_peers (id, name, url, public_key, fingerprint, status, created_at) "
                     "VALUES ('pm-peer', 'devbox', 'https://d.example', 'pk-pm', 'fp-devbox', 'active', ?)", (now_iso(),))
        conn.execute("INSERT INTO federation_catalog_items (peer_id, kind, item_id, owner, title, status, project_id, "
                     "project_name, updated_at, received_at) VALUES ('pm-peer', 'idea', 'i-1', 'testuser', 'I', 'new', "
                     "'o-g', ?, 'x', 'x')", (f"  garten {setup['tag']} ",))
    try:
        o = _origins(client, auth_headers)
        assert o["o-g"]["origin_fp"] == "fp-devbox" and o["o-g"]["local_project_id"] == setup["garten"]["id"]
    finally:
        with db() as conn:
            conn.execute("DELETE FROM federation_peers WHERE id = 'pm-peer'")


def test_nur_angemeldet_und_felder_geprueft(client, auth_headers, setup):
    assert client.get(URL).status_code == 401
    assert client.put(URL, json={"origin_fp": FP, "origin_project_id": "x", "target": "auto"}).status_code == 401
    r = client.put(URL, headers=auth_headers, json={"origin_fp": "", "origin_project_id": "x", "target": "auto"})
    assert r.status_code == 422
