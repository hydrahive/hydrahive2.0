"""OpenRouter-Video-Backend — kapselt die bestehende _openrouter_video-Logik.

E1: KEIN Verhaltensumbau. Dieser Adapter delegiert 1:1 an die vorhandenen
Funktionen (submit_video_job/poll_video_job/download_video/list_video_models),
damit der OpenRouter-Pfad exakt gleich bleibt und nur hinter das Protocol wandert.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.llm.video_backends._base import (
    JobRef,
    JobStatus,
    VideoModel,
    VideoParams,
)


class OpenRouterVideoBackend:
    type = "openrouter"

    async def list_models(self, provider: dict) -> list[VideoModel]:
        from hydrahive.llm.media_models import list_video_models
        raw = await list_video_models()
        return [
            VideoModel(
                id=m.get("id", ""),
                name=m.get("name") or m.get("id", ""),
                category="video",
                durations=m.get("durations") or [],
                aspect_ratios=m.get("aspect_ratios") or [],
                frame_images=m.get("frame_images") or [],
            )
            for m in raw if m.get("id")
        ]

    async def submit(self, provider: dict, model: str, params: VideoParams) -> JobRef:
        from hydrahive.tools._openrouter_video import openrouter_key, submit_video_job
        key = openrouter_key()
        if not key:
            raise RuntimeError("Kein OpenRouter-Key konfiguriert")
        job_id = await submit_video_job(
            params.prompt, model, key=key,
            width=params.width, height=params.height,
            duration=params.duration, aspect_ratio=params.aspect_ratio,
            image_url=params.image_url,
        )
        return JobRef(native_id=job_id)

    async def poll(self, provider: dict, job: JobRef) -> JobStatus:
        from hydrahive.tools._openrouter_video import openrouter_key, poll_video_job
        res = await poll_video_job(job.native_id, key=openrouter_key())
        status = (res.get("status") or "pending").lower()
        state = {
            "completed": "done", "failed": "error",
            "processing": "running", "pending": "pending",
        }.get(status, "pending")
        return JobStatus(
            state=state,  # type: ignore[arg-type]
            url=res.get("url"),
            error=res.get("error"),
            raw=res.get("_raw") or {},
        )

    async def fetch_output(self, provider: dict, job: JobRef, dest_dir: Path) -> Path:
        from hydrahive.tools._openrouter_video import download_video, openrouter_key
        # Die URL kommt aus dem letzten poll — der Caller reicht sie via job.extra
        url = job.extra.get("url")
        if not url:
            # Fallback: nochmal pollen, um die aktuelle URL zu holen
            st = await self.poll(provider, job)
            url = st.url
        if not url:
            raise RuntimeError("Keine Download-URL für fertigen Video-Job")
        return await download_video(url, dest_dir, key=openrouter_key())
