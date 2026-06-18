"""SSE-Route /api/agents/activity/stream — Auth + initiale Owner-Momentaufnahme.

Der Stream ist endlos; statt ihn über den TestClient zu lesen (hängt), rufen wir
den Handler direkt auf und lesen genau einen Frame aus dem body_iterator.
"""
from __future__ import annotations

import asyncio


def test_stream_requires_auth(client):
    r = client.get("/api/agents/activity/stream")
    assert r.status_code == 401


def test_stream_sends_initial_owner_snapshot():
    from hydrahive.api.routes.agent_activity import stream_activity
    from hydrahive.runner import activity

    activity.start("sess-r", {"id": "a1", "name": "Reviewer"}, owner="testuser", project_id="P")

    async def _first_frame() -> str:
        resp = await stream_activity(auth=("testuser", "user"))
        frame = await resp.body_iterator.__anext__()
        await resp.body_iterator.aclose()  # → finally: unsubscribe
        return frame

    try:
        frame = asyncio.run(_first_frame())
        assert frame.startswith("data:")
        assert "Reviewer" in frame
        # Owner-Filter: fremder User sieht ihn nicht
        assert all(e["name"] != "Reviewer" for e in activity.snapshot("someone_else"))
    finally:
        activity.stop("sess-r")
