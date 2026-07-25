"""Protocol + Datentypen für Video-/Bild-Backends.

Ein Backend kapselt einen kompletten Generierungs-Anbieter (OpenRouter, ComfyUI,
Switch-Wrapper). Der Aufruf-Lebenszyklus ist immer gleich:

    models = await backend.list_models(provider)
    job    = await backend.submit(provider, model, params)
    while (st := await backend.poll(provider, job)).state in ("pending","running"):
        await asyncio.sleep(...)
    if st.state == "done":
        data = await backend.fetch_output(provider, job)   # bytes (mp4/png) oder Path

`provider` ist das Config-Dict des jeweiligen Backends aus llm.json
(media_backends[]). Für OpenRouter ist es ein synthetischer Eintrag ohne
api_base — der Adapter zieht seinen Key selbst.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

JobState = Literal["pending", "running", "done", "error"]
Category = Literal["video", "image"]


@dataclass(frozen=True)
class VideoModel:
    """Ein anbietbares Modell/Workflow im Picker."""
    id: str                       # z.B. "minimax/hailuo-2.3" oder "local:muskeln1/ltx-t2v"
    name: str
    category: Category = "video"
    durations: list[int] = field(default_factory=list)
    aspect_ratios: list[str] = field(default_factory=list)
    frame_images: list[str] = field(default_factory=list)  # z.B. ["first_frame"]


@dataclass(frozen=True)
class VideoParams:
    """Generierungs-Parameter — backend-neutral."""
    prompt: str
    width: int = 1280
    height: int = 720
    duration: int = 5
    aspect_ratio: str = "16:9"
    seed: int | None = None
    frames: int | None = None
    image_url: str | None = None  # Startframe (data-URI/https) für I2V


@dataclass(frozen=True)
class JobRef:
    """Opaker Job-Handle. Jedes Backend füllt `native_id` mit seiner eigenen ID."""
    native_id: str
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class JobStatus:
    state: JobState
    url: str | None = None       # falls das Ergebnis eine URL ist
    error: str | None = None
    message: str | None = None   # z.B. "schalte um / generiere …" (Switch-Wrapper)
    raw: dict = field(default_factory=dict)


@runtime_checkable
class VideoBackend(Protocol):
    """Gemeinsame Schnittstelle aller Generierungs-Backends.

    Adapter sind zustandslos — der Zustand steckt in `provider` (Config) und
    `JobRef` (laufender Job).
    """

    type: str  # "openrouter" | "comfyui" | "switch-http"

    async def list_models(self, provider: dict) -> list[VideoModel]:
        """Verfügbare Modelle/Workflows. Leere Liste bei Fehler/nicht konfiguriert."""
        ...

    async def submit(self, provider: dict, model: str, params: VideoParams) -> JobRef:
        """Startet einen Job. Raises RuntimeError bei Submit-Fehler."""
        ...

    async def poll(self, provider: dict, job: JobRef) -> JobStatus:
        """Fragt den Job-Status ab."""
        ...

    async def fetch_output(self, provider: dict, job: JobRef, dest_dir: Path) -> Path:
        """Holt das fertige Ergebnis und speichert es in dest_dir. Gibt Pfad zurück."""
        ...
