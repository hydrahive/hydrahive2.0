"""Settings-Mixin für Teamchat / Matrix.

Lazy-Imports in jeder Testfunktion (settings.data_dir-Freeze-Gotcha).
"""
from __future__ import annotations


def test_teamchat_enabled_default_false(monkeypatch, tmp_path):
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_TEAMCHAT_ENABLED", raising=False)
    from hydrahive.settings import settings

    assert settings.teamchat_enabled is False


def test_teamchat_enabled_true_wenn_env_1(monkeypatch, tmp_path):
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("HH_TEAMCHAT_ENABLED", "1")
    from hydrahive.settings import settings

    assert settings.teamchat_enabled is True


def test_matrix_homeserver_url_default(monkeypatch, tmp_path):
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MATRIX_HOMESERVER_URL", raising=False)
    from hydrahive.settings import settings

    assert settings.matrix_homeserver_url == "http://127.0.0.1:6167"


def test_matrix_server_name_default_leer(monkeypatch, tmp_path):
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MATRIX_SERVER_NAME", raising=False)
    from hydrahive.settings import settings

    assert settings.matrix_server_name == ""


def test_matrix_registration_token_default_leer(monkeypatch, tmp_path):
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MATRIX_REGISTRATION_TOKEN", raising=False)
    from hydrahive.settings import settings

    assert settings.matrix_registration_token == ""
