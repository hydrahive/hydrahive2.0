"""Video-/Bild-Generierungs-Backends hinter einem gemeinsamen Protocol.

E1-Fundament (Spec: docs/specs/local-video-backends.md). Ziel: die heute hart
auf OpenRouter verdrahtete Video-Generierung so kapseln, dass lokale Backends
(ComfyUI, node-lokaler Switch-Wrapper) als weitere Adapter danebentreten können —
ohne den OpenRouter-Pfad zu ändern.

Öffentliche API:
- VideoBackend (Protocol), JobRef, JobStatus, VideoModel, VideoParams
- resolve_backend(model_id, config) -> (backend, provider) — mappt eine Modell-ID
  auf den zuständigen Adapter. Default (kein `local:`-Prefix) = OpenRouter.
"""
from __future__ import annotations

from hydrahive.llm.video_backends._base import (
    JobRef,
    JobStatus,
    VideoBackend,
    VideoModel,
    VideoParams,
)
from hydrahive.llm.video_backends._registry import (
    LOCAL_PREFIX,
    resolve_backend,
)
from hydrahive.llm.video_backends._runner import run_local_media

__all__ = [
    "VideoBackend",
    "JobRef",
    "JobStatus",
    "VideoModel",
    "VideoParams",
    "resolve_backend",
    "run_local_media",
    "LOCAL_PREFIX",
]
