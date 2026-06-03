"""Tests für db/teamchat.py — identities, rooms, room_agents.

TDD: Tests wurden zuerst geschrieben, dann die Implementierung.
Lazy imports innerhalb jeder Test-Funktion (Projekt-Gotcha: top-level
hydrahive-Import friert settings.data_dir zur Collection-Zeit ein).
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db.connection import db

    init_db()
    yield
    # Tabellen nach jedem Test leeren damit Tests isoliert bleiben
    with db() as conn:
        conn.execute("DELETE FROM teamchat_room_agents")
        conn.execute("DELETE FROM teamchat_rooms")
        conn.execute("DELETE FROM teamchat_identities")


# ---------------------------------------------------------------------------
# identities
# ---------------------------------------------------------------------------

def test_upsert_identity_und_get_roundtrip():
    from hydrahive.db import teamchat

    row = teamchat.upsert_identity(
        user_id="user-1",
        mxid="@user1:matrix.example.org",
        access_token="syt_secret_token",
    )
    assert row["user_id"] == "user-1"
    assert row["mxid"] == "@user1:matrix.example.org"
    assert row["access_token"] == "syt_secret_token"
    assert row["device_id"] is None
    assert row["next_batch"] is None
    assert row["created_at"] is not None

    fetched = teamchat.get_identity("user-1")
    assert fetched is not None
    assert fetched["user_id"] == "user-1"
    assert fetched["access_token"] == "syt_secret_token"


def test_upsert_identity_mit_device_id():
    from hydrahive.db import teamchat

    row = teamchat.upsert_identity(
        user_id="user-2",
        mxid="@user2:matrix.example.org",
        access_token="syt_other_token",
        device_id="DEVXYZ",
    )
    assert row["device_id"] == "DEVXYZ"


def test_upsert_identity_aktualisiert_bei_zweitem_aufruf():
    """Re-Provisioning überschreibt statt zu duplizieren."""
    from hydrahive.db import teamchat

    teamchat.upsert_identity(
        user_id="user-3",
        mxid="@user3:matrix.example.org",
        access_token="old_token",
    )
    updated = teamchat.upsert_identity(
        user_id="user-3",
        mxid="@user3:matrix.example.org",
        access_token="new_token",
        device_id="DEV_NEW",
    )
    assert updated["access_token"] == "new_token"
    assert updated["device_id"] == "DEV_NEW"

    # Nur eine Zeile in der DB
    from hydrahive.db.connection import db
    with db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM teamchat_identities WHERE user_id = 'user-3'"
        ).fetchone()[0]
    assert count == 1


def test_get_identity_nicht_vorhanden_gibt_none():
    from hydrahive.db import teamchat

    assert teamchat.get_identity("nonexistent-user") is None


def test_update_next_batch():
    from hydrahive.db import teamchat

    teamchat.upsert_identity(
        user_id="user-4",
        mxid="@user4:matrix.example.org",
        access_token="tok",
    )
    teamchat.update_next_batch("user-4", "s12345_6789_0_1_2_3_4_5_6")

    row = teamchat.get_identity("user-4")
    assert row["next_batch"] == "s12345_6789_0_1_2_3_4_5_6"


def test_update_next_batch_zweimal_ueberschreibt():
    from hydrahive.db import teamchat

    teamchat.upsert_identity(
        user_id="user-5",
        mxid="@user5:matrix.example.org",
        access_token="tok",
        next_batch="old_batch",
    )
    teamchat.update_next_batch("user-5", "new_batch")
    row = teamchat.get_identity("user-5")
    assert row["next_batch"] == "new_batch"


# ---------------------------------------------------------------------------
# rooms
# ---------------------------------------------------------------------------

def test_create_room_und_get_roundtrip():
    from hydrahive.db import teamchat

    room = teamchat.create_room(
        room_id="!abc123:matrix.example.org",
        name="General",
        created_by="admin",
    )
    assert room["room_id"] == "!abc123:matrix.example.org"
    assert room["name"] == "General"
    assert room["created_by"] == "admin"
    assert room["created_at"] is not None

    fetched = teamchat.get_room("!abc123:matrix.example.org")
    assert fetched is not None
    assert fetched["name"] == "General"


def test_get_room_nicht_vorhanden_gibt_none():
    from hydrahive.db import teamchat

    assert teamchat.get_room("!nonexistent:matrix.example.org") is None


def test_list_rooms_for_user_gibt_alle_raeume():
    """list_rooms_for_user gibt aktuell ALLE bekannten Räume zurück
    (Mitgliedschaft liegt in Matrix, nicht in der DB — forward-compat-arg)."""
    from hydrahive.db import teamchat

    teamchat.create_room("!room1:mx.example", "Room 1", created_by="alice")
    teamchat.create_room("!room2:mx.example", "Room 2", created_by="bob")

    rooms = teamchat.list_rooms_for_user("alice")
    room_ids = {r["room_id"] for r in rooms}
    assert "!room1:mx.example" in room_ids
    assert "!room2:mx.example" in room_ids


def test_list_rooms_for_user_sortiert_nach_created_at():
    from hydrahive.db import teamchat

    teamchat.create_room("!roomA:mx.example", "Alpha", created_by="u1")
    teamchat.create_room("!roomB:mx.example", "Beta", created_by="u1")

    # created_at deterministisch setzen (SQLite-strftime: 1s-Auflösung).
    # roomB bewusst FRÜHER als roomA, obwohl roomA zuerst erstellt wurde —
    # so prüft der Assert die ORDER BY created_at echt.
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            "UPDATE teamchat_rooms SET created_at = ? WHERE room_id = ?",
            ("2026-01-01T00:00:00Z", "!roomB:mx.example"),
        )
        conn.execute(
            "UPDATE teamchat_rooms SET created_at = ? WHERE room_id = ?",
            ("2026-01-01T00:00:01Z", "!roomA:mx.example"),
        )

    rooms = teamchat.list_rooms_for_user("u1")
    ours = [r["room_id"] for r in rooms if r["room_id"] in ("!roomA:mx.example", "!roomB:mx.example")]
    assert ours == ["!roomB:mx.example", "!roomA:mx.example"]


def test_update_room_name():
    from hydrahive.db import teamchat

    teamchat.create_room("!rn:mx.example", "Alt", created_by="admin")
    teamchat.update_room_name("!rn:mx.example", "Neu")
    assert teamchat.get_room("!rn:mx.example")["name"] == "Neu"


def test_delete_room_entfernt_raum_und_agents():
    from hydrahive.db import teamchat

    teamchat.create_room("!rd:mx.example", "Weg", created_by="admin")
    teamchat.attach_agent("!rd:mx.example", "agent-x", attached_by="admin")
    teamchat.delete_room("!rd:mx.example")
    assert teamchat.get_room("!rd:mx.example") is None
    assert teamchat.list_room_agents("!rd:mx.example") == []


# ---------------------------------------------------------------------------
# room_agents
# ---------------------------------------------------------------------------

def test_attach_agent_und_list_room_agents():
    from hydrahive.db import teamchat

    teamchat.create_room("!r1:mx.example", "Test Room", created_by="admin")
    teamchat.attach_agent("!r1:mx.example", "agent-001", attached_by="admin")

    agents = teamchat.list_room_agents("!r1:mx.example")
    assert len(agents) == 1
    assert agents[0]["room_id"] == "!r1:mx.example"
    assert agents[0]["agent_id"] == "agent-001"
    assert agents[0]["attached_by"] == "admin"
    assert agents[0]["attached_at"] is not None


def test_attach_agent_idempotent():
    """Zweimaliges Anhängen darf nicht duplizieren."""
    from hydrahive.db import teamchat

    teamchat.create_room("!r2:mx.example", "Idempotent Room", created_by="admin")
    teamchat.attach_agent("!r2:mx.example", "agent-002", attached_by="admin")
    teamchat.attach_agent("!r2:mx.example", "agent-002", attached_by="admin")

    agents = teamchat.list_room_agents("!r2:mx.example")
    assert len(agents) == 1


def test_detach_agent():
    from hydrahive.db import teamchat

    teamchat.create_room("!r3:mx.example", "Detach Room", created_by="admin")
    teamchat.attach_agent("!r3:mx.example", "agent-003", attached_by="admin")
    teamchat.detach_agent("!r3:mx.example", "agent-003")

    agents = teamchat.list_room_agents("!r3:mx.example")
    assert agents == []


def test_list_room_agents_sortiert_nach_attached_at():
    from hydrahive.db import teamchat
    from hydrahive.db.connection import db

    teamchat.create_room("!r4:mx.example", "Multi-Agent Room", created_by="admin")
    teamchat.attach_agent("!r4:mx.example", "agent-A", attached_by="admin")
    teamchat.attach_agent("!r4:mx.example", "agent-B", attached_by="admin")

    # attached_at deterministisch setzen — SQLite-strftime hat nur 1s-Auflösung,
    # ein sleep wäre unzuverlässig. agent-B bewusst FRÜHER als agent-A, obwohl
    # agent-A zuerst attached wurde — so prüft der Assert die ORDER BY echt.
    with db() as conn:
        conn.execute(
            "UPDATE teamchat_room_agents SET attached_at = ? WHERE room_id = ? AND agent_id = ?",
            ("2026-01-01T00:00:00Z", "!r4:mx.example", "agent-B"),
        )
        conn.execute(
            "UPDATE teamchat_room_agents SET attached_at = ? WHERE room_id = ? AND agent_id = ?",
            ("2026-01-01T00:00:01Z", "!r4:mx.example", "agent-A"),
        )

    agents = teamchat.list_room_agents("!r4:mx.example")
    assert [a["agent_id"] for a in agents] == ["agent-B", "agent-A"]


def test_list_room_agents_leerer_raum():
    from hydrahive.db import teamchat

    teamchat.create_room("!r5:mx.example", "Empty Room", created_by="admin")
    assert teamchat.list_room_agents("!r5:mx.example") == []
