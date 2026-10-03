"""Buddy: frühere Unterhaltungen wieder aufrufen (Spec docs/specs/buddy-session-picker.md).

Till 02.10.2026: „Neuer Chat“ — alte Unterhaltungen verschwinden im Nirvana.
Sie sind noch da (78 bei Till), es fehlt nur die Auswahl. Dabei gefunden:
F1  Kanal-Sitzungen (WhatsApp, Discord …) konnten zur „aktuellen“ Web-Sitzung werden.
F2  Bei > 50 neueren Sitzungen fand Buddy seine eigene nicht und legte eine neue an.
"""
from __future__ import annotations

import pytest

USER = "picker-user"
OTHER = "picker-other"
HELPER = "picker-projekt-helfer"   # andere Agent-ID desselben Nutzers (Projekt, Automatik …)


@pytest.fixture(autouse=True)
def _clean(setup_test_env):
    from hydrahive.agents import config as agent_config
    from hydrahive.db import init_db

    init_db()
    yield
    from hydrahive.db.connection import db

    for u in (USER, OTHER):
        for a in agent_config.list_by_owner(u):
            agent_config.delete(a["id"])
        with db() as conn:
            conn.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE user_id = ?)", (u,))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (u,))


def _buddy(user: str = USER) -> dict:
    from hydrahive.buddy import get_or_create_buddy

    return get_or_create_buddy(user)


def _session(agent_id: str, user: str = USER, *, channel: str | None = None, at: str | None = None) -> str:
    """Sitzung anlegen; `at` setzt created_at/updated_at (Reihenfolge)."""
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db.connection import db

    sid = sessions_db.create(agent_id=agent_id, user_id=user, title=f"{user}'s Buddy").id
    with db() as conn:
        if channel:
            conn.execute("UPDATE sessions SET channel = ?, external_user_id = 'x' WHERE id = ?", (channel, sid))
        if at:
            conn.execute("UPDATE sessions SET created_at = ?, updated_at = ? WHERE id = ?", (at, at, sid))
    return sid


def _backdate(session_id: str, at: str) -> None:
    from hydrahive.db.connection import db

    with db() as conn:
        conn.execute("UPDATE sessions SET created_at = ?, updated_at = ? WHERE id = ?", (at, at, session_id))


def test_list_order_follows_last_activity():
    """Eine alte Unterhaltung, in der heute geschrieben wurde, steht oben."""
    from hydrahive.buddy import sessions_picker

    b = _buddy()
    old = _session(b["agent_id"], at="2026-06-01T10:00:00+00:00")
    _say(old, "user", "heute nochmal weiter")

    assert sessions_picker.list_sessions(USER)["sessions"][0]["id"] == old


def _say(session_id: str, role: str, content) -> None:
    from hydrahive.db import messages as messages_db

    messages_db.append(session_id, role, content)


# --- Liste --------------------------------------------------------------------

def test_list_shows_only_own_web_sessions_newest_first():
    from hydrahive.buddy import sessions_picker

    b = _buddy()
    old = _session(b["agent_id"])
    _say(old, "user", "alte Frage zum Garten")      # setzt updated_at auf jetzt …
    _backdate(old, "2026-06-01T10:00:00+00:00")     # … deshalb danach zurückdatieren
    _session(b["agent_id"], channel="whatsapp", at="2026-09-01T10:00:00+00:00")
    other = _buddy(OTHER)
    _session(other["agent_id"], OTHER, at="2026-09-02T10:00:00+00:00")
    _session(b["agent_id"], OTHER, at="2026-09-03T10:00:00+00:00")   # fremd, auf meiner Buddy-ID

    res = sessions_picker.list_sessions(USER)
    ids = [s["id"] for s in res["sessions"]]

    assert ids[0] == b["session_id"]               # die aktuelle (gerade angelegt) zuerst
    assert old in ids
    assert len(ids) == 2                           # kein WhatsApp, nichts vom anderen Nutzer
    assert res["active_id"] == b["session_id"]
    row = next(s for s in res["sessions"] if s["id"] == old)
    assert row["first_message"] == "alte Frage zum Garten"
    assert row["message_count"] == 1


def test_list_pages_with_has_more():
    from hydrahive.buddy import sessions_picker

    b = _buddy()
    for i in range(5):
        sid = _session(b["agent_id"])
        _say(sid, "user", f"Frage {i}")              # leere würden ausgeblendet
        _backdate(sid, f"2026-05-0{i + 1}T10:00:00+00:00")

    first = sessions_picker.list_sessions(USER, offset=0, limit=4)
    rest = sessions_picker.list_sessions(USER, offset=4, limit=4)

    assert len(first["sessions"]) == 4 and first["has_more"] is True
    assert len(rest["sessions"]) == 2 and rest["has_more"] is False


