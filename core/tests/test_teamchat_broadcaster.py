"""Tests für RoomBroadcaster — SSE-Fanout pro room_id.

Spiegelt die Semantik von _session_broadcast.py, nur mit room_id statt session_id.
Alle Tests sind synchron: asyncio.Queue.put_nowait/get_nowait brauchen keine
laufende Event-Loop für den nicht-blockierenden Pfad.
"""
import asyncio

import pytest

from hydrahive.teamchat.broadcaster import RoomBroadcaster


def make_broadcaster(maxsize: int = 4) -> RoomBroadcaster:
    return RoomBroadcaster(maxsize=maxsize)


# ---------------------------------------------------------------------------
# subscribe → broadcast → receive
# ---------------------------------------------------------------------------


def test_subscribe_then_broadcast_delivers_payload():
    """Einzelner Subscriber empfängt die broadcastete Nachricht."""
    bc = make_broadcaster()
    q = bc.subscribe("room-1")
    bc.broadcast("room-1", "hello")
    assert q.get_nowait() == "hello"


# ---------------------------------------------------------------------------
# zwei Subscriber auf demselben Room
# ---------------------------------------------------------------------------


def test_two_subscribers_both_receive():
    """Beide Queues bekommen dasselbe Payload."""
    bc = make_broadcaster()
    q1 = bc.subscribe("room-x")
    q2 = bc.subscribe("room-x")
    bc.broadcast("room-x", "ping")
    assert q1.get_nowait() == "ping"
    assert q2.get_nowait() == "ping"


# ---------------------------------------------------------------------------
# Isolation: verschiedene Rooms
# ---------------------------------------------------------------------------


def test_different_rooms_are_isolated():
    """Broadcast an room-A darf nicht in room-B-Queue landen."""
    bc = make_broadcaster()
    qa = bc.subscribe("room-a")
    qb = bc.subscribe("room-b")
    bc.broadcast("room-a", "only-a")
    # room-a queue has the message
    assert qa.get_nowait() == "only-a"
    # room-b queue must be empty
    with pytest.raises(asyncio.QueueEmpty):
        qb.get_nowait()


# ---------------------------------------------------------------------------
# unsubscribe: keine Nachrichten mehr; leerer Room wird aus State entfernt
# ---------------------------------------------------------------------------


def test_unsubscribe_stops_delivery():
    """Nach unsubscribe erhält die Queue keine Broadcasts mehr."""
    bc = make_broadcaster()
    q = bc.subscribe("room-1")
    bc.unsubscribe("room-1", q)
    bc.broadcast("room-1", "should-not-arrive")
    with pytest.raises(asyncio.QueueEmpty):
        q.get_nowait()


def test_unsubscribe_cleans_up_empty_room():
    """Leerer Room darf nicht als leeres Set im internen Dict bleiben."""
    bc = make_broadcaster()
    q = bc.subscribe("room-cleanup")
    bc.unsubscribe("room-cleanup", q)
    # Internes Dict darf den Key nicht mehr enthalten
    assert "room-cleanup" not in bc._subs


# ---------------------------------------------------------------------------
# QueueFull: ältestes Item droppen, neues einfügen
# ---------------------------------------------------------------------------


def test_queue_full_drops_oldest():
    """Wird die Queue gefüllt, fliegt das älteste Item raus und das neue rein."""
    maxsize = 2
    bc = make_broadcaster(maxsize=maxsize)
    q = bc.subscribe("room-full")

    # Queue bis maxsize füllen
    bc.broadcast("room-full", "msg-1")
    bc.broadcast("room-full", "msg-2")
    assert q.qsize() == 2

    # Eine weitere Nachricht → Queue voll → älteste (msg-1) wird gedroppt
    bc.broadcast("room-full", "msg-3")

    assert q.qsize() == 2
    assert q.get_nowait() == "msg-2"
    assert q.get_nowait() == "msg-3"
