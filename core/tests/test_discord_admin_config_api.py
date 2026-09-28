"""Serverfreigabe für die Discord-Verwaltungswerkzeuge: Config + Katalog.

Spec: docs/specs/discord-server-admin-tools.md, Abschnitt 3.
"""
from __future__ import annotations

from types import SimpleNamespace

import discord
import pytest

from tests._discord_fakes import perms


@pytest.fixture
def discord_dir(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setitem(settings.__dict__, "discord_config_dir", tmp_path)
    return tmp_path


def _base(**over):
    cfg = {"bot_token": "", "dm_enabled": True, "mention_enabled": True, "require_keyword": "",
           "allowed_user_ids": [], "blocked_user_ids": [], "allowed_channel_ids": [],
           "respond_as_voice": False, "voice_name": "German_FriendlyMan"}
    cfg.update(over)
    return cfg


def test_admin_guild_ids_roundtrip_und_bleiben_ohne_key_erhalten(client, auth_headers, discord_dir):
    url = "/api/communication/discord/config"
    r = client.put(url, headers=auth_headers, json=_base(admin_guild_ids=[" 77 ", "77", "88"]))
    assert r.status_code == 200, r.text
    assert r.json()["admin_guild_ids"] == ["77", "88"]
    # Älteres Frontend ohne den Key darf die Freigabe nicht still löschen.
    r = client.put(url, headers=auth_headers, json=_base(require_keyword="!bot"))
    assert r.status_code == 200
    assert client.get(url, headers=auth_headers).json()["admin_guild_ids"] == ["77", "88"]
    r = client.put(url, headers=auth_headers, json=_base(admin_guild_ids=[]))
    assert r.json()["admin_guild_ids"] == []


def test_config_default_ohne_serverfreigabe(discord_dir):
    from hydrahive.communication.discord import config as dc_config
    assert dc_config.load("niemand").admin_guild_ids == []


def test_katalog_liefert_server_mit_admin_faehigkeit(client, auth_headers, monkeypatch):
    from hydrahive.communication import registry

    def ch(cid, name, pos):
        return SimpleNamespace(id=cid, type=discord.ChannelType.text, name=name, position=pos,
                               category=None, permissions_for=lambda _m: perms(view_channel=True))

    me_admin = SimpleNamespace(guild_permissions=discord.Permissions(administrator=True))
    me_plain = SimpleNamespace(guild_permissions=discord.Permissions(view_channel=True))
    g1 = SimpleNamespace(id=1, name="HydraHive", me=me_admin, member_count=3,
                         channels=[ch(11, "allgemein", 0)])
    g2 = SimpleNamespace(id=2, name="FlowKI Club", me=me_plain, member_count=250,
                         channels=[ch(22, "lounge", 0)])
    fake_client = SimpleNamespace(guilds=[g1, g2])
    adapter = SimpleNamespace(name="discord", label="Discord",
                              client_for=lambda u: fake_client if u == "testuser" else None)
    monkeypatch.setitem(registry._REGISTRY, "discord", adapter)

    r = client.get("/api/communication/discord/channels", headers=auth_headers)
    assert r.status_code == 200, r.text
    guilds = {g["id"]: g for g in r.json()["guilds"]}
    assert guilds["1"] == {"id": "1", "name": "HydraHive", "can_admin": True, "members": 3}
    assert guilds["2"]["can_admin"] is False
    # Kanäle wie bisher
    assert {c["id"] for c in r.json()["channels"]} == {"11", "22"}
