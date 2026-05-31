"""Geteilte OpenRouter-Media-Helfer (Key-Lookup + base64→Datei)."""
from __future__ import annotations

from unittest.mock import patch


def test_save_bytes_schreibt_datei_mit_endung(tmp_path):
    from hydrahive.tools._openrouter_media import save_bytes
    path = save_bytes(b"\x00\x01\x02", tmp_path / "sub", "mp3")
    assert path.exists()
    assert path.suffix == ".mp3"
    assert path.parent == tmp_path / "sub"
    assert path.read_bytes() == b"\x00\x01\x02"


def test_save_bytes_eindeutige_namen(tmp_path):
    from hydrahive.tools._openrouter_media import save_bytes
    a = save_bytes(b"x", tmp_path, "png")
    b = save_bytes(b"y", tmp_path, "png")
    assert a != b


def test_save_bytes_strippt_punkt_in_endung(tmp_path):
    from hydrahive.tools._openrouter_media import save_bytes
    path = save_bytes(b"x", tmp_path, ".wav")
    assert path.suffix == ".wav"
    assert ".." not in path.name


def test_openrouter_key_liest_aus_config():
    from hydrahive.tools import _openrouter_media
    with patch("hydrahive.llm._config.load_config", return_value={
        "providers": [{"id": "openrouter", "api_key": "sk-or-v1-abc"}]
    }):
        assert _openrouter_media.openrouter_key() == "sk-or-v1-abc"


def test_openrouter_key_leer_wenn_nicht_konfiguriert():
    from hydrahive.tools import _openrouter_media
    with patch("hydrahive.llm._config.load_config", return_value={"providers": []}):
        assert _openrouter_media.openrouter_key() == ""
