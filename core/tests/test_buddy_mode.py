"""Gesprächsmodus des Buddys (Normal / Fokus / Humorvoll / Kurze Antworten).

Regression: Das Auswahlfeld „Modus“ auf der Buddy-Seite hatte keinen State und
keine Wirkung. Jetzt: pro Session gespeichert, als Stil-Hinweis an den Prompt.
"""
from __future__ import annotations

import pytest


def test_modus_haengt_hinweis_nur_beim_buddy_an():
    from hydrahive.runner._buddy_mode import with_buddy_mode

    out = with_buddy_mode("BASIS", is_buddy=True, mode="brief")
    assert out.startswith("BASIS") and "Kurz-Modus" in out
    assert with_buddy_mode("BASIS", is_buddy=False, mode="brief") == "BASIS"


@pytest.mark.parametrize("mode", [None, "", "normal", "unbekannt"])
def test_normal_oder_unbekannt_aendert_nichts(mode):
    from hydrahive.runner._buddy_mode import with_buddy_mode

    assert with_buddy_mode("BASIS", is_buddy=True, mode=mode) == "BASIS"


def test_jeder_modus_hat_einen_hinweis():
    from hydrahive.runner._buddy_mode import BUDDY_MODES, VALID_MODES

    assert set(BUDDY_MODES) == {"focus", "humor", "brief"}
    assert VALID_MODES == {"normal", "focus", "humor", "brief"}
    assert all(text.strip() for text in BUDDY_MODES.values())


def test_modus_wird_pro_session_gespeichert_und_normal_entfernt_ihn(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db import sessions as sessions_db

    init_db()
    s = sessions_db.create(agent_id="a", user_id="mode-user", title="t")
    sessions_db.set_buddy_mode(s.id, "humor")
    assert sessions_db.get(s.id).metadata["buddy_mode"] == "humor"
    sessions_db.set_reasoning_effort(s.id, "high")
    sessions_db.set_buddy_mode(s.id, "normal")
    md = sessions_db.get(s.id).metadata
    assert "buddy_mode" not in md and md["reasoning_effort"] == "high"
    sessions_db.delete(s.id)


def test_buddy_status_liefert_den_modus_der_session(setup_test_env):
    """Die Buddy-Seite liest den gespeicherten Modus aus dem Buddy-Status."""
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.db import init_db
    from hydrahive.db import sessions as sessions_db

    init_db()
    try:
        first = get_or_create_buddy("mode-status-user")
        assert first["mode"] == "normal"
        sessions_db.set_buddy_mode(first["session_id"], "focus")
        assert get_or_create_buddy("mode-status-user")["mode"] == "focus"
    finally:
        for a in agent_config.list_by_owner("mode-status-user"):
            agent_config.delete(a["id"])


def test_session_api_setzt_und_validiert_den_modus(client, auth_headers):
    from hydrahive.db import sessions as sessions_db

    sid = sessions_db.create(agent_id="a", user_id="testuser", title="t").id
    try:
        ok = client.patch(f"/api/sessions/{sid}", headers=auth_headers, json={"buddy_mode": "focus"})
        assert ok.status_code == 200 and ok.json()["metadata"]["buddy_mode"] == "focus"
        bad = client.patch(f"/api/sessions/{sid}", headers=auth_headers, json={"buddy_mode": "chaos"})
        assert bad.status_code == 422
        reset = client.patch(f"/api/sessions/{sid}", headers=auth_headers, json={"buddy_mode": "normal"})
        assert "buddy_mode" not in reset.json()["metadata"]
    finally:
        sessions_db.delete(sid)
