"""Regression tests for immutable Core user identities."""
from __future__ import annotations

import json

from hydrahive.api.middleware import users
from hydrahive.settings import settings


def _legacy_users_file(tmp_path, monkeypatch):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({
        "alice": {"password_hash": "legacy-hash", "role": "user"},
    }))
    monkeypatch.setattr(settings, "users_config", path, raising=False)
    return path


def test_legacy_user_receives_persisted_stable_id(tmp_path, monkeypatch):
    path = _legacy_users_file(tmp_path, monkeypatch)

    first = users.get_by_username("alice")
    second = users.get_by_username("alice")
    stored = json.loads(path.read_text())

    assert first is not None
    assert first["user_id"] == second["user_id"]
    assert stored["alice"]["user_id"] == first["user_id"]
    assert "password_hash" not in first


def test_delete_and_recreate_same_username_gets_new_id(tmp_path, monkeypatch):
    path = tmp_path / "users.json"
    path.write_text("{}")
    monkeypatch.setattr(settings, "users_config", path, raising=False)

    old_id = users.create("alice", "first-password")
    users.delete("alice")
    new_id = users.create("alice", "second-password")

    assert old_id != new_id
    assert users.get_by_id(old_id) is None
    assert users.get_by_id(new_id) == {
        "user_id": new_id,
        "username": "alice",
        "role": "user",
    }


def test_list_users_includes_id_without_password_hash(tmp_path, monkeypatch):
    _legacy_users_file(tmp_path, monkeypatch)

    result = users.list_users()

    assert result == [{
        "user_id": result[0]["user_id"],
        "username": "alice",
        "role": "user",
    }]
    assert "password_hash" not in result[0]
