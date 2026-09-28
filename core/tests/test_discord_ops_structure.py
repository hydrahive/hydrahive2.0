"""Serververwaltung: Kategorien, Kanäle, Foren, Kanalrechte, Einladung.

Spec: docs/specs/discord-server-admin-tools.md, Abschnitt 2 (discord_server_manage).
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import discord
import pytest

from tests._discord_guild_fakes import FakeGuild, FakeRole, install_guild


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def scope(monkeypatch, tmp_path):
    from hydrahive.communication.discord import ops_guild
    guild = FakeGuild()
    install_guild(monkeypatch, tmp_path, guild)
    s = ops_guild.open_admin_scope("u")
    return s, guild


def test_overview_zeigt_struktur_und_rollen(scope):
    from hydrahive.communication.discord import ops_structure
    s, guild = scope
    run(guild.create_category("Info"))
    ch = run(guild.create_text_channel("allgemein"))
    ch.category = guild.categories[0]
    out = run(ops_structure.overview(s, guild_id=str(guild.id)))
    assert "HydraHive" in out and "Info" in out and "#allgemein" in out
    assert "Admin" in out and "Bot" in out
    assert "Mitglieder: 3" in out


def test_kategorie_und_kanaele_anlegen(scope):
    from hydrahive.communication.discord import ops_structure
    s, guild = scope
    out = run(ops_structure.create_category(s, "", guild_id=str(guild.id), name="Support"))
    assert "Support" in out and guild.categories[0].name == "Support"
    cat_id = str(guild.categories[0].id)
    out = run(ops_structure.create_channel(s, "", guild_id=str(guild.id), name="fragen",
                                           kind="text", category_id=cat_id, topic="Alles fragen",
                                           slowmode=10))
    ch = guild.channels[-1]
    assert ch.name == "fragen" and ch.category is guild.categories[0]
    assert ch.created_with["topic"] == "Alles fragen" and ch.created_with["slowmode_delay"] == 10
    assert ch.created_with["reason"].startswith("HydraHive-Agent")
    assert "nicht automatisch" in out  # Hinweis auf fehlende Werkzeug-Freigabe
    out = run(ops_structure.create_channel(s, "", guild_id=str(guild.id), name="ideen",
                                           kind="forum", tags=["Bug", "Wunsch"], require_tag=True))
    forum = guild.channels[-1]
    assert forum.type == discord.ChannelType.forum
    assert [t.name for t in forum.created_with["available_tags"]] == ["Bug", "Wunsch"]
    assert "ideen" in out


def test_kanalname_wird_geprueft(scope):
    from hydrahive.communication.discord import ops_access, ops_structure
    s, guild = scope
    with pytest.raises(ops_access.DiscordToolError, match="1–100 Zeichen"):
        run(ops_structure.create_channel(s, "", guild_id=str(guild.id), name="", kind="text"))
    with pytest.raises(ops_access.DiscordToolError, match="Kanaltyp"):
        run(ops_structure.create_channel(s, "", guild_id=str(guild.id), name="x", kind="voice"))


def test_kanal_bearbeiten(scope):
    from hydrahive.communication.discord import ops_structure
    s, guild = scope
    ch = run(guild.create_text_channel("alt"))
    out = run(ops_structure.edit_channel(s, "", channel_id=str(ch.id), name="neu", topic="Thema",
                                         slowmode=5, position=2))
    assert ch.edit_calls[-1]["name"] == "neu" and ch.edit_calls[-1]["topic"] == "Thema"
    assert ch.edit_calls[-1]["slowmode_delay"] == 5 and ch.edit_calls[-1]["position"] == 2
    assert "neu" in out


def test_kanal_loeschen_und_fremder_server(monkeypatch, scope):
    from hydrahive.communication.discord import ops_access, ops_structure
    s, guild = scope
    ch = run(guild.create_text_channel("weg"))
    out = run(ops_structure.delete_channel(s, channel_id=str(ch.id)))
    assert ch.deleted_with.startswith("HydraHive-Agent") and "weg" in out
    other = FakeGuild(gid=2, name="Fremd")
    fremd = run(other.create_text_channel("fremd"))
    monkeypatch.setattr(s.client, "get_channel", other.get_channel)
    with pytest.raises(ops_access.DiscordToolError, match="nicht für die Verwaltung freigegeben"):
        run(ops_structure.delete_channel(s, channel_id=str(fremd.id)))


def test_rechte_pro_rolle_setzen(scope):
    from hydrahive.communication.discord import ops_access, ops_structure
    s, guild = scope
    ch = run(guild.create_text_channel("intern"))
    role = FakeRole(50, "Team", 2)
    guild.roles.append(role)
    calls = []

    async def set_permissions(target, *, overwrite=None, reason=""):
        calls.append((target, overwrite, reason))
    ch.set_permissions = set_permissions
    out = run(ops_structure.set_permissions(s, channel_id=str(ch.id), role_id="50",
                                            allow=["view_channel", "send_messages"], deny=["manage_messages"]))
    target, ow, reason = calls[0]
    assert target is role and reason.startswith("HydraHive-Agent")
    assert ow.pair()[0].view_channel and ow.pair()[0].send_messages and ow.pair()[1].manage_messages
    assert "Team" in out
    with pytest.raises(ops_access.DiscordToolError, match="nie vergeben"):
        run(ops_structure.set_permissions(s, channel_id=str(ch.id), role_id="50", allow=["administrator"]))


def test_einladung_erzeugen(scope):
    from hydrahive.communication.discord import ops_structure
    s, guild = scope
    ch = run(guild.create_text_channel("willkommen"))

    async def create_invite(*, max_age=0, max_uses=0, reason=""):
        return SimpleNamespace(url="https://discord.gg/abc123", max_age=max_age, max_uses=max_uses)
    ch.create_invite = create_invite
    out = run(ops_structure.create_invite(s, channel_id=str(ch.id), max_age_hours=24, max_uses=5))
    assert "https://discord.gg/abc123" in out and "24" in out and "5" in out
