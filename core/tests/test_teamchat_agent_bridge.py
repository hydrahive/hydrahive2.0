"""agent_bridge.is_addressed — Anrede-Erkennung (TDD).

Reine Funktion, kein I/O. Die Test-Fälle SIND die Verhaltens-Entscheidung
("mittel"-Heuristik): ein Agent reagiert auf explizite @-Anrede / Matrix-
m.mentions und auf den Namen als vokativische Anrede (Wortgrenze am Anfang
oder an einem Komma/Doppelpunkt) — aber NICHT auf den Namen beiläufig im
Fließtext.
"""
from __future__ import annotations


def _is_addressed(text, agent_name, **kwargs):
    """Lazy import (settings.data_dir-Freeze-Gotcha)."""
    from hydrahive.teamchat.agent_bridge import is_addressed
    return is_addressed(text, agent_name, **kwargs)


# ---------------------------------------------------------------- @-Anrede

def test_at_mention_triggert():
    assert _is_addressed("@buddy hallo, wie gehts?", "buddy") is True


def test_at_mention_case_insensitive():
    assert _is_addressed("@Buddy hallo", "buddy") is True


# ---------------------------------------------------------------- Matrix m.mentions

def test_matrix_mention_triggert():
    """Steht der Bot-MXID in m.mentions, ist er adressiert — Text egal."""
    assert _is_addressed(
        "kann das mal jemand prüfen",
        "buddy",
        mention_mxids=["@agent-buddy:masternode.hydrahive.org"],
        bot_mxid="@agent-buddy:masternode.hydrahive.org",
    ) is True


def test_matrix_mention_anderer_bot_triggert_nicht():
    """Eine Mention eines ANDEREN Bots adressiert mich nicht."""
    assert _is_addressed(
        "frag mal jemand",
        "buddy",
        mention_mxids=["@agent-zahnfee:masternode.hydrahive.org"],
        bot_mxid="@agent-buddy:masternode.hydrahive.org",
    ) is False


# ---------------------------------------------------------------- Vokativ (Name als Anrede)

def test_name_am_anfang_triggert():
    """'buddy mach X' — Name als ganzes Wort am Satzanfang."""
    assert _is_addressed("buddy mach mir eine Liste", "buddy") is True


def test_name_am_anfang_mit_komma_triggert():
    assert _is_addressed("buddy, kannst du das übernehmen?", "buddy") is True


def test_name_vor_doppelpunkt_triggert():
    assert _is_addressed("hey buddy: schau dir das an", "buddy") is True


def test_name_als_nachgestellte_anrede_triggert():
    """'..., buddy' — Name am Ende nach Komma (typischer Vokativ)."""
    assert _is_addressed("mach das bitte mal, buddy", "buddy") is True


# ---------------------------------------------------------------- KEINE Fehlauslösung

def test_name_beilaeufig_triggert_nicht():
    """'ich frag mal buddy ob ...' — über den Agenten reden ≠ ihn anreden."""
    assert _is_addressed("ich frag nachher mal buddy ob er Zeit hat", "buddy") is False


def test_teilwort_triggert_nicht():
    """'buddybear' enthält 'buddy', ist aber ein anderes Wort."""
    assert _is_addressed("buddybear ist ein anderer name", "buddy") is False


def test_kein_name_kein_mention_triggert_nicht():
    assert _is_addressed("guten morgen zusammen", "buddy") is False


def test_leerer_text_triggert_nicht():
    assert _is_addressed("", "buddy") is False


# ===========================================================================
# respond_if_addressed — Orchestrierung (welche Agents reagieren)
# ===========================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _fresh_guard():
    from hydrahive.teamchat.loop_guard import LoopGuard
    return LoopGuard()


def _bot_tokens(mxid="@agent-buddy:s"):
    from hydrahive.teamchat.client import AccountTokens
    return AccountTokens(user_id=mxid, access_token="tok", device_id="D")


