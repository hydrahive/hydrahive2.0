"""Discord-Moderations-Tools: Freigabe, Rechte, Beitrag verwalten, anpinnen, löschen.

Sicherheitsrelevant: Moderation nur in doppelt freigegebenen Kanälen (fail-closed),
fehlende Discord-Rechte werden benannt, gelöschter Inhalt wird nie zurückgegeben,
Aktionen tragen einen Audit-Log-Grund.
"""
from __future__ import annotations

import discord

from tests._discord_fakes import (
    BOT_ID, FakeChannel, FakeMessage, ctx, install, link_thread, perms,
)

TEXT, FORUM, THREAD = (discord.ChannelType.text, discord.ChannelType.forum,
                       discord.ChannelType.public_thread)
MOD = perms(manage_threads=True, manage_messages=True, pin_messages=True, manage_channels=True)


def _mod():
    from hydrahive.tools import discord_moderate
    return discord_moderate


def _tags():
    tags = [discord.ForumTag(name="🐛 Bug"), discord.ForumTag(name="❓ Frage"),
            discord.ForumTag(name="✅ Gelöst", moderated=True)]
    for i, t in enumerate(tags, start=1):
        t.id = i
    return tags


def _setup(monkeypatch, tmp_path, *, mod_ids=("10",), tool_ids=("10",), p=MOD, messages=None,
           archived=False, require_tag=False):
    forum = FakeChannel(10, FORUM, "supportforum", tags=_tags(), permissions=p,
                        require_tag=require_tag)
    thread = link_thread(FakeChannel(20, THREAD, "Frage zu X", permissions=p,
                                     messages=messages or []), forum)
    thread.applied_tags = [forum.available_tags[1]]
    thread.archived = archived
    install(monkeypatch, tmp_path, [forum, thread], tool_ids=list(tool_ids), mod_ids=list(mod_ids))
    return forum, thread


async def test_ohne_moderationsfreigabe_abgelehnt(monkeypatch, tmp_path):
    _, thread = _setup(monkeypatch, tmp_path, mod_ids=())
    res = await _mod()._thread({"post_id": "20", "archived": True}, ctx())
    assert not res.success and "nicht für Moderation freigegeben" in res.error
    assert thread.edit_calls == []


async def test_moderation_ohne_werkzeugfreigabe_wirkt_nicht(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, mod_ids=("10",), tool_ids=("99",))
    res = await _mod()._thread({"post_id": "20", "locked": True}, ctx())
    assert not res.success and "für Agenten-Werkzeuge nicht freigegeben" in res.error


async def test_geloest_tag_ergaenzen_und_schliessen(monkeypatch, tmp_path):
    _, thread = _setup(monkeypatch, tmp_path)
    res = await _mod()._thread({"post_id": "20", "add_tags": ["gelöst"], "archived": True}, ctx())
    assert res.success, res.error
    assert [t.name for t in thread.applied_tags] == ["❓ Frage", "✅ Gelöst"]
    assert thread.archived is True
    assert all(c["reason"].startswith("HydraHive-Agent:") for c in thread.edit_calls)


async def test_tags_ersetzen_und_entfernen(monkeypatch, tmp_path):
    _, thread = _setup(monkeypatch, tmp_path)
    res = await _mod()._thread({"post_id": "20", "set_tags": ["Bug", "Frage"],
                                "remove_tags": ["frage"]}, ctx())
    assert res.success, res.error
    assert [t.name for t in thread.applied_tags] == ["🐛 Bug"]


async def test_pflicht_tag_verhindert_leere_tagliste(monkeypatch, tmp_path):
    _, thread = _setup(monkeypatch, tmp_path, require_tag=True)
    res = await _mod()._thread({"post_id": "20", "set_tags": []}, ctx())
    assert not res.success and "mindestens einen Tag" in res.error


async def test_geschlossener_beitrag_wird_fuer_aenderung_geoeffnet_und_wieder_geschlossen(
        monkeypatch, tmp_path):
    _, thread = _setup(monkeypatch, tmp_path, archived=True)
    res = await _mod()._thread({"post_id": "20", "locked": True}, ctx())
    assert res.success, res.error
    assert [c.get("archived") for c in thread.edit_calls] == [False, None, True]
    assert thread.locked is True and thread.archived is True