@pytest.mark.parametrize(("messages", "expected"), [
    ([("user", [{"type": "text", "text": "Hallo   Buddy,\nwie geht's?"}])], "Hallo Buddy, wie geht's?"),
    ([("user", "/system"), ("user", "echte Frage")], "echte Frage"),
    # Nur Befehle (z. B. „/system“ auf hydratest): Befehl statt „(noch leer)“ —
    # sonst sieht eine Unterhaltung mit Nachrichten leer aus.
    ([("user", "/system"), ("assistant", "System-Prompt: …")], "/system"),
    ([("user", [{"type": "tool_result", "tool_use_id": "t", "content": "x"}]), ("user", "danach")], "danach"),
    ([("assistant", "nur Antwort")], None),
    ([("user", "x" * 300)], "x" * 79 + "…"),
])
def test_first_message_preview(messages, expected):
    from hydrahive.buddy import sessions_picker

    b = _buddy()
    for role, content in messages:
        _say(b["session_id"], role, content)

    row = sessions_picker.list_sessions(USER)["sessions"][0]
    assert row["first_message"] == expected


# --- F1 / F2: welche Sitzung zeigt Buddy? ------------------------------------

def test_f1_channel_session_never_becomes_the_web_session():
    from hydrahive.buddy import get_or_create_buddy

    b = _buddy()
    web = b["session_id"]
    _session(b["agent_id"], channel="whatsapp", at="2099-01-01T00:00:00+00:00")   # „jüngste“

    assert get_or_create_buddy(USER)["session_id"] == web


def test_f2_many_newer_sessions_do_not_lose_the_buddy_session():
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy import get_or_create_buddy

    b = _buddy()
    web = b["session_id"]
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE sessions SET created_at = '2026-01-01T00:00:00+00:00', "
                     "updated_at = '2026-01-01T00:00:00+00:00' WHERE id = ?", (web,))
    for i in range(60):
        _session(HELPER, at=f"2026-09-{(i % 28) + 1:02d}T10:{i % 60:02d}:00+00:00")

    assert get_or_create_buddy(USER)["session_id"] == web


def test_f2_new_chat_keeps_settings_even_with_many_newer_sessions():
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy.commands import clear_session
    from hydrahive.db import sessions as sessions_db

    b = _buddy()
    sessions_db.set_reasoning_effort(b["session_id"], "xhigh")
    for i in range(60):
        _session(HELPER, at=f"2099-01-01T10:{i % 60:02d}:00+00:00")

    new_id = clear_session(USER)["session_id"]
    assert (sessions_db.get(new_id).metadata or {}).get("reasoning_effort") == "xhigh"


# --- Öffnen -------------------------------------------------------------------

def test_open_old_session_becomes_active_and_is_remembered():
    from hydrahive.buddy import get_or_create_buddy, sessions_picker

    b = _buddy()
    old = _session(b["agent_id"], at="2026-06-01T10:00:00+00:00")

    state = sessions_picker.open_session(USER, old)

    assert state["session_id"] == old
    assert get_or_create_buddy(USER)["session_id"] == old        # bleibt nach Neuladen


@pytest.mark.parametrize("kind", ["foreign", "foreign_on_my_agent", "channel", "other_agent", "unknown"])
def test_open_rejects_sessions_that_are_not_my_buddy_web_sessions(kind):
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy import sessions_picker

    b = _buddy()
    if kind == "foreign":
        sid = _buddy(OTHER)["session_id"]
    elif kind == "foreign_on_my_agent":
        # Sitzung eines anderen Nutzers auf MEINER Buddy-ID (z. B. geteilter Agent,
        # Datenfehler): darf trotzdem nicht geöffnet werden — Prüfung auf user_id.
        sid = _session(b["agent_id"], OTHER)
    elif kind == "channel":
        sid = _session(b["agent_id"], channel="discord")
    elif kind == "other_agent":
        sid = _session(HELPER)
    else:
        sid = "01a0ffff-0000-7000-8000-000000000000"

    with pytest.raises(LookupError):
        sessions_picker.open_session(USER, sid)


def test_open_refused_while_current_run_is_active(monkeypatch):
    from hydrahive.buddy import sessions_picker
    from hydrahive.runner import concurrency

    b = _buddy()
    old = _session(b["agent_id"], at="2026-06-01T10:00:00+00:00")
    monkeypatch.setattr(concurrency, "is_running", lambda sid: sid == b["session_id"])

    with pytest.raises(sessions_picker.RunActive):
        sessions_picker.open_session(USER, old)