def _cfg(agent_id, name, *, status="active", owner="till"):
    return {"id": agent_id, "name": name, "owner": owner, "status": status}


@pytest.mark.asyncio
async def test_respond_addressed_runs_agent():
    """Agent zugeschaltet + angesprochen → _run_and_post wird gerufen."""
    db = MagicMock(); db.list_room_agents.return_value = [{"agent_id": "a1"}]
    cfgmod = MagicMock(); cfgmod.get.return_value = _cfg("a1", "buddy")
    with (
        patch("hydrahive.teamchat.agent_bridge.db_teamchat", db),
        patch("hydrahive.teamchat.agent_bridge.agent_config", cfgmod),
        patch("hydrahive.teamchat.agent_bridge.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_bridge._loop_guard", new=_fresh_guard()),
        patch("hydrahive.teamchat.agent_bridge._run_and_post", new=AsyncMock()) as run_post,
    ):
        from hydrahive.teamchat.agent_bridge import respond_if_addressed
        await respond_if_addressed("!r:s", "alice", "buddy, hilf mir")
    run_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_respond_not_addressed_stays_silent():
    """Nicht angesprochen → _run_and_post wird NICHT gerufen."""
    db = MagicMock(); db.list_room_agents.return_value = [{"agent_id": "a1"}]
    cfgmod = MagicMock(); cfgmod.get.return_value = _cfg("a1", "buddy")
    with (
        patch("hydrahive.teamchat.agent_bridge.db_teamchat", db),
        patch("hydrahive.teamchat.agent_bridge.agent_config", cfgmod),
        patch("hydrahive.teamchat.agent_bridge.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_bridge._loop_guard", new=_fresh_guard()),
        patch("hydrahive.teamchat.agent_bridge._run_and_post", new=AsyncMock()) as run_post,
    ):
        from hydrahive.teamchat.agent_bridge import respond_if_addressed
        await respond_if_addressed("!r:s", "alice", "guten morgen zusammen")
    run_post.assert_not_awaited()


@pytest.mark.asyncio
async def test_respond_no_agents_does_nothing():
    """Kein Agent im Raum → kein ensure_bot_identity, kein Post."""
    db = MagicMock(); db.list_room_agents.return_value = []
    ensure = AsyncMock()
    with (
        patch("hydrahive.teamchat.agent_bridge.db_teamchat", db),
        patch("hydrahive.teamchat.agent_bridge.ensure_bot_identity", new=ensure),
        patch("hydrahive.teamchat.agent_bridge._loop_guard", new=_fresh_guard()),
        patch("hydrahive.teamchat.agent_bridge._run_and_post", new=AsyncMock()) as run_post,
    ):
        from hydrahive.teamchat.agent_bridge import respond_if_addressed
        await respond_if_addressed("!r:s", "alice", "buddy, hilf")
    ensure.assert_not_awaited()
    run_post.assert_not_awaited()


@pytest.mark.asyncio
async def test_respond_loopguard_open_skips():
    """LoopGuard offen → angesprochener Agent wird übersprungen."""
    db = MagicMock(); db.list_room_agents.return_value = [{"agent_id": "a1"}]
    cfgmod = MagicMock(); cfgmod.get.return_value = _cfg("a1", "buddy")
    guard = MagicMock(); guard.check.return_value = True
    with (
        patch("hydrahive.teamchat.agent_bridge.db_teamchat", db),
        patch("hydrahive.teamchat.agent_bridge.agent_config", cfgmod),
        patch("hydrahive.teamchat.agent_bridge.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_bridge._loop_guard", new=guard),
        patch("hydrahive.teamchat.agent_bridge._run_and_post", new=AsyncMock()) as run_post,
    ):
        from hydrahive.teamchat.agent_bridge import respond_if_addressed
        await respond_if_addressed("!r:s", "alice", "buddy, hilf")
    run_post.assert_not_awaited()


