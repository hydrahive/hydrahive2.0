"""API: Freigabe `tool_channel_ids` + Kanal-Katalog für die UI-Auswahl."""
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


def test_tool_channel_ids_roundtrip_and_kept_when_missing(client, auth_headers, discord_dir):
    url = "/api/communication/discord/config"
    r = client.put(url, headers=auth_headers, json=_base(tool_channel_ids=[" 10 ", "10", "20"]))
    assert r.status_code == 200
    assert r.json()["tool_channel_ids"] == ["10", "20"]
    # Älteres Frontend ohne das Feld darf die Freigabe nicht löschen
    r = client.put(url, headers=auth_headers, json=_base(require_keyword="!bot"))
    assert r.json()["tool_channel_ids"] == ["10", "20"]
    assert client.get(url, headers=auth_headers).json()["tool_channel_ids"] == ["10", "20"]
    # Explizit leeren geht
    r = client.put(url, headers=auth_headers, json=_base(tool_channel_ids=[]))
    assert r.json()["tool_channel_ids"] == []


def test_moderation_channel_ids_roundtrip_and_kept_when_missing(client, auth_headers, discord_dir):
    url = "/api/communication/discord/config"
    r = client.put(url, headers=auth_headers,
                   json=_base(tool_channel_ids=["10"], moderation_channel_ids=["10", " 10 "]))
    assert r.status_code == 200 and r.json()["moderation_channel_ids"] == ["10"]
    # Älteres Frontend ohne das Feld darf die Moderationsfreigabe nicht löschen
    r = client.put(url, headers=auth_headers, json=_base(tool_channel_ids=["10"]))
    assert r.json()["moderation_channel_ids"] == ["10"]
    r = client.put(url, headers=auth_headers, json=_base(moderation_channel_ids=[]))
    assert r.json()["moderation_channel_ids"] == []


def test_channels_catalog_requires_auth(client):
    assert client.get("/api/communication/discord/channels").status_code == 401


def test_channels_catalog(client, auth_headers, monkeypatch):
    from hydrahive.communication import registry

    def ch(cid, ctype, name, pos, view=True):
        return SimpleNamespace(id=cid, type=ctype, name=name, position=pos, category=None,
                               permissions_for=lambda _m, v=view: perms(view_channel=v))

    guild = SimpleNamespace(id=1, name="FlowKI Club", me=object(), channels=[
        ch(3, discord.ChannelType.forum, "supportforum", 2),
        ch(2, discord.ChannelType.text, "allgemein", 1),
        ch(4, discord.ChannelType.voice, "Sprache", 0),
        ch(5, discord.ChannelType.text, "geheim", 3, view=False),
    ])
    fake_client = SimpleNamespace(guilds=[guild])
    adapter = SimpleNamespace(name="discord", label="Discord",
                              client_for=lambda u: fake_client if u == "testuser" else None)
    monkeypatch.setitem(registry._REGISTRY, "discord", adapter)

    r = client.get("/api/communication/discord/channels", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["connected"] is True
    assert [(c["id"], c["kind"]) for c in body["channels"]] == [("2", "text"), ("3", "forum")]

    monkeypatch.setitem(registry._REGISTRY, "discord",
                        SimpleNamespace(name="discord", label="Discord", client_for=lambda u: None))
    r = client.get("/api/communication/discord/channels", headers=auth_headers)
    assert r.json() == {"connected": False, "channels": []}
