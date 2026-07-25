"""E1: VideoBackend-Protocol + Registry/Resolver.

Sichert das Fundament aus docs/specs/local-video-backends.md:
- Resolver mappt Modell-IDs auf den richtigen Adapter (Default = OpenRouter,
  local:<provider>/... = lokales Backend nach type).
- OpenRouter-Adapter delegiert 1:1 an die bestehende _openrouter_video-Logik
  (kein Verhaltensumbau).
- Unbekannte/nicht konfigurierte local:-IDs -> ValueError (kein stiller Fehler).

Importe lazy in den Funktionen (Test-Isolation).
"""
from __future__ import annotations

import asyncio


# --- Resolver: Default = OpenRouter ------------------------------------------

def test_resolve_default_is_openrouter():
    from hydrahive.llm.video_backends import resolve_backend
    backend, provider = resolve_backend("minimax/hailuo-2.3", {})
    assert backend.type == "openrouter"
    assert provider == {}


def test_resolve_openrouter_ignores_media_backends():
    from hydrahive.llm.video_backends import resolve_backend
    cfg = {"media_backends": [{"id": "muskeln1", "type": "comfyui"}]}
    backend, _ = resolve_backend("google/veo-3.1", cfg)
    assert backend.type == "openrouter"


# --- Resolver: local: -> lokales Backend -------------------------------------

def test_resolve_local_unknown_provider_raises():
    from hydrahive.llm.video_backends import resolve_backend
    try:
        resolve_backend("local:doesnotexist/ltx-t2v", {"media_backends": []})
        assert False, "sollte ValueError werfen"
    except ValueError as e:
        assert "doesnotexist" in str(e)


def test_resolve_local_unknown_type_raises():
    from hydrahive.llm.video_backends import resolve_backend
    cfg = {"media_backends": [{"id": "muskeln1", "type": "quantumfoo"}]}
    try:
        resolve_backend("local:muskeln1/x", cfg)
        assert False, "sollte ValueError werfen"
    except ValueError as e:
        assert "quantumfoo" in str(e)


# --- Typen / Protocol vorhanden ----------------------------------------------

def test_protocol_and_types_exist():
    from hydrahive.llm.video_backends import (
        JobRef, JobStatus, VideoBackend, VideoModel, VideoParams,
    )
    p = VideoParams(prompt="hello", width=768, height=432, frames=121)
    assert p.prompt == "hello" and p.frames == 121
    ref = JobRef(native_id="abc")
    assert ref.native_id == "abc"
    st = JobStatus(state="done", url="http://x/y.mp4")
    assert st.state == "done"
    m = VideoModel(id="a", name="A", category="video")
    assert m.category == "video"
    # OpenRouter-Adapter erfüllt das runtime-checkable Protocol
    from hydrahive.llm.video_backends._openrouter import OpenRouterVideoBackend
    assert isinstance(OpenRouterVideoBackend(), VideoBackend)


# --- OpenRouter-Adapter delegiert (submit/poll) ------------------------------

def test_openrouter_backend_submit_delegates(monkeypatch):
    from hydrahive.llm.video_backends._openrouter import OpenRouterVideoBackend
    from hydrahive.llm.video_backends._base import VideoParams
    import hydrahive.tools._openrouter_video as ov

    captured = {}

    async def fake_submit(prompt, model, *, key, **kw):
        captured.update(prompt=prompt, model=model, key=key, **kw)
        return "job-123"

    monkeypatch.setattr(ov, "submit_video_job", fake_submit)
    monkeypatch.setattr(ov, "openrouter_key", lambda: "sk-test")

    b = OpenRouterVideoBackend()
    ref = asyncio.run(b.submit({}, "minimax/hailuo-2.3",
                               VideoParams(prompt="a cat", duration=10)))
    assert ref.native_id == "job-123"
    assert captured["model"] == "minimax/hailuo-2.3"
    assert captured["duration"] == 10


def test_openrouter_backend_poll_maps_state(monkeypatch):
    from hydrahive.llm.video_backends._openrouter import OpenRouterVideoBackend
    from hydrahive.llm.video_backends._base import JobRef
    import hydrahive.tools._openrouter_video as ov

    async def fake_poll(job_id, *, key):
        return {"status": "completed", "url": "http://x/v.mp4", "error": None, "_raw": {}}

    monkeypatch.setattr(ov, "poll_video_job", fake_poll)
    monkeypatch.setattr(ov, "openrouter_key", lambda: "sk-test")

    b = OpenRouterVideoBackend()
    st = asyncio.run(b.poll({}, JobRef(native_id="job-123")))
    assert st.state == "done"
    assert st.url == "http://x/v.mp4"
