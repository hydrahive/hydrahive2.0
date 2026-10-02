"""Neue Buddy-Session aus Einstellungen/Neuwürfeln behält Tiefe und Modus.

Regression (02.10.2026, live erlebt): Kontext in den Buddy-Einstellungen
gespeichert → neue Session, die Denktiefe „xhigh“ war weg. „Frischer Chat“
(clear_session) übernahm Tiefe und Modus schon, patch_config und
reroll_character legen die Session aber über new_session_keeping_project an,
und das kopierte nur die Projektbindung.
"""
from __future__ import annotations

import pytest

USER = "keep-settings-user"


@pytest.fixture(autouse=True)
def _clean(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.db import init_db

    init_db()
    yield
    for a in agent_config.list_by_owner(USER):
        agent_config.delete(a["id"])


def _buddy_with(effort: str | None, mode: str | None) -> dict:
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.db import sessions as sessions_db

    b = get_or_create_buddy(USER)
    if effort:
        sessions_db.set_reasoning_effort(b["session_id"], effort)
    if mode:
        sessions_db.set_buddy_mode(b["session_id"], mode)
    return b


def _md(session_id: str) -> dict:
    from hydrahive.db import sessions as sessions_db

    return sessions_db.get(session_id).metadata or {}


def test_einstellungen_speichern_behaelt_tiefe_und_modus():
    from hydrahive.buddy._config import patch_config

    _buddy_with("xhigh", "humor")
    new_id = patch_config(USER, {"context": "Wahrheit zuerst."})["new_session_id"]
    assert new_id
    md = _md(new_id)
    assert md.get("reasoning_effort") == "xhigh"
    assert md.get("buddy_mode") == "humor"


def test_neuwuerfeln_behaelt_tiefe_und_modus():
    from hydrahive.buddy.commands import reroll_character

    _buddy_with("max", "focus")
    md = _md(reroll_character(USER)["session_id"])
    assert md.get("reasoning_effort") == "max"
    assert md.get("buddy_mode") == "focus"


def test_ohne_gesetzte_werte_bleibt_metadata_leer():
    """Nichts erfinden: ohne Tiefe/Modus keine Schlüssel in der neuen Session."""
    from hydrahive.buddy._config import patch_config

    _buddy_with(None, None)
    md = _md(patch_config(USER, {"tone": "knapp"})["new_session_id"])
    assert "reasoning_effort" not in md and "buddy_mode" not in md


def test_projektbindung_bleibt_weiter_erhalten():
    from hydrahive.buddy._config import patch_config
    from hydrahive.db import sessions as sessions_db

    from hydrahive.db.connection import db

    b = _buddy_with("high", None)
    with db() as conn:
        conn.execute("UPDATE sessions SET project_id = ? WHERE id = ?", ("proj-x", b["session_id"]))
    new_id = patch_config(USER, {"context": "x"})["new_session_id"]
    assert sessions_db.get(new_id).project_id == "proj-x"