@pytest.mark.asyncio
async def test_respond_only_addressed_of_many_runs():
    """Zwei Agents, nur einer angesprochen → nur der läuft."""
    db = MagicMock(); db.list_room_agents.return_value = [{"agent_id": "a1"}, {"agent_id": "a2"}]
    cfgmod = MagicMock()
    cfgmod.get.side_effect = lambda aid: {"a1": _cfg("a1", "buddy"), "a2": _cfg("a2", "zahnfee")}[aid]
    with (
        patch("hydrahive.teamchat.agent_bridge.db_teamchat", db),
        patch("hydrahive.teamchat.agent_bridge.agent_config", cfgmod),
        patch("hydrahive.teamchat.agent_bridge.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_bridge._loop_guard", new=_fresh_guard()),
        patch("hydrahive.teamchat.agent_bridge._run_and_post", new=AsyncMock()) as run_post,
    ):
        from hydrahive.teamchat.agent_bridge import respond_if_addressed
        await respond_if_addressed("!r:s", "alice", "zahnfee, mach das")
    run_post.assert_awaited_once()
    # der gelaufene Agent ist a2 (zahnfee)
    assert run_post.await_args.args[1] == "a2"


@pytest.mark.asyncio
async def test_respond_disabled_agent_skipped():
    """Deaktivierter Agent reagiert nicht, auch wenn angesprochen."""
    db = MagicMock(); db.list_room_agents.return_value = [{"agent_id": "a1"}]
    cfgmod = MagicMock(); cfgmod.get.return_value = _cfg("a1", "buddy", status="disabled")
    ensure = AsyncMock()
    with (
        patch("hydrahive.teamchat.agent_bridge.db_teamchat", db),
        patch("hydrahive.teamchat.agent_bridge.agent_config", cfgmod),
        patch("hydrahive.teamchat.agent_bridge.ensure_bot_identity", new=ensure),
        patch("hydrahive.teamchat.agent_bridge._loop_guard", new=_fresh_guard()),
        patch("hydrahive.teamchat.agent_bridge._run_and_post", new=AsyncMock()) as run_post,
    ):
        from hydrahive.teamchat.agent_bridge import respond_if_addressed
        await respond_if_addressed("!r:s", "alice", "buddy, hilf")
    run_post.assert_not_awaited()


