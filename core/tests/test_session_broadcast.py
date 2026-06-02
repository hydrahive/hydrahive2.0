"""Live-Sync v1: schlanker Per-Session-Broadcaster.

Ein User, mehrere Geräte/Tabs derselben Session → jeder offene Client abonniert
eine Queue, der Lauf broadcastet leichte Pings, die Clients laden bei Ping nach.
Kein Presence/Replay (das wäre v2) — nur fan-out + sauberes Cleanup.
"""
from __future__ import annotations

import asyncio

import pytest


def test_subscribe_gibt_queue_und_zaehlt():
    from hydrahive.api._session_broadcast import SessionBroadcaster

    b = SessionBroadcaster()
    assert b.subscriber_count("s1") == 0
    q = b.subscribe("s1")
    assert isinstance(q, asyncio.Queue)
    assert b.subscriber_count("s1") == 1


@pytest.mark.asyncio
async def test_broadcast_erreicht_alle_subscriber():
    from hydrahive.api._session_broadcast import SessionBroadcaster

    b = SessionBroadcaster()
    q1 = b.subscribe("s1")
    q2 = b.subscribe("s1")
    q_other = b.subscribe("s2")

    b.broadcast("s1", '{"t":"activity"}')

    assert q1.get_nowait() == '{"t":"activity"}'
    assert q2.get_nowait() == '{"t":"activity"}'
    assert q_other.empty()  # andere Session → nichts


def test_unsubscribe_entfernt_und_raeumt_auf():
    from hydrahive.api._session_broadcast import SessionBroadcaster

    b = SessionBroadcaster()
    q = b.subscribe("s1")
    b.unsubscribe("s1", q)
    assert b.subscriber_count("s1") == 0
    # broadcast auf leere Session = kein Fehler
    b.broadcast("s1", "x")


def test_volle_queue_droppt_statt_zu_crashen():
    from hydrahive.api._session_broadcast import SessionBroadcaster

    b = SessionBroadcaster(maxsize=2)
    q = b.subscribe("s1")
    # mehr broadcasten als die Queue fasst → kein Crash, älteste/überzählige droppen
    for i in range(10):
        b.broadcast("s1", str(i))
    assert q.qsize() <= 2
