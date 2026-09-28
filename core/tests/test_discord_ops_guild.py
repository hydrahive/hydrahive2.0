"""Serververwaltung: Freigabe, Rollenhierarchie, geschützte Personen, Rechte-Grenzen.

Spec: docs/specs/discord-server-admin-tools.md, Abschnitte 3 und 4.
"""
from __future__ import annotations

import asyncio

import discord
import pytest

from tests._discord_guild_fakes import FakeGuild, FakeRole, OWNER_ID, add_member, install_guild


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def guild():
    return FakeGuild()


def test_ohne_serverfreigabe_verstaendlicher_fehler(monkeypatch, tmp_path, guild):
    from hydrahive.communication.discord import ops_access, ops_guild
    install_guild(monkeypatch, tmp_path, guild, admin_ids=[])
    with pytest.raises(ops_access.DiscordToolError, match="Server verwalten"):
        ops_guild.open_admin_scope("u")


def test_nicht_freigegebener_server_wird_abgelehnt(monkeypatch, tmp_path, guild):
    from hydrahive.communication.discord import ops_access, ops_guild
    install_guild(monkeypatch, tmp_path, guild, admin_ids=["424242"])
    scope = ops_guild.open_admin_scope("u")
    with pytest.raises(ops_access.DiscordToolError, match="nicht für die Verwaltung freigegeben"):
        run(ops_guild.resolve_guild(scope, str(guild.id)))


def test_freigegebener_server_wird_geliefert(monkeypatch, tmp_path, guild):
    from hydrahive.communication.discord import ops_guild
    install_guild(monkeypatch, tmp_path, guild)
    scope = ops_guild.open_admin_scope("u")
    assert run(ops_guild.resolve_guild(scope, str(guild.id))) is guild


def test_kanal_eines_fremden_servers_ist_tabu(monkeypatch, tmp_path, guild):
    from hydrahive.communication.discord import ops_access, ops_guild
    other = FakeGuild(gid=2, name="Fremd")
    run(other.create_text_channel("geheim"))
    install_guild(monkeypatch, tmp_path, guild)
    scope = ops_guild.open_admin_scope("u")
    scope.client.get_channel = other.get_channel  # Bot kennt den Kanal, Server ist nicht frei
    with pytest.raises(ops_access.DiscordToolError, match="nicht für die Verwaltung freigegeben"):
        run(ops_guild.resolve_admin_channel(scope, "800"))


def test_rolle_ueber_bot_rolle_wird_abgelehnt(monkeypatch, tmp_path, guild):
    from hydrahive.communication.discord import ops_access, ops_guild
    install_guild(monkeypatch, tmp_path, guild)
    with pytest.raises(ops_access.DiscordToolError, match="über oder auf Höhe der Bot-Rolle"):
        ops_guild.require_role_below_bot(guild, guild.admin_role)
    with pytest.raises(ops_access.DiscordToolError, match="Bot-Rolle"):
        ops_guild.require_role_below_bot(guild, guild.bot_role)
    ops_guild.require_role_below_bot(guild, FakeRole(50, "Mitglied", 2))  # darunter: ok


def test_everyone_rolle_ist_sonderfall(guild):
    from hydrahive.communication.discord import ops_access, ops_guild
    with pytest.raises(ops_access.DiscordToolError, match="@everyone"):
        ops_guild.require_role_below_bot(guild, guild.everyone)


def test_geschuetzte_personen(monkeypatch, tmp_path, guild):
    from hydrahive.communication.discord import ops_access, ops_guild
    install_guild(monkeypatch, tmp_path, guild, owner_user_ids=["555"])
    scope = ops_guild.open_admin_scope("u")
    till = add_member(guild, 555, "till")
    normal = add_member(guild, 777, "gast")
    with pytest.raises(ops_access.DiscordToolError, match="Serverbesitzer"):
        ops_guild.require_actionable_member(scope, guild, guild.owner)
    with pytest.raises(ops_access.DiscordToolError, match="Bot selbst"):
        ops_guild.require_actionable_member(scope, guild, guild.me)
    with pytest.raises(ops_access.DiscordToolError, match="Besitzer-ID"):
        ops_guild.require_actionable_member(scope, guild, till)
    ops_guild.require_actionable_member(scope, guild, normal)


def test_mitglied_mit_hoeherer_rolle_wird_abgelehnt(monkeypatch, tmp_path, guild):
    from hydrahive.communication.discord import ops_access, ops_guild
    install_guild(monkeypatch, tmp_path, guild)
    scope = ops_guild.open_admin_scope("u")
    boss = add_member(guild, 888, "boss", guild.admin_role)
    with pytest.raises(ops_access.DiscordToolError, match="höchste Rolle"):
        ops_guild.require_actionable_member(scope, guild, boss)


def test_gefaehrliche_rechte():
    from hydrahive.communication.discord import ops_access, ops_guild
    with pytest.raises(ops_access.DiscordToolError, match="Administrator"):
        ops_guild.check_permissions(discord.Permissions(administrator=True))
    with pytest.raises(ops_access.DiscordToolError, match="Server verwalten"):
        ops_guild.check_permissions(discord.Permissions(manage_guild=True))
    # Riskante, aber erlaubte Rechte werden nur benannt (für die Bestätigung).
    risky = ops_guild.risky_permission_names(discord.Permissions(kick_members=True, manage_messages=True))
    assert risky == ["Mitglieder kicken", "Nachrichten verwalten"]
    assert ops_guild.risky_permission_names(discord.Permissions(send_messages=True)) == []


def test_permissions_aus_namen():
    from hydrahive.communication.discord import ops_access, ops_guild
    p = ops_guild.permissions_from_names(["send_messages", "manage_messages"])
    assert p.send_messages and p.manage_messages and not p.kick_members
    with pytest.raises(ops_access.DiscordToolError, match="Unbekanntes Recht"):
        ops_guild.permissions_from_names(["fliegen"])


def test_require_guild_perm_meldet_fehlendes_recht(monkeypatch, tmp_path):
    from hydrahive.communication.discord import ops_access, ops_guild
    guild = FakeGuild(bot_permissions=discord.Permissions(view_channel=True))
    with pytest.raises(ops_access.DiscordToolError, match="Kanäle verwalten"):
        ops_guild.require_guild_perm(guild, "manage_channels", "Kanäle verwalten")
    assert OWNER_ID == guild.owner_id
