"""Presence-Tracker — online = aktive teamchat-SSE-Verbindung (TDD).

Reiner In-Memory-Refcount pro User, kein I/O. Lazy import (data_dir-Freeze-Gotcha).
"""
from __future__ import annotations


def _presence():
    from hydrahive.teamchat.presence import Presence
    return Presence()


def test_connect_marks_user_online():
    p = _presence()
    assert "till" not in p.online_users()
    p.connect("till")
    assert "till" in p.online_users()


def test_two_connects_one_disconnect_still_online():
    """Mehrere Tabs/Räume = mehrere Verbindungen → erst offline wenn alle zu."""
    p = _presence()
    p.connect("till")
    p.connect("till")
    p.disconnect("till")
    assert "till" in p.online_users()
    p.disconnect("till")
    assert "till" not in p.online_users()


def test_disconnect_unknown_is_noop():
    p = _presence()
    p.disconnect("ghost")  # darf nicht werfen
    assert p.online_users() == set()


def test_online_users_multiple():
    p = _presence()
    p.connect("till")
    p.connect("bibi")
    assert p.online_users() == {"till", "bibi"}
