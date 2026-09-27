"""Discord-Agenten-Tools: Posten, Forum-Beitrag, Antworten, Bearbeiten.

Sicherheitsrelevant: keine Massen-Pings, Secret-/Token-Redaction, nur eigene
Nachrichten bearbeiten, moderierte Tags nur mit Berechtigung.
"""
from __future__ import annotations

import discord

from tests._discord_fakes import BOT_ID, FakeChannel, FakeMessage, ctx, install, perms

TEXT, FORUM, THREAD = (discord.ChannelType.text, discord.ChannelType.forum,
                       discord.ChannelType.public_thread)
TOKEN = "MTIzNDU2Nzg5MDEy.bot-token-geheim"


def _wr():
    from hydrahive.tools import discord_write
    return discord_write


def _forum(**kw):
    tags = [discord.ForumTag(name="🐛 Bug"), discord.ForumTag(name="💡 Modulwunsch"),
            discord.ForumTag(name="✅ Gelöst", moderated=True)]
    for i, t in enumerate(tags, start=1):
        t.id = i
    return FakeChannel(10, FORUM, "supportforum", tags=tags, **kw)


async def test_post_in_text_channel_blocks_mass_pings(monkeypatch, tmp_path):
    ch = FakeChannel(1, TEXT, "allgemein")
    install(monkeypatch, tmp_path, [ch], tool_ids=["1"])
    res = await _wr()._post({"channel_id": "1", "text": "@everyone Hallo"}, ctx())
    assert res.success, res.error
    am = ch.sent[0]["allowed_mentions"]
    assert am.everyone is False and am.roles is False and am.replied_user is False


async def test_post_scrubs_bot_token(monkeypatch, tmp_path):
    ch = FakeChannel(1, TEXT)
    install(monkeypatch, tmp_path, [ch], tool_ids=["1"], bot_token=TOKEN)
    res = await _wr()._post({"channel_id": "1", "text": f"Token: {TOKEN}"}, ctx())
    assert res.success
    assert TOKEN not in ch.sent[0]["content"] and "[REDACTED]" in ch.sent[0]["content"]


async def test_long_text_is_split_and_too_long_rejected(monkeypatch, tmp_path):
    ch = FakeChannel(1, TEXT)
    install(monkeypatch, tmp_path, [ch], tool_ids=["1"])
    para = ("x" * 1500 + "\n\n")
    res = await _wr()._post({"channel_id": "1", "text": para * 3}, ctx())
    assert res.success and len(ch.sent) == 3
    assert all(len(s["content"]) <= 2000 for s in ch.sent)
    res = await _wr()._post({"channel_id": "1", "text": "y " * 5000}, ctx())
    assert not res.success and "zu lang" in res.error


async def test_title_rejected_outside_forum(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, [FakeChannel(1, TEXT)], tool_ids=["1"])
    res = await _wr()._post({"channel_id": "1", "text": "a", "title": "T"}, ctx())
    assert not res.success and "nur beim Anlegen" in res.error


async def test_forum_post_with_tags_by_name(monkeypatch, tmp_path):
    forum = _forum()
    install(monkeypatch, tmp_path, [forum], tool_ids=["10"])
    res = await _wr()._post({"channel_id": "10", "title": "Installer hängt", "text": "Details",
                             "tags": ["bug", "💡 Modulwunsch"]}, ctx())
    assert res.success, res.error
    created = forum.created_threads[0]
    assert created["name"] == "Installer hängt" and created["content"] == "Details"
    assert [t.name for t in created["applied_tags"]] == ["🐛 Bug", "💡 Modulwunsch"]
    assert created["allowed_mentions"].everyone is False
    assert "Beitrag-ID" in res.output and "5000" in res.output


async def test_forum_post_requires_title_and_valid_tags(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, [_forum(require_tag=True)], tool_ids=["10"])
    wr = _wr()
    res = await wr._post({"channel_id": "10", "text": "x"}, ctx())
    assert not res.success and "Titel" in res.error
    res = await wr._post({"channel_id": "10", "title": "T", "text": "x", "tags": ["gibtsnicht"]}, ctx())
    assert not res.success and "unbekannt" in res.error and "🐛 Bug" in res.error
    res = await wr._post({"channel_id": "10", "title": "T", "text": "x"}, ctx())
    assert not res.success and "mindestens einen Tag" in res.error
    res = await wr._post({"channel_id": "10", "title": "T" * 101, "text": "x", "tags": ["Bug"]}, ctx())
    assert not res.success and "Titel zu lang" in res.error


async def test_moderated_tag_needs_manage_threads(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, [_forum()], tool_ids=["10"])
    res = await _wr()._post({"channel_id": "10", "title": "T", "text": "x",
                             "tags": ["Gelöst"]}, ctx())
    assert not res.success and "Moderatoren" in res.error
    install(monkeypatch, tmp_path, [_forum(permissions=perms(manage_threads=True))], tool_ids=["10"])
    res = await _wr()._post({"channel_id": "10", "title": "T", "text": "x",
                             "tags": ["Gelöst"]}, ctx())
    assert res.success, res.error


async def test_reply_in_thread_with_reference(monkeypatch, tmp_path):
    thread = FakeChannel(77, THREAD, "Frage", parent_id=10, messages=[FakeMessage(78, "Hilfe?")])
    install(monkeypatch, tmp_path, [_forum(), thread], tool_ids=["10"])
    res = await _wr()._reply({"channel_id": "77", "text": "Lösung", "reply_to": "78"}, ctx())
    assert res.success, res.error
    sent = thread.sent[0]
    assert sent["content"] == "Lösung" and sent["reference"].id == 78
    assert sent["mention_author"] is False


async def test_reply_to_forum_itself_or_locked_thread_fails(monkeypatch, tmp_path):
    locked = FakeChannel(77, THREAD, "zu", parent_id=10, locked=True)
    install(monkeypatch, tmp_path, [_forum(), locked], tool_ids=["10"])
    res = await _wr()._reply({"channel_id": "10", "text": "x"}, ctx())
    assert not res.success and "Forum selbst" in res.error
    res = await _wr()._reply({"channel_id": "77", "text": "x"}, ctx())
    assert not res.success and "gesperrt" in res.error


async def test_edit_only_own_messages(monkeypatch, tmp_path):
    own = FakeMessage(50, "alt", author_id=BOT_ID, bot=True)
    foreign = FakeMessage(51, "fremd", author_id=1)
    thread = FakeChannel(77, THREAD, "Frage", parent_id=10, messages=[own, foreign])
    install(monkeypatch, tmp_path, [_forum(), thread], tool_ids=["10"])
    wr = _wr()
    res = await wr._edit({"channel_id": "77", "message_id": "51", "text": "neu"}, ctx())
    assert not res.success and "keine Nachricht des Bots" in res.error
    assert foreign.edits == []
    res = await wr._edit({"channel_id": "77", "message_id": "50", "text": "neu"}, ctx())
    assert res.success, res.error
    assert own.edits[0]["content"] == "neu"
    assert own.edits[0]["allowed_mentions"].everyone is False
    res = await wr._edit({"channel_id": "77", "message_id": "50", "text": "z" * 2001}, ctx())
    assert not res.success and "zu lang" in res.error


async def test_missing_send_permission(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, [FakeChannel(1, TEXT, permissions=perms(send_messages=False))],
            tool_ids=["1"])
    res = await _wr()._post({"channel_id": "1", "text": "x"}, ctx())
    assert not res.success and "Berechtigung" in res.error
