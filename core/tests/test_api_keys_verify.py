"""API-Key-Verifikation (Issue #205, kritischer Pfad).

verify() ist das Auth-Gate für API-Key-authentifizierte Requests. Getestet:
Round-Trip (create→verify), Ablehnung falscher/manipulierter Keys, Owner-
gescoptes delete.
"""
from __future__ import annotations

from hydrahive.api.middleware import api_keys


def test_create_then_verify_roundtrip(client):
    plain = api_keys.create("test-key", "alice", "user")
    assert plain.startswith("hhk_")
    result = api_keys.verify(plain)
    assert result == {"username": "alice", "role": "user"}


def test_verify_rejects_garbage(client):
    assert api_keys.verify("not-a-key") is None
    assert api_keys.verify("hhk_deadbeefdeadbeef_totally-wrong-token-aaaaaaaaaaaaaaaaaaaa") is None


def test_verify_rejects_tampered_key(client):
    plain = api_keys.create("k", "bob", "admin")
    tampered = plain[:-1] + ("X" if plain[-1] != "X" else "Y")
    assert api_keys.verify(tampered) is None


def test_delete_is_owner_scoped(client):
    plain = api_keys.create("ownkey", "carol", "user")
    key_id = plain.split("_")[1]

    assert api_keys.delete(key_id, "mallory") is False, "fremder User darf nicht löschen"
    assert api_keys.verify(plain) is not None

    assert api_keys.delete(key_id, "carol") is True
    assert api_keys.verify(plain) is None, "nach delete kein gültiger Key mehr"
