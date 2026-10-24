"""docs/specs/startdesktop.md: Startseite, aktiver Bereich und zuletzt benutzte App je Bereich am Server.
Falsche Werte werden verworfen (Rückfall auf den Standard), nicht mit Fehler beantwortet."""
from __future__ import annotations

URL = "/api/me/preferences"


def test_area_prefs_persist_and_stay_per_user(client, auth_headers, admin_headers):
    r = client.patch(URL, headers=auth_headers, json={
        "landing": "buddy", "active_area": "schreiben", "area_last": {"schreiben": "/storyteller", "medien": "/studio/neu"},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["landing"] == "buddy"
    assert body["active_area"] == "schreiben"
    assert body["area_last"] == {"schreiben": "/storyteller", "medien": "/studio/neu"}
    again = client.get(URL, headers=auth_headers).json()
    assert (again["landing"], again["active_area"], again["area_last"]["medien"]) == ("buddy", "schreiben", "/studio/neu")
    admin = client.get(URL, headers=admin_headers).json()
    assert (admin["landing"], admin["active_area"], admin["area_last"]) == ("start", None, {})


def test_patch_keeps_other_fields(client, auth_headers):
    client.patch(URL, headers=auth_headers, json={"active_vault_scope": "family"})
    r = client.patch(URL, headers=auth_headers, json={"active_area": "medien"})
    assert r.json()["active_vault_scope"] == "family"
    assert r.json()["active_area"] == "medien"


def test_landing_only_known_values(client, auth_headers):
    for ok in ("start", "buddy", "dashboard"):
        assert client.patch(URL, headers=auth_headers, json={"landing": ok}).json()["landing"] == ok
    for bad in ("admin", "", "javascript:alert(1)", 5):
        r = client.patch(URL, headers=auth_headers, json={"landing": bad})
        assert r.status_code == 200, bad
        assert r.json()["landing"] == "start", bad


def test_active_area_must_be_simple_id(client, auth_headers):
    for bad in ("Schreiben", "a b", "../x", "x" * 33, 7):
        r = client.patch(URL, headers=auth_headers, json={"active_area": bad})
        assert r.status_code == 200, bad
        assert r.json()["active_area"] is None, bad
    assert client.patch(URL, headers=auth_headers, json={"active_area": "x" * 32}).json()["active_area"] == "x" * 32
    assert client.patch(URL, headers=auth_headers, json={"active_area": None}).json()["active_area"] is None


def test_area_last_drops_bad_entries(client, auth_headers):
    r = client.patch(URL, headers=auth_headers, json={"area_last": {
        "schreiben": "/storyteller",
        "BAD KEY": "/x",
        "medien": "https://evil.example/",
        "wissen": "/recht?x=1",
        "freizeit": "/" + "a" * 121,
        "zuhause": 5,
        "agenten": "/projects",
    }})
    assert r.status_code == 200
    assert r.json()["area_last"] == {"schreiben": "/storyteller", "agenten": "/projects"}


def test_area_last_limited_to_20(client, auth_headers):
    many = {f"b{i}": f"/app{i}" for i in range(30)}
    got = client.patch(URL, headers=auth_headers, json={"area_last": many}).json()["area_last"]
    assert len(got) == 20
    assert got == {f"b{i}": f"/app{i}" for i in range(20)}


def test_area_last_must_be_object(client, auth_headers):
    r = client.patch(URL, headers=auth_headers, json={"area_last": ["/x"]})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["area_last"] == {}
