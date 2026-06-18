"""Tests für die Live-Agent-Aktivitäts-Registry (Pixel-Leiste)."""
from __future__ import annotations

import time

from hydrahive.runner import activity


def _agent():
    return {"id": "a1", "name": "Reviewer"}


def test_start_appears_in_owner_snapshot():
    activity.stop("s1")
    activity.start("s1", _agent(), owner="u", project_id="P")
    snap = activity.snapshot("u")
    assert any(e["session_id"] == "s1" and e["name"] == "Reviewer" and e["project_id"] == "P" for e in snap)
    assert activity.snapshot("other") == []
    activity.stop("s1")


def test_set_tool_and_stop():
    activity.start("s2", _agent(), owner="u", project_id=None)
    activity.set_tool("s2", "shell_exec")
    assert activity.snapshot("u")[0]["current_tool"] == "shell_exec"
    activity.stop("s2")
    assert all(e["session_id"] != "s2" for e in activity.snapshot("u"))


def test_ttl_prunes_stale():
    activity.start("s3", _agent(), owner="u", project_id=None)
    with activity._lock:
        activity._active["s3"].started_at = time.time() - 1000
    assert all(e["session_id"] != "s3" for e in activity.snapshot("u"))


def test_broadcaster_wakes_subscriber():
    q = activity.broadcaster.subscribe()
    try:
        activity.start("s4", _agent(), owner="u", project_id=None)
        assert not q.empty()
    finally:
        activity.broadcaster.unsubscribe(q)
        activity.stop("s4")
