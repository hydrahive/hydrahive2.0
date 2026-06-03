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


# ---------------------------------------------------------------------------
# matrix_server_name — File-Fallback (Part A)
# ---------------------------------------------------------------------------

def test_matrix_server_name_file_fallback(monkeypatch, tmp_path):
    """Wenn env leer und Datei vorhanden → Datei-Inhalt wird zurückgegeben."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MATRIX_SERVER_NAME", raising=False)

    server_name_file = tmp_path / "matrix" / "server_name"
    server_name_file.parent.mkdir(parents=True, exist_ok=True)
    server_name_file.write_text("masternode.hydrahive.org\n")

    from hydrahive.settings import settings
    assert settings.matrix_server_name == "masternode.hydrahive.org"


def test_matrix_server_name_env_gewinnt_vor_datei(monkeypatch, tmp_path):
    """Wenn env gesetzt → env-Wert gewinnt, Datei wird ignoriert."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "env-server.example.org")

    server_name_file = tmp_path / "matrix" / "server_name"
    server_name_file.parent.mkdir(parents=True, exist_ok=True)
    server_name_file.write_text("file-server.example.org\n")

    from hydrahive.settings import settings
    assert settings.matrix_server_name == "env-server.example.org"


def test_matrix_server_name_datei_fehlt_gibt_leer(monkeypatch, tmp_path):
    """Wenn env leer und Datei fehlt → leerer String."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MATRIX_SERVER_NAME", raising=False)

    from hydrahive.settings import settings
    assert settings.matrix_server_name == ""


def test_matrix_server_name_datei_leer_gibt_leer(monkeypatch, tmp_path):
    """Wenn env leer und Datei vorhanden aber leer → leerer String."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MATRIX_SERVER_NAME", raising=False)

    server_name_file = tmp_path / "matrix" / "server_name"
    server_name_file.parent.mkdir(parents=True, exist_ok=True)
    server_name_file.write_text("   \n")

    from hydrahive.settings import settings
    assert settings.matrix_server_name == ""


# ---------------------------------------------------------------------------
# matrix_registration_token — File-Fallback (gleiche Quelle wie der Installer)
# ---------------------------------------------------------------------------

def test_matrix_registration_token_file_fallback(monkeypatch, tmp_path):
    """Wenn env leer und Datei vorhanden → Token aus der Installer-Datei."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MATRIX_REGISTRATION_TOKEN", raising=False)

    token_file = tmp_path / "matrix" / "registration_token"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text("deadbeef0123\n")

    from hydrahive.settings import settings
    assert settings.matrix_registration_token == "deadbeef0123"


def test_matrix_registration_token_env_gewinnt_vor_datei(monkeypatch, tmp_path):
    """Wenn env gesetzt → env-Wert gewinnt, Datei wird ignoriert."""
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "env-token")

    token_file = tmp_path / "matrix" / "registration_token"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text("file-token\n")

    from hydrahive.settings import settings
    assert settings.matrix_registration_token == "env-token"
