"""Discord-Moderation: Tag-Liste eines Forums pflegen (discord_forum_tags)."""
from __future__ import annotations

import discord

from tests._discord_fakes import FakeChannel, ctx, install, perms

FORUM, TEXT = discord.ChannelType.forum, discord.ChannelType.text
MOD = perms(manage_channels=True)


def _mod():
    from hydrahive.tools import discord_moderate
    return discord_moderate


def _forum(p=MOD, n_extra: int = 0):
    tags = [discord.ForumTag(name="🐛 Bug"), discord.ForumTag(name="✅ Gelöst", moderated=True)]
    tags += [discord.ForumTag(name=f"T{i}") for i in range(n_extra)]
    for i, t in enumerate(tags, start=1):
        t.id = i
    return FakeChannel(10, FORUM, "supportforum", tags=tags, permissions=p)


def _names(forum):
    return [t.name for t in forum.available_tags]


async def test_tag_anlegen_mit_emoji_und_moderiert(monkeypatch, tmp_path):
    forum = _forum()
    install(monkeypatch, tmp_path, [forum], tool_ids=["10"], mod_ids=["10"])
    res = await _mod()._forum_tags({"forum_id": "10", "action": "create", "name": "Frage",
                                    "emoji": "❓", "moderated": False}, ctx())
    assert res.success, res.error
    new = forum.available_tags[-1]
    assert new.name == "Frage" and str(new.emoji) == "❓" and new.moderated is False
    assert forum.edit_calls[0]["reason"].startswith("HydraHive-Agent:")


async def test_doppelter_tag_abgelehnt(monkeypatch, tmp_path):
    forum = _forum()
    install(monkeypatch, tmp_path, [forum], tool_ids=["10"], mod_ids=["10"])
    res = await _mod()._forum_tags({"forum_id": "10", "action": "create", "name": "bug"}, ctx())
    assert not res.success and "gibt es schon" in res.error and forum.edit_calls == []


async def test_tag_umbenennen_behaelt_id(monkeypatch, tmp_path):
    forum = _forum()
    install(monkeypatch, tmp_path, [forum], tool_ids=["10"], mod_ids=["10"])
    res = await _mod()._forum_tags({"forum_id": "10", "action": "update", "name": "Bug",
                                    "new_name": "Fehler"}, ctx())
    assert res.success, res.error
    assert _names(forum) == ["Fehler", "✅ Gelöst"] and forum.available_tags[0].id == 1


async def test_tag_entfernen(monkeypatch, tmp_path):
    forum = _forum()
    install(monkeypatch, tmp_path, [forum], tool_ids=["10"], mod_ids=["10"])
    res = await _mod()._forum_tags({"forum_id": "10", "action": "delete", "name": "gelöst"}, ctx())
    assert res.success and _names(forum) == ["🐛 Bug"]


async def test_limit_20_tags(monkeypatch, tmp_path):
    forum = _forum(n_extra=18)
    install(monkeypatch, tmp_path, [forum], tool_ids=["10"], mod_ids=["10"])
    res = await _mod()._forum_tags({"forum_id": "10", "action": "create", "name": "Neu"}, ctx())
    assert not res.success and "höchstens 20" in res.error


async def test_ohne_recht_kanaele_verwalten(monkeypatch, tmp_path):
    forum = _forum(p=perms())
    install(monkeypatch, tmp_path, [forum], tool_ids=["10"], mod_ids=["10"])
    res = await _mod()._forum_tags({"forum_id": "10", "action": "create", "name": "X"}, ctx())
    assert not res.success and "Kanäle verwalten" in res.error


async def test_nur_in_foren(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, [FakeChannel(1, TEXT, permissions=MOD)], tool_ids=["1"],
            mod_ids=["1"])
    res = await _mod()._forum_tags({"forum_id": "1", "action": "create", "name": "X"}, ctx())
    assert not res.success and "nur in Foren" in res.error


async def test_unbekannte_aktion(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, [_forum()], tool_ids=["10"], mod_ids=["10"])
    res = await _mod()._forum_tags({"forum_id": "10", "action": "purge"}, ctx())
    assert not res.success and "Unbekannte Aktion" in res.error
