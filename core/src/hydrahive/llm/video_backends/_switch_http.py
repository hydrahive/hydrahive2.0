"""Switch-HTTP-Backend — spricht den node-lokalen Switch-Wrapper.

Der Wrapper läuft dauerhaft und leichtgewichtig auf dem Generierungs-Node und
kapselt dort den VRAM-Konflikt (LLM-Runtime <-> Bild-/Video-Runtime): er lädt
die LLM-Runtime aus, startet die Generierungs-Runtime, generiert, räumt wieder
auf. HydraHive muss sich um VRAM **nicht** kümmern.

Vertrag (docs/specs/local-video-backends.md):

    GET  /health           -> {"status":"ok","mode":"ollama|sd|switching"}
    GET  /models           -> [{"id","name","category":"image|video"}]
    POST /generate         -> {"job_id"}
    GET  /status/{job_id}  -> {"state":"pending|running|done|error","message?"}
    GET  /result/{job_id}  -> Bytes ODER {"url"}
    POST /release          -> {"ok":true}   (optional)

Bewusst schmal: Das interne Payload-Schema der Generierungs-Runtime kennt
**nur** der Wrapper. Dieser Adapter kennt ausschließlich obigen Vertrag — so
bleibt HydraHive unabhängig davon, was auf dem Node tatsächlich läuft.

Anders als bei ComfyUI gibt es hier **keine** Workflow-Graphen: der Wrapper
bietet fertige Modelle/Presets an.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from hydrahive.llm.video_backends._base import (
    JobRef,
    JobStatus,
    VideoModel,
    VideoParams,
)

logger = logging.getLogger(__name__)

# Ein Generate kann inkl. Runtime-Umschaltung Minuten dauern; Submit selbst
# antwortet aber sofort mit der job_id. Nur der Result-Download braucht Luft.
_TIMEOUT_SHORT = 20.0
_TIMEOUT_DOWNLOAD = 300.0

_VALID_STATES = {"pending", "running", "done", "error"}

_EXT_BY_CONTENT_TYPE = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _api_base(provider: dict) -> str:
    base = (provider.get("api_base") or "").rstrip("/")
    if not base:
        raise RuntimeError("Switch-Backend ohne api_base")
    return base


def _bare_model_id(model: str, provider_id: str) -> str:
    """'local:muskeln2/ltx-video' -> 'ltx-video'.

    Der Wrapper kennt nur seine eigenen IDs — der `local:`-Prefix ist reine
    HydraHive-Routing-Information.
    """
    rest = model.split(":", 1)[1] if model.startswith("local:") else model
    if rest.startswith(f"{provider_id}/"):
        return rest[len(provider_id) + 1:]
    return rest.split("/", 1)[1] if "/" in rest else rest


def _ext_for(content_type: str, fallback: str = ".bin") -> str:
    return _EXT_BY_CONTENT_TYPE.get(content_type.split(";")[0].strip().lower(), fallback)


class SwitchHttpVideoBackend:
    """Adapter gegen den Switch-Wrapper-Vertrag."""

    type = "switch-http"

    async def list_models(self, provider: dict) -> list[VideoModel]:
        """Verfügbare Modelle. Leere Liste bei jedem Fehler — ein nicht
        erreichbarer Node darf den Modell-Picker nicht sprengen."""
        try:
            base = _api_base(provider)
        except RuntimeError:
            return []
        pid = provider.get("id", "")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SHORT) as client:
                resp = await client.get(f"{base}/models")
                if resp.status_code >= 400:
                    logger.warning("Switch-Wrapper /models Fehler %s (%s)", resp.status_code, pid)
                    return []
                data = resp.json()
        except Exception as e:  # noqa: BLE001 - Picker darf nie hart fehlschlagen
            logger.warning("Switch-Wrapper /models nicht erreichbar (%s): %s", pid, e)
            return []

        out: list[VideoModel] = []
        for m in data or []:
            if not isinstance(m, dict):
                continue
            mid = m.get("id", "")
            if not mid:
                continue
            out.append(VideoModel(
                id=f"local:{pid}/{mid}",
                name=m.get("name") or mid,
                category=m.get("category", "video"),
                durations=m.get("durations") or [],
                aspect_ratios=m.get("aspect_ratios") or [],
                frame_images=m.get("frame_images") or [],
            ))
        return out

    async def submit(self, provider: dict, model: str, params: VideoParams) -> JobRef:
        base = _api_base(provider)
        payload = {
            "model": _bare_model_id(model, provider.get("id", "")),
            "prompt": params.prompt,
            "width": params.width,
            "height": params.height,
        }
        # Optionale Felder nur senden wenn gesetzt — der Wrapper hat eigene Defaults.
        if params.seed is not None:
            payload["seed"] = params.seed
        if params.frames is not None:
            payload["frames"] = params.frames
        if params.image_url:
            payload["image_url"] = params.image_url

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SHORT) as client:
                resp = await client.post(f"{base}/generate", json=payload)
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"Switch-Wrapper /generate Fehler {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Netzwerk-Fehler beim Switch-Submit: {e}") from e

        job_id = (data or {}).get("job_id") or ""
        if not job_id:
            raise RuntimeError(f"Keine job_id in Wrapper-Antwort: {str(data)[:200]}")
        return JobRef(native_id=str(job_id))

    async def poll(self, provider: dict, job: JobRef) -> JobStatus:
        base = _api_base(provider)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SHORT) as client:
                resp = await client.get(f"{base}/status/{job.native_id}")
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"Switch-Wrapper /status Fehler {resp.status_code}: {resp.text[:300]}")
                data = resp.json() or {}
        except httpx.HTTPError as e:
            raise RuntimeError(f"Netzwerk-Fehler beim Switch-Poll: {e}") from e

        raw_state = str(data.get("state", ""))
        message = data.get("message")
        if raw_state not in _VALID_STATES:
            # Fail-safe: unbekannt heißt NIE "done" — sonst würde der Caller ein
            # Ergebnis abholen wollen, das es gar nicht gibt.
            logger.warning("Switch-Wrapper meldet unbekannten state %r — als running behandelt",
                           raw_state)
            return JobStatus(state="running", message=message, raw=data)
        if raw_state == "error":
            return JobStatus(state="error", error=str(message or "Wrapper-Fehler"),
                             message=message, raw=data)
        return JobStatus(state=raw_state, url=data.get("url"), message=message, raw=data)

    async def fetch_output(self, provider: dict, job: JobRef, dest_dir: Path) -> Path:
        """Holt das Ergebnis. Der Vertrag erlaubt beides: rohe Bytes oder {"url"}."""
        base = _api_base(provider)
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_DOWNLOAD) as client:
                resp = await client.get(f"{base}/result/{job.native_id}")
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"Switch-Wrapper /result Fehler {resp.status_code}: {resp.text[:300]}")
                content_type = resp.headers.get("content-type", "")
                content = resp.content
                # Variante 2: JSON mit URL -> zweiter Hop
                if "application/json" in content_type.lower():
                    url = (resp.json() or {}).get("url") or ""
                    if not url:
                        raise RuntimeError("Wrapper-Ergebnis ohne Daten und ohne url")
                    resp = await client.get(url)
                    if resp.status_code >= 400:
                        raise RuntimeError(
                            f"Switch-Wrapper Result-URL Fehler {resp.status_code}")
                    content_type = resp.headers.get("content-type", "")
                    content = resp.content
        except httpx.HTTPError as e:
            raise RuntimeError(f"Netzwerk-Fehler beim Switch-Result: {e}") from e

        if not content:
            raise RuntimeError("Switch-Wrapper lieferte ein leeres Ergebnis")

        ext = _ext_for(content_type)
        out = dest_dir / f"{job.native_id}{ext}"
        out.write_bytes(content)
        return out

    # --- Zusatz über das Protocol hinaus (GUI-Komfort) ----------------------

    async def health(self, provider: dict) -> tuple[bool, dict]:
        """Für „Verbindung testen": (erreichbar, {status, mode}).

        Der `mode` sagt der GUI, ob der Node gerade die LLM- oder die
        Generierungs-Runtime geladen hat bzw. gerade umschaltet.
        """
        try:
            base = _api_base(provider)
            async with httpx.AsyncClient(timeout=_TIMEOUT_SHORT) as client:
                resp = await client.get(f"{base}/health")
                if resp.status_code >= 400:
                    return False, {"error": f"HTTP {resp.status_code}"}
                data = resp.json() or {}
        except Exception as e:  # noqa: BLE001 - Health darf nie werfen
            return False, {"error": str(e)}
        return str(data.get("status", "")).lower() == "ok", data

    async def release(self, provider: dict) -> bool:
        """Bittet den Wrapper, die Generierungs-Runtime freizugeben.

        Laut Vertrag optional — der Wrapper räumt nach jedem Job ohnehin selbst
        auf. Deshalb best-effort: ein 404 ist kein Fehler, nur ein `False`.
        """
        try:
            base = _api_base(provider)
            async with httpx.AsyncClient(timeout=_TIMEOUT_SHORT) as client:
                resp = await client.post(f"{base}/release")
                if resp.status_code >= 400:
                    return False
                return bool((resp.json() or {}).get("ok"))
        except Exception as e:  # noqa: BLE001 - best effort
            logger.debug("Switch-Wrapper /release nicht verfügbar: %s", e)
            return False