async def test_titel_wird_geschwaerzt_und_laenge_geprueft(monkeypatch, tmp_path):
    token = "MTIzNDU2Nzg5MDEy.bot-token-geheim"
    forum, thread = _setup(monkeypatch, tmp_path)
    install(monkeypatch, tmp_path, [forum, thread], tool_ids=["10"], mod_ids=["10"],
            bot_token=token)
    res = await _mod()._thread({"post_id": "20", "title": f"Key {token}"}, ctx())
    assert res.success and token not in thread.name
    res = await _mod()._thread({"post_id": "20", "title": "x" * 101}, ctx())
    assert not res.success and "1–100" in res.error


async def test_fehlendes_recht_wird_benannt(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, p=perms())
    res = await _mod()._thread({"post_id": "20", "locked": True}, ctx())
    assert not res.success and "Threads verwalten" in res.error


async def test_nichts_zu_aendern(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    res = await _mod()._thread({"post_id": "20"}, ctx())
    assert not res.success and "Nichts zu ändern" in res.error


async def test_forum_statt_beitrag_abgelehnt(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    res = await _mod()._thread({"post_id": "10", "locked": True}, ctx())
    assert not res.success and "kein Forum-Beitrag" in res.error


async def test_nachricht_anpinnen_und_loesen(monkeypatch, tmp_path):
    msg = FakeMessage(21, "Lösung: Neustart hilft")
    _setup(monkeypatch, tmp_path, messages=[msg])
    assert (await _mod()._pin({"channel_id": "20", "message_id": "21"}, ctx())).success
    assert msg.pinned is True
    assert (await _mod()._pin({"channel_id": "20", "message_id": "21", "pin": False}, ctx())).success
    assert msg.pinned is False


async def test_anpinnen_ohne_recht(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, p=perms(manage_threads=True), messages=[FakeMessage(21, "x")])
    res = await _mod()._pin({"channel_id": "20", "message_id": "21"}, ctx())
    assert not res.success and "Nachrichten anpinnen" in res.error


async def test_fremde_nachricht_loeschen_gibt_inhalt_nicht_zurueck(monkeypatch, tmp_path):
    secret = "sk-geheimer-api-key-123"
    msg = FakeMessage(21, f"mein key ist {secret}", author_id=5, name="Alex")
    _setup(monkeypatch, tmp_path, messages=[msg])
    res = await _mod()._delete({"channel_id": "20", "message_id": "21"}, ctx())
    assert res.success, res.error
    assert msg.deleted is True
    assert secret not in res.output and "Alex" in res.output


async def test_fremde_nachricht_ohne_recht_nicht_loeschbar(monkeypatch, tmp_path):
    msg = FakeMessage(21, "hallo", author_id=5)
    _setup(monkeypatch, tmp_path, p=perms(manage_threads=True), messages=[msg])
    res = await _mod()._delete({"channel_id": "20", "message_id": "21"}, ctx())
    assert not res.success and "Nachrichten verwalten" in res.error and msg.deleted is False


async def test_eigene_nachricht_ohne_recht_loeschbar(monkeypatch, tmp_path):
    msg = FakeMessage(21, "vom Bot", author_id=BOT_ID, bot=True)
    _setup(monkeypatch, tmp_path, p=perms(), messages=[msg])
    res = await _mod()._delete({"channel_id": "20", "message_id": "21"}, ctx())
    assert res.success and msg.deleted is True


async def test_ganzen_beitrag_loeschen(monkeypatch, tmp_path):
    _, thread = _setup(monkeypatch, tmp_path)
    res = await _mod()._delete({"channel_id": "20"}, ctx())
    assert res.success, res.error
    assert thread.deleted_with and thread.deleted_with.startswith("HydraHive-Agent:")


async def test_forum_selbst_wird_nie_geloescht(monkeypatch, tmp_path):
    forum, _ = _setup(monkeypatch, tmp_path)
    res = await _mod()._delete({"channel_id": "10"}, ctx())
    assert not res.success and forum.deleted_with is None


def test_loeschen_verlangt_immer_bestaetigung():
    from hydrahive.runner._runner_tools import ALWAYS_CONFIRM
    assert "discord_delete" in ALWAYS_CONFIRM
