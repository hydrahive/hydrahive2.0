"""Tests für get_default / set_default in llm._config (Task 4 LLM-SSOT)."""
import json


def _setup(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.llm import _config
    p = tmp_path / "llm.json"
    p.write_text(json.dumps({"providers": [], "default_model": "claude-x",
                             "embed_model": "bge", "media_models": {"tts": "kokoro"}}))
    monkeypatch.setattr(settings, "llm_config", p, raising=False)
    _config._config_cache = None
    return _config, p


def test_get_default_maps_keys(tmp_path, monkeypatch):
    _config, _ = _setup(tmp_path, monkeypatch)
    assert _config.get_default("chat") == "claude-x"
    assert _config.get_default("embed") == "bge"
    assert _config.get_default("tts") == "kokoro"
    assert _config.get_default("stt") == ""       # nicht gesetzt


def test_set_default_writes_correct_key(tmp_path, monkeypatch):
    _config, p = _setup(tmp_path, monkeypatch)
    _config.set_default("stt", "openai/whisper-large-v3")
    _config.set_default("chat", "openrouter/new")
    data = json.loads(p.read_text())
    assert data["media_models"]["transcribe"] == "openai/whisper-large-v3"  # stt→transcribe
    assert data["default_model"] == "openrouter/new"
    _config._config_cache = None
    assert _config.get_default("stt") == "openai/whisper-large-v3"
