"""Serververwaltung: Mitglieder — Nickname, Timeout, Kick, Ban, Unban, Liste.

Spec: docs/specs/discord-server-admin-tools.md, discord_member_manage (Mitglieder).
"""
from __future__ import annotations

import asyncio
import datetime as dt

import pytest

from tests._discord_guild_fakes import FakeGuild, FakeRole, add_member, install_guild


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def scope(monkeypatch, tmp_path):
    from hydrahive.communication.discord import ops_guild
    guild = FakeGuild()
    install_guild(monkeypatch, tmp_path, guild, owner_user_ids=["555"])
    return ops_guild.open_admin_scope("u"), guild


def test_mitgliederliste_mit_filter(scope):
    from hydrahive.communication.discord import ops_members
    s, guild = scope
    team = FakeRole(50, "Team", 2)
    guild.roles.append(team)
    add_member(guild, 777, "gast")
    add_member(guild, 778, "gustav", team)
    out = run(ops_members.list_members(s, guild_id=str(guild.id)))
    assert "gast" in out and "gustav" in out and "chef" in out and "hydrahive" in out
    out = run(ops_members.list_members(s, guild_id=str(guild.id), query="gus"))
    assert "gustav" in out and "gast" not in out
    out = run(ops_members.list_members(s, guild_id=str(guild.id), role_id="50"))
    assert "gustav" in out and "gast" not in out


def test_nickname_setzen_und_entfernen(scope):
    from hydrahive.communication.discord import ops_access, ops_members
    s, guild = scope
    gast = add_member(guild, 777, "gast")
    out = run(ops_members.set_nickname(s, "", guild_id=str(guild.id), user_id="777", nickname="Gastgeber"))
    assert gast.nick == "Gastgeber" and "Gastgeber" in out
    run(ops_members.set_nickname(s, "", guild_id=str(guild.id), user_id="777", nickname=""))
    assert gast.nick is None
    with pytest.raises(ops_access.DiscordToolError, match="Serverbesitzer"):
        run(ops_members.set_nickname(s, "", guild_id=str(guild.id), user_id=str(guild.owner.id), nickname="x"))


def test_timeout_mit_grenze(scope):
    from hydrahive.communication.discord import ops_access, ops_members
    s, guild = scope
    gast = add_member(guild, 777, "gast")
    out = run(ops_members.timeout(s, "", guild_id=str(guild.id), user_id="777", minutes=90, reason="Spam"))
    action, until, reason = gast.actions[-1]
    assert action == "timeout" and reason.startswith("HydraHive-Agent") and "Spam" in reason
    assert until - dt.datetime.now(dt.timezone.utc) < dt.timedelta(minutes=91)
    assert "90" in out
    with pytest.raises(ops_access.DiscordToolError, match="28 Tage"):
        run(ops_members.timeout(s, "", guild_id=str(guild.id), user_id="777", minutes=60 * 24 * 29))
    run(ops_members.timeout(s, "", guild_id=str(guild.id), user_id="777", minutes=0))
    assert gast.actions[-1][1] is None  # Timeout aufgehoben


def test_kick_und_ban_mit_schutz(scope):
    from hydrahive.communication.discord import ops_access, ops_members
    s, guild = scope
    gast = add_member(guild, 777, "gast")
    till = add_member(guild, 555, "till")
    out = run(ops_members.kick(s, "", guild_id=str(guild.id), user_id="777", reason="Regelverstoß"))
    assert gast.actions[-1][0] == "kick" and "Regelverstoß" in gast.actions[-1][2] and "gast" in out
    out = run(ops_members.ban(s, "", guild_id=str(guild.id), user_id="777", reason="Spam", delete_days=3))
    assert gast.actions[-1] == ("ban", 3, "HydraHive-Agent: Bann — Spam")
    assert "gebannt" in out
    with pytest.raises(ops_access.DiscordToolError, match="Besitzer-ID"):
        run(ops_members.kick(s, "", guild_id=str(guild.id), user_id="555", reason="x"))
    with pytest.raises(ops_access.DiscordToolError, match="Bot selbst"):
        run(ops_members.ban(s, "", guild_id=str(guild.id), user_id=str(guild.me.id)))
    with pytest.raises(ops_access.DiscordToolError, match="0 und 7"):
        run(ops_members.ban(s, "", guild_id=str(guild.id), user_id="777", delete_days=9))
    assert till.actions == []


def test_unban(scope):
    from hydrahive.communication.discord import ops_members
    s, guild = scope
    out = run(ops_members.unban(s, "", guild_id=str(guild.id), user_id="4242", reason="Zweite Chance"))
    assert guild.unbans[-1][0] == 4242 and "Zweite Chance" in guild.unbans[-1][1]
    assert "4242" in out


def test_grund_wird_geschwaerzt(monkeypatch, tmp_path):
    from hydrahive.communication.discord import ops_guild, ops_members
    from hydrahive.credentials import redaction
    guild = FakeGuild()
    install_guild(monkeypatch, tmp_path, guild)
    monkeypatch.setattr(redaction, "egress_secrets", lambda u, a: {"geheimes-token-abcdef123456"})
    s = ops_guild.open_admin_scope("u")
    gast = add_member(guild, 777, "gast")
    run(ops_members.kick(s, "", guild_id=str(guild.id), user_id="777", reason="Token geheimes-token-abcdef123456 gepostet"))
    assert "geheimes-token-abcdef123456" not in gast.actions[-1][2]
