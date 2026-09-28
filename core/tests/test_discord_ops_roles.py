"""Serververwaltung: Rollen anlegen, ändern, löschen, zuweisen, entziehen.

Spec: docs/specs/discord-server-admin-tools.md, discord_member_manage (Rollen).
"""
from __future__ import annotations

import asyncio

import discord
import pytest

from tests._discord_guild_fakes import FakeGuild, FakeRole, add_member, install_guild


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def scope(monkeypatch, tmp_path):
    from hydrahive.communication.discord import ops_guild
    guild = FakeGuild()
    install_guild(monkeypatch, tmp_path, guild)
    return ops_guild.open_admin_scope("u"), guild


def test_list_roles(scope):
    from hydrahive.communication.discord import ops_roles
    s, guild = scope
    out = run(ops_roles.list_roles(s, guild_id=str(guild.id)))
    assert "Admin" in out and "Bot" in out and "@everyone" in out
    assert "administrator" in out  # Rechte der Admin-Rolle werden genannt


def test_rolle_anlegen_mit_rechten_und_farbe(scope):
    from hydrahive.communication.discord import ops_roles
    s, guild = scope
    out = run(ops_roles.create_role(s, "", guild_id=str(guild.id), name="Team", color="#3366ff",
                                    permissions=["send_messages", "manage_messages"],
                                    mentionable=True, hoist=True))
    role = guild.roles[-1]
    assert role.name == "Team" and role.created_with["colour"].value == 0x3366FF
    assert role.created_with["permissions"].manage_messages
    assert role.created_with["mentionable"] is True and role.created_with["hoist"] is True
    assert role.created_with["reason"].startswith("HydraHive-Agent")
    assert "Team" in out and str(role.id) in out


def test_rolle_mit_admin_recht_wird_abgelehnt(scope):
    from hydrahive.communication.discord import ops_access, ops_roles
    s, guild = scope
    with pytest.raises(ops_access.DiscordToolError, match="nie vergeben"):
        run(ops_roles.create_role(s, "", guild_id=str(guild.id), name="Boss", permissions=["administrator"]))
    assert all(r.name != "Boss" for r in guild.roles)


def test_ungueltige_farbe(scope):
    from hydrahive.communication.discord import ops_access, ops_roles
    s, guild = scope
    with pytest.raises(ops_access.DiscordToolError, match="Farbe"):
        run(ops_roles.create_role(s, "", guild_id=str(guild.id), name="Bunt", color="blau"))


def test_rolle_aendern_nur_unterhalb_bot(scope):
    from hydrahive.communication.discord import ops_access, ops_roles
    s, guild = scope
    team = FakeRole(50, "Team", 2)
    guild.roles.append(team)
    out = run(ops_roles.edit_role(s, "", guild_id=str(guild.id), role_id="50", name="Crew",
                                  permissions=["send_messages"]))
    assert team.name == "Crew" and team.edited_with["permissions"].send_messages
    assert "Crew" in out
    with pytest.raises(ops_access.DiscordToolError, match="Bot-Rolle"):
        run(ops_roles.edit_role(s, "", guild_id=str(guild.id), role_id=str(guild.admin_role.id), name="x"))


def test_rolle_loeschen(scope):
    from hydrahive.communication.discord import ops_access, ops_roles
    s, guild = scope
    team = FakeRole(50, "Team", 2)
    guild.roles.append(team)
    out = run(ops_roles.delete_role(s, guild_id=str(guild.id), role_id="50"))
    assert team.deleted_with.startswith("HydraHive-Agent") and "Team" in out
    with pytest.raises(ops_access.DiscordToolError, match="@everyone"):
        run(ops_roles.delete_role(s, guild_id=str(guild.id), role_id=str(guild.everyone.id)))


def test_rolle_zuweisen_und_entziehen(scope):
    from hydrahive.communication.discord import ops_access, ops_roles
    s, guild = scope
    team = FakeRole(50, "Team", 2)
    guild.roles.append(team)
    gast = add_member(guild, 777, "gast")
    out = run(ops_roles.assign_role(s, guild_id=str(guild.id), user_id="777", role_id="50"))
    assert team in gast.roles and "Team" in out and "gast" in out
    out = run(ops_roles.remove_role(s, guild_id=str(guild.id), user_id="777", role_id="50"))
    assert team not in gast.roles and "entzogen" in out
    # Serverbesitzer ist geschützt, auch beim Entziehen
    with pytest.raises(ops_access.DiscordToolError, match="Serverbesitzer"):
        run(ops_roles.remove_role(s, guild_id=str(guild.id), user_id=str(guild.owner.id), role_id="50"))
    # Rolle über der Bot-Rolle kann nicht zugewiesen werden
    with pytest.raises(ops_access.DiscordToolError, match="Bot-Rolle"):
        run(ops_roles.assign_role(s, guild_id=str(guild.id), user_id="777", role_id=str(guild.admin_role.id)))


def test_zuweisen_an_geschuetzte_person_erlaubt_kein_entziehen_bei_besitzer_id(monkeypatch, tmp_path):
    from hydrahive.communication.discord import ops_access, ops_guild, ops_roles
    guild = FakeGuild()
    install_guild(monkeypatch, tmp_path, guild, owner_user_ids=["555"])
    s = ops_guild.open_admin_scope("u")
    team = FakeRole(50, "Team", 2)
    guild.roles.append(team)
    till = add_member(guild, 555, "till")
    # Zuweisen ist harmlos und erlaubt …
    run(ops_roles.assign_role(s, guild_id=str(guild.id), user_id="555", role_id="50"))
    assert team in till.roles
    # … entziehen nicht.
    with pytest.raises(ops_access.DiscordToolError, match="Besitzer-ID"):
        run(ops_roles.remove_role(s, guild_id=str(guild.id), user_id="555", role_id="50"))
    assert isinstance(discord.Permissions.none(), discord.Permissions)
