"""session_end muss die Live-Aktivität abräumen (Hook für die Pixel-Leiste)."""
from __future__ import annotations

from hydrahive.runner import activity
from hydrahive.tools import _sessions


def test_session_end_stops_activity():
    activity.start("sess-x", {"id": "a1", "name": "X"}, owner="u", project_id=None)
    assert activity.snapshot("u")
    _sessions.session_end("a1", "sess-x", status="completed")
    assert all(e["session_id"] != "sess-x" for e in activity.snapshot("u"))
