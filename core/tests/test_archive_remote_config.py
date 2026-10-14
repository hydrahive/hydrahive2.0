"""Externer Server: Einstellungen und Verbindungstest (Spec archiv-system.md, Etappe 3)."""
from __future__ import annotations

import json

import pytest

from tests.conftest import error_code

pytest_plugins = ["tests._delete_env", "tests._remote_env"]  # archive_root, fake_remote, remote_queue, remote_on

GOOD = {"host": "nas.local", "share": "Backups", "subdir": "hydrahive", "user": "hh", "password": "geheim-NAS-123"}


@pytest.fixture(autouse=True)
def _clean():
    from hydrahive.archive import remote_config
    remote_config.reset_for_tests()
    yield
    remote_config.reset_for_tests()


def test_password_is_encrypted_and_never_returned() -> None:
    from hydrahive.archive import remote_config
    remote_config.save(dict(GOOD))
    raw = remote_config._path().read_text()
    assert "geheim-NAS-123" not in raw
    public = remote_config.public()
    assert "password" not in public and public["password_set"] is True
    assert "geheim-NAS-123" not in json.dumps(public)
    assert remote_config.load()["password"] == "geheim-NAS-123"


def test_empty_password_keeps_the_old_one() -> None:
    from hydrahive.archive import remote_config
    remote_config.save(dict(GOOD))
    remote_config.save({**GOOD, "password": "", "subdir": "neu"})
    cfg = remote_config.load()
    assert cfg["password"] == "geheim-NAS-123" and cfg["subdir"] == "neu"


@pytest.mark.parametrize("field,value", [
    ("host", "nas local"), ("host", "a/b"), ("host", ""), ("share", "a\\b"), ("share", ""),
    ("subdir", "../etc"), ("subdir", "a/../b"), ("user", "a b;c"),
])
def test_invalid_values_are_rejected(field, value) -> None:
    from hydrahive.archive import remote_config
    with pytest.raises(remote_config.RemoteConfigError):
        remote_config.save({**GOOD, field: value})


def test_leading_slash_in_subdir_is_normalized() -> None:
    """Prod trägt den Unterordner als „/hydrahive“ ein (wie beim Projekt-Laufwerk) – das ist kein Fehler."""
    from hydrahive.archive import remote_config
    remote_config.save({**GOOD, "subdir": "/hydrahive/"})
    assert remote_config.public()["subdir"] == "hydrahive"


def test_changed_settings_deactivate_until_tested_again(fake_remote) -> None:
    from hydrahive.archive import remote_config
    remote_config.save(dict(GOOD))
    with pytest.raises(remote_config.RemoteConfigError):
        remote_config.set_active(True)                       # nie getestet
    assert remote_config.test()["ok"] is True
    remote_config.set_active(True)
    assert remote_config.public()["active"] is True
    remote_config.save({**GOOD, "share": "Andere"})
    assert remote_config.public()["active"] is False         # neue Daten = neu testen


@pytest.mark.parametrize("problem,code", [
    ("down", "unreachable"), ("auth", "auth_failed"), ("share", "share_not_found"), ("ro", "not_writable"),
])
def test_connection_test_names_the_reason(fake_remote, monkeypatch, problem, code) -> None:
    from hydrahive.archive import remote_config, remote_smb
    remote_config.save(dict(GOOD))

    def failing(cfg):
        raise remote_smb.RemoteError({"down": "unreachable", "auth": "auth_failed", "share": "share_not_found",
                                      "ro": "not_writable"}[problem])

    monkeypatch.setattr(remote_smb, "connect", failing)
    result = remote_config.test()
    assert result["ok"] is False and result["error"] == code
    assert remote_config.public()["tested"] is False


def test_routes(client, admin_headers, auth_headers, fake_remote) -> None:
    r = client.put("/api/admin/archive/remote", headers=admin_headers, json=GOOD)
    assert r.status_code == 200 and "password" not in r.json() and r.json()["password_set"] is True
    assert client.get("/api/admin/archive/remote", headers=auth_headers).status_code == 403
    r = client.put("/api/admin/archive/remote", headers=admin_headers, json={**GOOD, "subdir": "../x"})
    assert r.status_code == 400 and error_code(r) == "archive_remote_invalid"
    r = client.post("/api/admin/archive/remote/active", headers=admin_headers, json={"active": True})
    assert r.status_code == 409 and error_code(r) == "archive_remote_untested"
    r = client.post("/api/admin/archive/remote/test", headers=admin_headers)
    assert r.status_code == 200 and r.json()["ok"] is True and r.json()["free_bytes"] > 0
    r = client.post("/api/admin/archive/remote/active", headers=admin_headers, json={"active": True})
    assert r.status_code == 200 and r.json()["active"] is True
    status = client.get("/api/admin/archive/status", headers=admin_headers).json()
    assert status["remote"]["active"] is True and "password" not in json.dumps(status["remote"]).replace(
        "password_set", "")