def test_new_chat_after_opening_old_one_keeps_its_settings_and_is_remembered():
    from hydrahive.buddy import get_or_create_buddy, sessions_picker
    from hydrahive.buddy.commands import clear_session
    from hydrahive.db import sessions as sessions_db

    b = _buddy()
    old = _session(b["agent_id"], at="2026-06-01T10:00:00+00:00")
    sessions_db.set_buddy_mode(old, "humor")
    sessions_picker.open_session(USER, old)

    new_id = clear_session(USER)["session_id"]

    assert new_id not in (old, b["session_id"])
    assert (sessions_db.get(new_id).metadata or {}).get("buddy_mode") == "humor"
    assert get_or_create_buddy(USER)["session_id"] == new_id


def test_deleted_remembered_session_falls_back_to_newest():
    from hydrahive.buddy import get_or_create_buddy, sessions_picker
    from hydrahive.db import sessions as sessions_db

    b = _buddy()
    old = _session(b["agent_id"], at="2026-06-01T10:00:00+00:00")
    sessions_picker.open_session(USER, old)
    sessions_db.delete(old)

    assert get_or_create_buddy(USER)["session_id"] == b["session_id"]


# --- API ------------------------------------------------------------------------

def test_api_list_and_open(client, auth_headers):
    me = client.get("/api/buddy/state", headers=auth_headers).json()
    from hydrahive.db import sessions as sessions_db

    old = sessions_db.create(agent_id=me["agent_id"], user_id="testuser", title="x").id
    _say(old, "user", "alte Frage")
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE sessions SET created_at = '2026-01-01T00:00:00+00:00', "
                     "updated_at = '2026-01-01T00:00:00+00:00' WHERE id = ?", (old,))

    lst = client.get("/api/buddy/sessions", headers=auth_headers).json()
    assert old in [s["id"] for s in lst["sessions"]]

    r = client.post(f"/api/buddy/sessions/{old}/open", headers=auth_headers)
    assert r.status_code == 200 and r.json()["session_id"] == old
    assert client.post("/api/buddy/sessions/01a0ffff-0000-7000-8000-000000000000/open",
                       headers=auth_headers).status_code == 404
    assert client.get("/api/buddy/sessions").status_code == 401


# --- Frontend-Vertrag ---------------------------------------------------------

FRONT = __import__("pathlib").Path(__file__).resolve().parents[2] / "frontend/src/features/buddy"


def test_frontend_picker_is_wired_into_the_buddy_header():
    page = (FRONT / "BuddyPage.tsx").read_text()
    picker = (FRONT / "_BuddySessionPicker.tsx").read_text()

    assert "<BuddySessionPicker" in page
    assert "Session: {state.session_id" not in page            # alte ID-Anzeige ersetzt
    # Gesperrt während eines Laufs (kein Wechsel mitten in der Antwort).
    assert "disabled={chat.busy || handoverBusy}" in page.split("<BuddySessionPicker", 1)[1].split("/>", 1)[0]
    assert "buddyApi.openSession(" in picker and "buddyApi.sessions(" in picker


def test_frontend_switch_reloads_only_the_tail():
    """Große Unterhaltungen (5.525 Nachrichten) öffnen nur mit dem Ende."""
    page = (FRONT / "BuddyPage.tsx").read_text()
    use_chat = (FRONT.parent / "chat/useChat.ts").read_text()

    assert "if (state?.session_id) { chat.reload(); setVisibleCount(MSG_WINDOW) }" in page
    assert "chatApi.listMessages(sessionId, RELOAD_MESSAGE_LIMIT)" in use_chat


def test_empty_sessions_are_hidden_except_the_active_one():
    """Leere Unterhaltungen (u. a. Altlasten aus F2) machen die Liste unübersichtlich."""
    from hydrahive.buddy import sessions_picker

    b = _buddy()                                         # aktuelle, noch leer → bleibt sichtbar
    empty_old = _session(b["agent_id"], at="2026-07-11T00:47:00+00:00")
    full = _session(b["agent_id"])
    _say(full, "user", "echte Frage")
    _backdate(full, "2026-07-10T16:15:00+00:00")

    ids = [s["id"] for s in sessions_picker.list_sessions(USER)["sessions"]]

    assert b["session_id"] in ids
    assert full in ids
    assert empty_old not in ids


def test_frontend_picker_looks_like_a_button():
    """Till 03.10.: „man sieht sie sehr schlecht“ — war nur grauer Text ohne Rahmen."""
    picker = (FRONT / "_BuddySessionPicker.tsx").read_text()
    knob = picker.split('title="Frühere Unterhaltungen"', 1)[1].split("</button>", 1)[0]

    assert "border " in knob and "border-fuchsia" in knob and "bg-fuchsia" in knob
    assert "Verlauf:" in knob                                   # sagt, wofür der Knopf ist
    assert "text-[#8d9ab0]" not in knob.split("className=", 1)[1].split("}`}", 1)[0]
