"""Bilder an discord_post / discord_reply (docs/specs/discord-attachments.md).

Sicherheitsrelevant: nur eigener Arbeitsordner, nur echte Bilder (Endung + Inhalt), Schutzliste, Grenzen,
alles vor dem ersten Senden geprüft.
"""
from __future__ import annotations

from pathlib import Path

import discord
import pytest

from tests._discord_fakes import FakeChannel, install, link_thread

FORUM, THREAD = discord.ChannelType.forum, discord.ChannelType.public_thread
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
GIF = b"GIF89a" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 64


def _ctx(ws: Path, username: str = "u"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="", user_id=username, workspace=ws)


def _wr():
    from hydrahive.tools import discord_write
    return discord_write


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "bilder").mkdir(parents=True)
    return ws


def _forum():
    t = discord.ForumTag(name="Anleitung")
    t.id = 1
    return FakeChannel(10, FORUM, "handbuch", tags=[t])


# ── Prüfung (_discord_images) ──────────────────────────────────────────────────

@pytest.mark.parametrize("name,data", [("a.png", PNG), ("b.jpg", JPG), ("c.JPEG", JPG), ("d.gif", GIF), ("e.webp", WEBP)])
def test_erlaubte_bilder_werden_geladen(tmp_path, name, data):
    from hydrahive.tools._discord_images import load_images
    ws = _ws(tmp_path)
    (ws / "bilder" / name).write_bytes(data)
    files = load_images(ws, [f"bilder/{name}"])
    stem, ext = name.rsplit(".", 1)
    assert [(f.filename, f.data) for f in files] == [(f"{stem}.{ext.lower()}", data)]


@pytest.mark.parametrize("bad", ["../draussen.png", "/etc/passwd", "bilder/../../draussen.png"])
def test_pfad_ausserhalb_abgelehnt(tmp_path, bad):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    (tmp_path / "draussen.png").write_bytes(PNG)
    with pytest.raises(ImageError, match="außerhalb"):
        load_images(ws, [bad])


def test_symlink_nach_draussen_abgelehnt(tmp_path):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    (tmp_path / "geheim.png").write_bytes(PNG)
    (ws / "bilder" / "link.png").symlink_to(tmp_path / "geheim.png")
    with pytest.raises(ImageError, match="außerhalb"):
        load_images(ws, ["bilder/link.png"])


def test_falsche_endung_abgelehnt(tmp_path):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    (ws / "notiz.txt").write_bytes(PNG)
    (ws / "bild.pdf").write_bytes(PNG)
    with pytest.raises(ImageError, match="Bildformat"):
        load_images(ws, ["bild.pdf"])
    with pytest.raises(ImageError, match="Bildformat"):
        load_images(ws, ["notiz.txt"])


def test_getarnte_datei_wird_am_inhalt_erkannt(tmp_path):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    (ws / "bilder" / "secrets.png").write_text("GH_TOKEN=ghp_xxx\n")
    with pytest.raises(ImageError, match="kein gültiges"):
        load_images(ws, ["bilder/secrets.png"])


@pytest.mark.parametrize("data", [b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 64, b"\x00" * 80, PNG])
def test_falsches_webp_abgelehnt(tmp_path, data):
    """WebP = RIFF-Container mit Kennung WEBP; RIFF allein (z. B. WAV) reicht nicht."""
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    (ws / "bilder" / "x.webp").write_bytes(data)
    with pytest.raises(ImageError, match="kein gültiges"):
        load_images(ws, ["bilder/x.webp"])


def test_endung_und_inhalt_muessen_zusammenpassen(tmp_path):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    (ws / "bilder" / "x.png").write_bytes(JPG)
    with pytest.raises(ImageError, match="kein gültiges"):
        load_images(ws, ["bilder/x.png"])


@pytest.mark.parametrize("rel", [".ssh/id_rsa.png", "keys/server.key.png", "x/.ssh/a.png", ".git/x.png", ".env.png"])
def test_geschuetzte_orte_abgelehnt_auch_als_bild(tmp_path, rel):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    p = ws / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(PNG)
    with pytest.raises(ImageError, match="geschützt"):
        load_images(ws, [rel])


def test_grenzen(tmp_path, monkeypatch):
    from hydrahive.tools import _discord_images as di
    ws = _ws(tmp_path)
    for i in range(5):
        (ws / "bilder" / f"{i}.png").write_bytes(PNG)
    with pytest.raises(di.ImageError, match="höchstens 4"):
        di.load_images(ws, [f"bilder/{i}.png" for i in range(5)])
    monkeypatch.setattr(di, "MAX_BYTES", 50)
    with pytest.raises(di.ImageError, match="zu groß"):
        di.load_images(ws, ["bilder/0.png"])
    monkeypatch.setattr(di, "MAX_BYTES", 10_000)
    monkeypatch.setattr(di, "MAX_TOTAL", 150)
    with pytest.raises(di.ImageError, match="zusammen"):
        di.load_images(ws, ["bilder/0.png", "bilder/1.png", "bilder/2.png"])


