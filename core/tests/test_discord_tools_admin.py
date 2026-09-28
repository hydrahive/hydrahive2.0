"""Tool-Hüllen discord_server_manage / discord_member_manage und die
argumentabhängige Bestätigung im Runner.

Spec: docs/specs/discord-server-admin-tools.md, Abschnitte 2 und 5.
"""
from __future__ import annotations

import asyncio

import discord
import pytest

from tests._discord_fakes import ctx
from tests._discord_guild_fakes import FakeGuild, FakeRole, add_member, install_guild


def run(coro):
    return asyncio.run(coro)


def _tools():
    from hydrahive.tools import discord_admin
    return discord_admin


@pytest.fixture
def guild(monkeypatch, tmp_path):
    g = FakeGuild()
    install_guild(monkeypatch, tmp_path, g)
    return g


def test_beide_werkzeuge_registriert_und_optional():
    from hydrahive.tools import OPTIONAL_TOOLS
    t = _tools()
    assert {x.name for x in t.TOOLS} == {"discord_server_manage", "discord_member_manage"}
    assert {"discord_server_manage", "discord_member_manage"} <= OPTIONAL_TOOLS
    assert "ausdrückliche Anweisung" in (t.TOOL_SERVER.prompt_hint or "")
    assert "ausdrückliche Anweisung" in (t.TOOL_MEMBER.prompt_hint or "")


def test_ohne_freigabe_fail(monkeypatch, tmp_path):
    g = FakeGuild()
    install_guild(monkeypatch, tmp_path, g, admin_ids=[])
    r = run(_tools().TOOL_SERVER.execute({"action": "overview", "guild_id": "1"}, ctx()))
    assert not r.success and "Server verwalten" in (r.error or "")


def test_unbekannte_aktion(guild):
    r = run(_tools().TOOL_SERVER.execute({"action": "explodieren", "guild_id": "1"}, ctx()))
    assert not r.success and "explodieren" in (r.error or "")


def test_server_overview_und_create(guild):
    t = _tools()
    r = run(t.TOOL_SERVER.execute({"action": "overview", "guild_id": "1"}, ctx()))
    assert r.success and "HydraHive" in r.output
    r = run(t.TOOL_SERVER.execute({"action": "create_channel", "guild_id": "1", "name": "news",
                                   "kind": "news"}, ctx()))
    assert r.success and "#news" in r.output and guild.channels[-1].created_with["news"] is True
    r = run(t.TOOL_SERVER.execute({"action": "create_channel", "guild_id": "1", "name": "ideen",
                                   "kind": "forum", "tags": "Bug, Wunsch", "require_tag": True}, ctx()))
    assert r.success and [x.name for x in guild.channels[-1].created_with["available_tags"]] == ["Bug", "Wunsch"]


def test_member_kick_ueber_tool(guild):
    gast = add_member(guild, 777, "gast")
    r = run(_tools().TOOL_MEMBER.execute({"action": "kick", "guild_id": "1", "user_id": "777",
                                          "reason": "Spam"}, ctx()))
    assert r.success and gast.actions[-1][0] == "kick"


def test_member_create_role_ueber_tool(guild):
    r = run(_tools().TOOL_MEMBER.execute({"action": "create_role", "guild_id": "1", "name": "Team",
                                          "permissions": "send_messages, manage_messages"}, ctx()))
    assert r.success and guild.roles[-1].name == "Team"
    assert guild.roles[-1].created_with["permissions"].manage_messages


def test_bestaetigung_je_nach_aktion():
    from hydrahive.tools._discord_admin_confirm import confirm_reason
    assert confirm_reason("discord_server_manage", {"action": "overview"}) is None
    assert confirm_reason("discord_server_manage", {"action": "create_channel"}) is None
    assert "löschen" in confirm_reason("discord_server_manage", {"action": "delete_channel"}).lower()
    assert "Rechte" in confirm_reason("discord_server_manage", {"action": "set_permissions"})
    assert confirm_reason("discord_member_manage", {"action": "list_members"}) is None
    assert confirm_reason("discord_member_manage", {"action": "set_nickname"}) is None
    assert "Kick" in confirm_reason("discord_member_manage", {"action": "kick"})
    assert "Bann" in confirm_reason("discord_member_manage", {"action": "ban"})
    assert "Rolle" in confirm_reason("discord_member_manage", {"action": "delete_role"})
    # Rollen mit riskanten Rechten: Bestätigung mit Nennung der Rechte
    r = confirm_reason("discord_member_manage", {"action": "create_role", "permissions": ["kick_members"]})
    assert r and "Mitglieder kicken" in r
    assert confirm_reason("discord_member_manage", {"action": "create_role", "permissions": ["send_messages"]}) is None
    assert confirm_reason("discord_member_manage", {"action": "assign_role", "role_id": "5"}) is not None
    assert confirm_reason("shell_exec", {"cmd": "ls"}) is None


def test_runner_verlangt_bestaetigung_fuer_kick(monkeypatch, tmp_path):
    from hydrahive.runner import _runner_tools, tool_confirmation
    from hydrahive.runner.events import ToolConfirmRequired
    from hydrahive.tools import ToolResult
    from tests.test_runner_harakiri_confirm import _ctx, _deny, _drive

    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    tool_confirmation._pending.clear()
    executed = []

    async def _fake_exec(*, tool_use, allowed_tools, ctx, parent_message_id, iteration=None):
        executed.append(tool_use["name"])
        return ToolResult.ok("weg"), "rec1", 5

    monkeypatch.setattr(tool_confirmation, "wait", _deny)
    monkeypatch.setattr(_runner_tools, "execute_tool", _fake_exec)
    events = asyncio.run(_drive(
        [{"id": "c9", "name": "discord_member_manage",
          "input": {"action": "kick", "guild_id": "1", "user_id": "777"}}],
        _ctx(tmp_path),
    ))
    confirms = [e for e in events if isinstance(e, ToolConfirmRequired)]
    assert len(confirms) == 1 and "Kick" in (confirms[0].reason or "")
    assert executed == []
    assert isinstance(FakeRole(1, "x", 1).permissions, discord.Permissions)
