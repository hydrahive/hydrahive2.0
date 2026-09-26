"""Lokale Sprach-Modelle (Whisper, Piper) als wählbare Standard-Modelle.

Hintergrund (26.09.2026): Die Standard-Auswahl für Sprachausgabe und
Spracherkennung bot nur OpenRouter an. Die lokalen Dienste (Whisper auf der
GPU im STT-Container, Piper im TTS-Container) liefen, waren aber weder
auswählbar noch von den Agent-Tools nutzbar. transcribe_audio und
generate_speech verlangten immer einen OpenRouter-Key.

Lokale Modelle bekommen feste IDs mit Präfix `local/`. Die Tools erkennen das
Präfix und nutzen dann den lokalen Dienst statt OpenRouter.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.llm import local_voice
from hydrahive.tools import generate_speech, transcribe_audio
from hydrahive.tools.base import ToolContext


def _ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=tmp_path)


# --- Liste --------------------------------------------------------------------

def test_local_ids_are_stable_and_prefixed():
    assert local_voice.LOCAL_STT_ID == "local/whisper"
    assert local_voice.LOCAL_TTS_ID == "local/piper"
    assert local_voice.is_local("local/whisper")
    assert not local_voice.is_local("openai/whisper-1")
    assert not local_voice.is_local("")


@pytest.mark.asyncio
async def test_local_models_listed_only_when_service_reachable(monkeypatch):
    monkeypatch.setattr(local_voice, "_reachable", lambda host, port: port == local_voice.STT_PORT)

    stt = await local_voice.list_local("stt")
    tts = await local_voice.list_local("tts")

    assert [m["id"] for m in stt] == ["local/whisper"]
    assert tts == []  # Piper nicht erreichbar -> nicht anbieten


@pytest.mark.asyncio
async def test_registry_contains_local_models(monkeypatch):
    from hydrahive.llm import registry

    async def fake_local(purpose):
        return [{"id": f"local/{purpose}", "name": purpose}]

    monkeypatch.setattr(local_voice, "list_local", fake_local)
    monkeypatch.setattr(registry, "catalog_for_providers", _empty_catalog)
    monkeypatch.setattr(registry, "list_speech_models", _empty)
    monkeypatch.setattr(registry, "list_transcribe_models", _empty)
    monkeypatch.setattr(registry, "list_video_models", _empty)
    registry.invalidate()

    stt = await registry.list_models("stt")
    tts = await registry.list_models("tts")
    registry.invalidate()

    assert any(m.id == "local/stt" and m.provider == "local" for m in stt)
    assert any(m.id == "local/tts" and m.provider == "local" for m in tts)


@pytest.mark.asyncio
async def test_media_entry_shows_openrouter_even_if_chat_catalog_has_same_id(monkeypatch):
    """openai/whisper-1 steht im OpenAI-Chat-Katalog UND in der OpenRouter-STT-
    Liste. Das Tool schickt STT immer an OpenRouter — die Auswahl darf es
    daher nicht unter "OpenAI" anzeigen, und Whisper ist kein Chat-Modell."""
    from hydrahive.llm import registry

    async def fake_catalog(providers):
        return [{"provider_id": "openai", "live_count": 1,
                 "models": [{"id": "openai/whisper-1"}, {"id": "openai/gpt-5"}]}]

    async def fake_stt(force=False):
        return [{"id": "openai/whisper-1", "name": "Whisper v1"}]

    async def no_local(purpose):
        return []

    monkeypatch.setattr(registry, "catalog_for_providers", fake_catalog)
    monkeypatch.setattr(registry, "list_speech_models", _empty)
    monkeypatch.setattr(registry, "list_transcribe_models", fake_stt)
    monkeypatch.setattr(registry, "list_video_models", _empty)
    monkeypatch.setattr(local_voice, "list_local", no_local)
    registry.invalidate()

    stt = {m.id: m for m in await registry.list_models("stt")}
    chat_ids = {m.id for m in await registry.list_models("chat")}
    registry.invalidate()

    assert stt["openai/whisper-1"].provider == "openrouter"
    assert "openai/whisper-1" not in chat_ids
    assert "openai/gpt-5" in chat_ids


async def _empty(force=False):
    return []


async def _empty_catalog(providers):
    return []


# --- transcribe_audio ---------------------------------------------------------

@pytest.mark.asyncio
async def test_transcribe_audio_uses_local_whisper_without_openrouter_key(tmp_path, monkeypatch):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF....fake")
    seen = {}

    async def fake_local(data, mime="audio/ogg", language=None):
        seen["mime"], seen["language"] = mime, language
        return "Hallo Welt"

    monkeypatch.setattr(transcribe_audio, "transcribe_bytes", fake_local)
    monkeypatch.setattr(transcribe_audio, "openrouter_key", lambda: "")
    monkeypatch.setattr(transcribe_audio, "get_media_model", lambda cat, config=None: "local/whisper")

    res = await transcribe_audio.TOOL.execute({"file": str(audio), "language": "de"}, _ctx(tmp_path))

    assert res.success, res.error
    assert res.output == "Hallo Welt"
    # mimetypes meldet für .wav je nach System audio/wav oder audio/x-wav;
    # voice.stt kennt beide.
    assert seen["mime"] in ("audio/wav", "audio/x-wav")
    assert seen["language"] == "de"


@pytest.mark.asyncio
async def test_transcribe_audio_cloud_still_needs_key(tmp_path, monkeypatch):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF....fake")
    monkeypatch.setattr(transcribe_audio, "openrouter_key", lambda: "")
    monkeypatch.setattr(transcribe_audio, "get_media_model", lambda cat, config=None: "openai/whisper-1")

    res = await transcribe_audio.TOOL.execute({"file": str(audio)}, _ctx(tmp_path))

    assert not res.success
    assert "OpenRouter" in res.error


# --- Vorlesen im Chat (Variante "openrouter") ----------------------------------

@pytest.mark.asyncio
async def test_chat_openrouter_tts_with_local_default_goes_to_piper(monkeypatch):
    """Steht der Standard auf local/piper, darf nichts zu OpenRouter gehen."""
    from hydrahive.voice import tts as voice_tts

    async def fake_piper(text, voice=""):
        return b"wav", "audio/wav"

    async def cloud_must_not_run(*a, **k):
        raise AssertionError("OpenRouter darf bei local/piper nicht aufgerufen werden")

    monkeypatch.setattr(voice_tts, "synthesize_local", fake_piper)
    monkeypatch.setattr("hydrahive.llm.media_models.get_media_model", lambda cat, config=None: "local/piper")
    monkeypatch.setattr("hydrahive.tools._openrouter_media.synthesize_speech", cloud_must_not_run)
    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "")

    data, mime = await voice_tts.synthesize_openrouter("Hallo")

    assert (data, mime) == (b"wav", "audio/wav")


# --- generate_speech ----------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_speech_uses_local_piper_without_openrouter_key(tmp_path, monkeypatch):
    async def fake_piper(text, voice=""):
        return b"RIFF-wav-bytes", "audio/wav"

    monkeypatch.setattr(generate_speech, "synthesize_local", fake_piper)
    monkeypatch.setattr(generate_speech, "openrouter_key", lambda: "")
    monkeypatch.setattr(generate_speech, "get_media_model", lambda cat, config=None: "local/piper")

    res = await generate_speech.TOOL.execute({"text": "Guten Tag"}, _ctx(tmp_path))

    assert res.success, res.error
    files = list((tmp_path / "generated").glob("*.wav"))
    assert len(files) == 1 and files[0].read_bytes() == b"RIFF-wav-bytes"


@pytest.mark.asyncio
async def test_generate_speech_explicit_local_model_argument(tmp_path, monkeypatch):
    """Auch ein Agent, der model='local/piper' übergibt, landet bei Piper."""
    called = {}

    async def fake_piper(text, voice=""):
        called["text"] = text
        return b"x", "audio/wav"

    monkeypatch.setattr(generate_speech, "synthesize_local", fake_piper)
    monkeypatch.setattr(generate_speech, "openrouter_key", lambda: "sk-cloud")
    monkeypatch.setattr(generate_speech, "get_media_model", lambda cat, config=None: "hexgrad/kokoro-82m")

    res = await generate_speech.TOOL.execute({"text": "Test", "model": "local/piper"}, _ctx(tmp_path))

    assert res.success and called == {"text": "Test"}
