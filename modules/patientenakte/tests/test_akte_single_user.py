"""Single-User-Akte über die exakten URLs, die der Frontend-Client (api.ts) und
der Agent-Skill (medical-akte.md via fetch_url) verwenden: OHNE Trailing-Slash.

follow_redirects=False ist bewusst: ein 307 auf die Slash-Variante wird von
nicht-folgenden Clients (curl ohne -L, evtl. fetch_url) leer empfangen -> die
Akte wird stillschweigend nicht angelegt. Die Root-Route muss direkt 200 liefern.
"""
from __future__ import annotations

BASE = "/api/modules/patientenakte/akte"


def test_create_own_akte_without_trailing_slash(client, auth_headers):
    r = client.post(BASE, json={"slug": "me", "name": "Tester", "vorname": "Live"},
                    headers=auth_headers, follow_redirects=False)
    assert r.status_code == 200, f"erwartet 200 direkt, kein Redirect — war {r.status_code}"

    own = client.get(BASE, headers=auth_headers, follow_redirects=False)
    assert own.status_code == 200
    assert own.json()["name"] == "Tester"


def test_full_single_user_flow(client, auth_headers):
    client.post(BASE, json={"slug": "me", "name": "Tester"},
                headers=auth_headers, follow_redirects=False)

    c = client.post(f"{BASE}/conditions",
                    json={"diagnose": "Leberabszess", "icd_code": "K75.0",
                          "diagnostiziert_am": "2024-11-15"}, headers=auth_headers)
    assert c.status_code == 200

    for _ in range(2):
        client.post(f"{BASE}/observations/batch",
                    json={"items": [{"external_id": "h1", "parameter": "HbA1c",
                                     "wert": 6.4, "datum": "2026-05-01"}]},
                    headers=auth_headers)

    assert len(client.get(f"{BASE}/observations", headers=auth_headers).json()) == 1
    summary = client.get(f"{BASE}/summary", headers=auth_headers).json()
    assert summary["conditions"] == 1
    assert summary["observations"] == 1
    assert len(client.get(f"{BASE}/timeline", headers=auth_headers).json()) == 2


def test_create_own_akte_twice_conflicts(client, auth_headers):
    r1 = client.post(BASE, json={"slug": "me", "name": "A"},
                     headers=auth_headers, follow_redirects=False)
    assert r1.status_code == 200
    r2 = client.post(BASE, json={"slug": "me", "name": "B"},
                     headers=auth_headers, follow_redirects=False)
    assert r2.status_code == 409
