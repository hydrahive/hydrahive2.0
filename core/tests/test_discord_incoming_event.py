"""Eingehende Discord-Nachricht → IncomingEvent (MED-3).

- Server-Kanal: eigene Session je Autor (vorher teilten sich alle Nutzer eines
  Kanals Verlauf und Kontext des Bots).
- is_group für Server-Kanäle, is_owner für eingetragene Besitzer-IDs
  (vorher war jede Nachricht "Einzel-Chat — unbekannter Kontakt").
"""
from __future__ import annotations

from hydrahive.communication.discord.config import DiscordConfig
from hydrahive.communication.discord.event import build_event


def _event(*, author="111", channel="500", is_dm=False, owners=None, guild="9"):
    cfg = DiscordConfig(owner_user_ids=list(owners or []))
    return build_event(cfg=cfg, username="u", author_id=author, author_name="Alex",
                       channel_id=channel, guild_id=None if is_dm else guild,
                       is_dm=is_dm, text="hallo")


def test_server_kanal_session_je_autor():
    a = _event(author="111")
    b = _event(author="222")
    assert a.external_user_id != b.external_user_id
    assert a.external_user_id == "500:111"


def test_dm_bleibt_beim_dm_kanal():
    ev = _event(is_dm=True, channel="700")
    assert ev.external_user_id == "700"
    assert ev.metadata["is_group"] is False


def test_server_kanal_ist_gruppe():
    assert _event().metadata["is_group"] is True


def test_besitzer_wird_erkannt():
    assert _event(author="111", owners=["111"]).metadata["is_owner"] is True
    assert _event(author="222", owners=["111"]).metadata["is_owner"] is False
    assert _event(author="111").metadata["is_owner"] is False


def test_metadaten_bleiben_erhalten():
    ev = _event()
    assert ev.channel == "discord" and ev.target_username == "u" and ev.text == "hallo"
    assert ev.sender_name == "Alex"
    assert ev.metadata["author_id"] == "111" and ev.metadata["guild_id"] == "9"
    assert ev.metadata["channel_id"] == "500"


def test_owner_ids_config_roundtrip(tmp_path, monkeypatch):
    from hydrahive.communication.discord import config as dc
    from hydrahive.settings import settings
    monkeypatch.setitem(settings.__dict__, "discord_config_dir", tmp_path)
    dc.save("u", DiscordConfig(owner_user_ids=[" 111 ", "111", "", "222"]))
    assert dc.load("u").owner_user_ids == ["111", "222"]


def test_besitzer_umgeht_user_allowlist_nicht_die_blockliste():
    from hydrahive.communication.discord.filter import evaluate
    cfg = DiscordConfig(owner_user_ids=["111"], allowed_user_ids=["333"])
    assert evaluate(cfg=cfg, author_id="111", is_dm=False, channel_id="1", text="x").accepted
    cfg = DiscordConfig(owner_user_ids=["111"], blocked_user_ids=["111"])
    assert not evaluate(cfg=cfg, author_id="111", is_dm=False, channel_id="1", text="x").accepted


def test_owner_ids_ueber_api_und_erhalten_wenn_key_fehlt(client, auth_headers, tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setitem(settings.__dict__, "discord_config_dir", tmp_path)
    url = "/api/communication/discord/config"
    base = {"bot_token": "", "dm_enabled": True, "mention_enabled": True, "require_keyword": "",
            "allowed_user_ids": [], "blocked_user_ids": [], "allowed_channel_ids": [],
            "respond_as_voice": False, "voice_name": "German_FriendlyMan"}
    r = client.put(url, headers=auth_headers, json={**base, "owner_user_ids": ["111"]})
    assert r.status_code == 200 and r.json()["owner_user_ids"] == ["111"]
    r = client.put(url, headers=auth_headers, json=base)   # älteres Frontend ohne Key
    assert r.json()["owner_user_ids"] == ["111"]