def test_fehlende_und_leere_datei(tmp_path):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    with pytest.raises(ImageError, match="nicht gefunden"):
        load_images(ws, ["bilder/gibtsnicht.png"])
    (ws / "bilder" / "leer.png").write_bytes(b"")
    with pytest.raises(ImageError, match="ist leer"):
        load_images(ws, ["bilder/leer.png"])
    with pytest.raises(ImageError, match="nicht gefunden"):
        load_images(ws, ["bilder"])


def test_dateiname_wird_bereinigt_und_meldung_ohne_absoluten_pfad(tmp_path):
    from hydrahive.tools._discord_images import ImageError, load_images
    ws = _ws(tmp_path)
    (ws / "bilder" / "Mein Bild (1) ä.png").write_bytes(PNG)
    assert load_images(ws, ["bilder/Mein Bild (1) ä.png"])[0].filename == "Mein_Bild__1___.png"
    with pytest.raises(ImageError) as e:
        load_images(ws, ["bilder/fehlt.png"])
    assert str(tmp_path) not in str(e.value)


# ── Werkzeuge ──────────────────────────────────────────────────────────────────

async def test_forum_beitrag_mit_bildern_an_der_eroeffnung(monkeypatch, tmp_path):
    forum = _forum()
    install(monkeypatch, tmp_path / "cfg", [forum], tool_ids=["10"])
    ws = _ws(tmp_path)
    (ws / "bilder" / "a.png").write_bytes(PNG)
    (ws / "bilder" / "b.jpg").write_bytes(JPG)
    res = await _wr()._post({"channel_id": "10", "title": "Auf einen Blick", "text": "Hallo",
                             "tags": ["Anleitung"], "images": ["bilder/a.png", "bilder/b.jpg"]}, _ctx(ws))
    assert res.success, res.error
    files = forum.created_threads[0]["files"]
    assert [f.filename for f in files] == ["a.png", "b.jpg"]
    assert files[0].fp.read() == PNG
    assert "2 Bilder" in res.output


async def test_antwort_mit_bildern_nur_an_der_ersten_nachricht(monkeypatch, tmp_path):
    forum = _forum()
    thread = link_thread(FakeChannel(20, THREAD, "beitrag"), forum)
    install(monkeypatch, tmp_path / "cfg", [forum, thread], tool_ids=["10"])
    ws = _ws(tmp_path)
    (ws / "bilder" / "a.png").write_bytes(PNG)
    long_text = ("Absatz.\n\n" * 400).strip()
    res = await _wr()._reply({"channel_id": "20", "text": long_text, "images": ["bilder/a.png"]}, _ctx(ws))
    assert res.success, res.error
    assert len(thread.sent) >= 2
    assert [f.filename for f in thread.sent[0]["files"]] == ["a.png"]
    assert all("files" not in s for s in thread.sent[1:])


async def test_nur_bilder_ohne_text(monkeypatch, tmp_path):
    forum = _forum()
    thread = link_thread(FakeChannel(20, THREAD, "beitrag"), forum)
    install(monkeypatch, tmp_path / "cfg", [forum, thread], tool_ids=["10"])
    ws = _ws(tmp_path)
    (ws / "bilder" / "a.png").write_bytes(PNG)
    res = await _wr()._reply({"channel_id": "20", "text": "", "images": ["bilder/a.png"]}, _ctx(ws))
    assert res.success, res.error
    assert len(thread.sent) == 1 and thread.sent[0]["files"][0].filename == "a.png"
    assert thread.sent[0]["content"] is None, "ohne Text kein leeres content-Feld senden"


async def test_ungueltiges_bild_sendet_gar_nichts(monkeypatch, tmp_path):
    forum = _forum()
    thread = link_thread(FakeChannel(20, THREAD, "beitrag"), forum)
    install(monkeypatch, tmp_path / "cfg", [forum, thread], tool_ids=["10"])
    ws = _ws(tmp_path)
    (ws / "bilder" / "gut.png").write_bytes(PNG)
    (ws / "bilder" / "boese.png").write_text("kein bild")
    res = await _wr()._reply({"channel_id": "20", "text": "Hallo",
                              "images": ["bilder/gut.png", "bilder/boese.png"]}, _ctx(ws))
    assert not res.success and "boese.png" in res.error
    assert thread.sent == []
    res = await _wr()._post({"channel_id": "10", "title": "T", "text": "x", "tags": ["Anleitung"],
                             "images": ["../x.png"]}, _ctx(ws))
    assert not res.success and forum.created_threads == []


async def test_ohne_bilder_unveraendert(monkeypatch, tmp_path):
    forum = _forum()
    thread = link_thread(FakeChannel(20, THREAD, "beitrag"), forum)
    install(monkeypatch, tmp_path / "cfg", [forum, thread], tool_ids=["10"])
    ws = _ws(tmp_path)
    res = await _wr()._reply({"channel_id": "20", "text": "Hallo"}, _ctx(ws))
    assert res.success and "files" not in thread.sent[0]
    res = await _wr()._reply({"channel_id": "20", "text": ""}, _ctx(ws))
    assert not res.success


def test_schema_beschreibt_bilder():
    w = _wr()
    for t in (w.TOOL_POST, w.TOOL_REPLY):
        assert t.schema["properties"]["images"]["type"] == "array"
        assert "images" not in t.schema["required"]
    assert "images" not in w.TOOL_EDIT.schema["properties"]
