"""GUI-editierbare Settings: Override-Store + Resolver (override → env → default).

Kern-Invariante: ohne Override verhält sich resolve identisch zu os.environ.get
(env_var, default) → null Regression für bestehende Deployments.
"""
from __future__ import annotations


def test_registry_enthaelt_kuratierte_keys():
    from hydrahive.settings.editable import BY_KEY

    assert "searxng_url" in BY_KEY
    assert BY_KEY["searxng_url"].env_var == "HH_SEARXNG_URL"
    # Mail-Gruppe + Secret-Typ vorhanden
    assert BY_KEY["mail_smtp_password"].type == "secret"
    assert {"Websuche", "Mail", "Discord", "AgentLink", "Health", "System"} <= {
        s.group for s in BY_KEY.values()
    }


def test_resolve_ohne_override_ohne_env_gibt_default():
    from hydrahive.settings.overrides import resolve

    # searxng_url hat default "" → ohne env/override leer
    assert resolve("searxng_url") == ""


def test_resolve_liest_env_wenn_kein_override(monkeypatch, tmp_path):
    from hydrahive.settings import overrides

    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("HH_SEARXNG_URL", "https://searx.env")
    assert overrides.resolve("searxng_url") == "https://searx.env"


def test_override_gewinnt_ueber_env(monkeypatch, tmp_path):
    from hydrahive.settings import overrides

    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("HH_SEARXNG_URL", "https://searx.env")
    overrides.set_override("searxng_url", "https://searx.gui")

    assert overrides.resolve("searxng_url") == "https://searx.gui"
    assert overrides.get_overrides()["searxng_url"] == "https://searx.gui"


def test_set_override_unbekannter_key_wirft(monkeypatch, tmp_path):
    import pytest
    from hydrahive.settings import overrides

    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    with pytest.raises(KeyError):
        overrides.set_override("HH_SECRET_KEY", "hack")  # Bootstrap-Infra nicht editierbar


def test_clear_override_faellt_auf_env_zurueck(monkeypatch, tmp_path):
    from hydrahive.settings import overrides

    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("HH_SEARXNG_URL", "https://searx.env")
    overrides.set_override("searxng_url", "https://searx.gui")
    overrides.clear_override("searxng_url")
    assert overrides.resolve("searxng_url") == "https://searx.env"


def test_env_or_override_ist_dropin_fuer_environ_get(monkeypatch, tmp_path):
    from hydrahive.settings import overrides

    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("HH_MAIL_SMTP_HOST", raising=False)
    # kein env, kein override → default (wie os.environ.get(..., default))
    assert overrides.env_or_override("mail_smtp_host", "HH_MAIL_SMTP_HOST", "fallback") == "fallback"
    monkeypatch.setenv("HH_MAIL_SMTP_HOST", "mail.example")
    assert overrides.env_or_override("mail_smtp_host", "HH_MAIL_SMTP_HOST", "fallback") == "mail.example"
