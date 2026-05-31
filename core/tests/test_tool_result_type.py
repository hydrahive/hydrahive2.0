"""#146 Tool-Result-Format für Media.

ToolResult bekommt result_type-Feld. to_tool_result_block liefert media-Liste
mit url-Eintrag wenn result_type != 'text' — damit Frontend ohne lokale Datei
Bilder/Audio/Video rendern kann.
"""
from __future__ import annotations

from hydrahive.tools.base import ToolResult


def test_tool_result_type_default_ist_text():
    r = ToolResult(success=True, output="hallo")
    assert r.result_type == "text"


def test_tool_result_ok_erbt_default():
    r = ToolResult.ok("hallo")
    assert r.result_type == "text"


def test_tool_result_image_url():
    r = ToolResult.ok("https://example.com/img.png", result_type="image_url")
    assert r.result_type == "image_url"


def test_tool_result_audio_url():
    r = ToolResult.ok("https://example.com/audio.mp3", result_type="audio_url")
    assert r.result_type == "audio_url"


def test_tool_result_video_url():
    r = ToolResult.ok("https://example.com/video.mp4", result_type="video_url")
    assert r.result_type == "video_url"


def test_to_tool_result_block_image_url_setzt_media():
    from hydrahive.runner.dispatcher import to_tool_result_block

    r = ToolResult.ok("https://openrouter.ai/generated/abc.png", result_type="image_url")
    block = to_tool_result_block("tool-id-1", r)
    assert "media" in block
    media = block["media"]
    assert len(media) == 1
    assert media[0]["kind"] == "image"
    assert media[0]["url"] == "https://openrouter.ai/generated/abc.png"


def test_to_tool_result_block_audio_url_setzt_media():
    from hydrahive.runner.dispatcher import to_tool_result_block

    r = ToolResult.ok("https://tts.example.com/speech.mp3", result_type="audio_url")
    block = to_tool_result_block("tool-id-2", r)
    media = block["media"]
    assert media[0]["kind"] == "audio"
    assert media[0]["url"] == "https://tts.example.com/speech.mp3"


def test_to_tool_result_block_text_kein_media_change():
    from hydrahive.runner.dispatcher import to_tool_result_block

    r = ToolResult.ok("normaler Text ohne Media")
    block = to_tool_result_block("tool-id-3", r)
    assert block.get("media", []) == []