@pytest.mark.asyncio
async def test_respond_agent_error_does_not_propagate():
    """Ein abstürzender Agent darf die Background-Task nicht hochreißen."""
    db = MagicMock(); db.list_room_agents.return_value = [{"agent_id": "a1"}]
    cfgmod = MagicMock(); cfgmod.get.return_value = _cfg("a1", "buddy")
    with (
        patch("hydrahive.teamchat.agent_bridge.db_teamchat", db),
        patch("hydrahive.teamchat.agent_bridge.agent_config", cfgmod),
        patch("hydrahive.teamchat.agent_bridge.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_bridge._loop_guard", new=_fresh_guard()),
        patch("hydrahive.teamchat.agent_bridge._run_and_post", new=AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        from hydrahive.teamchat.agent_bridge import respond_if_addressed
        # darf NICHT werfen
        await respond_if_addressed("!r:s", "alice", "buddy, hilf")


# ===========================================================================
# _run_and_post — Matrix-I/O (Typing, Bot-Post, Broadcast)
# ===========================================================================

def _mock_client():
    client = MagicMock()
    client.room_typing = AsyncMock()
    send_resp = MagicMock(); send_resp.event_id = "$evt:s"
    client.room_send = AsyncMock(return_value=send_resp)
    client.close = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_run_and_post_posts_and_broadcasts():
    """Antwort wird als Bot gepostet und gebroadcastet, Client geschlossen."""
    client = _mock_client()
    bcast = MagicMock()
    with (
        patch("hydrahive.teamchat.agent_bridge.build_client", return_value=client),
        patch("hydrahive.teamchat.agent_bridge.run_agent_for_event", new=AsyncMock(return_value="Hallo zusammen!")),
        patch("hydrahive.teamchat.agent_bridge.room_broadcaster", bcast),
    ):
        from hydrahive.teamchat.agent_bridge import _run_and_post
        await _run_and_post("!r:s", "a1", _cfg("a1", "buddy"), _bot_tokens(), "alice", "buddy, hi")

    client.room_send.assert_awaited_once()
    sent = client.room_send.await_args
    assert sent.kwargs.get("content", {}).get("body") == "Hallo zusammen!" or "Hallo zusammen!" in str(sent)
    bcast.broadcast.assert_called_once()
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_and_post_empty_answer_no_post():
    """Leere Antwort → kein room_send, aber Client wird sauber geschlossen."""
    client = _mock_client()
    bcast = MagicMock()
    with (
        patch("hydrahive.teamchat.agent_bridge.build_client", return_value=client),
        patch("hydrahive.teamchat.agent_bridge.run_agent_for_event", new=AsyncMock(return_value="   ")),
        patch("hydrahive.teamchat.agent_bridge.room_broadcaster", bcast),
    ):
        from hydrahive.teamchat.agent_bridge import _run_and_post
        await _run_and_post("!r:s", "a1", _cfg("a1", "buddy"), _bot_tokens(), "alice", "buddy, hi")

    client.room_send.assert_not_awaited()
    bcast.broadcast.assert_not_called()
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_and_post_typing_off_even_when_run_fails():
    """Agent-Run wirft → Typing wird trotzdem beendet und Client geschlossen."""
    client = _mock_client()
    with (
        patch("hydrahive.teamchat.agent_bridge.build_client", return_value=client),
        patch("hydrahive.teamchat.agent_bridge.run_agent_for_event",
              new=AsyncMock(side_effect=RuntimeError("boom"))),
        patch("hydrahive.teamchat.agent_bridge.room_broadcaster", MagicMock()),
    ):
        from hydrahive.teamchat.agent_bridge import _run_and_post
        with pytest.raises(RuntimeError):
            await _run_and_post("!r:s", "a1", _cfg("a1", "buddy"), _bot_tokens(), "alice", "buddy hi")

    # Typing wurde auf False gesetzt (Indikator hängt nicht 30s), Client geschlossen
    assert any(c.kwargs.get("typing_state") is False for c in client.room_typing.await_args_list)
    client.room_send.assert_not_awaited()
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_and_post_skips_agent_without_owner():
    """Agent ohne owner → kein Run unter dem Absender (stille Fehlleitung vermeiden)."""
    client = _mock_client()
    run = AsyncMock()
    with (
        patch("hydrahive.teamchat.agent_bridge.build_client", return_value=client) as bc,
        patch("hydrahive.teamchat.agent_bridge.run_agent_for_event", new=run),
        patch("hydrahive.teamchat.agent_bridge.room_broadcaster", MagicMock()),
    ):
        from hydrahive.teamchat.agent_bridge import _run_and_post
        await _run_and_post(
            "!r:s", "a1", {"id": "a1", "name": "buddy", "owner": None},
            _bot_tokens(), "alice", "buddy hi",
        )

    run.assert_not_awaited()
    bc.assert_not_called()


# ===========================================================================
# schedule_response — fire-and-forget-Naht (für die POST-Route)
# ===========================================================================

@pytest.mark.asyncio
async def test_schedule_response_creates_task_running_respond():
    """schedule_response plant respond_if_addressed als Task."""
    with patch("hydrahive.teamchat.agent_bridge.respond_if_addressed", new=AsyncMock()) as resp:
        from hydrahive.teamchat.agent_bridge import schedule_response
        task = schedule_response("!r:s", "alice", "buddy hi")
        await task
    resp.assert_awaited_once_with("!r:s", "alice", "buddy hi", mention_mxids=None)
