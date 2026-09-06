"""ComfyUI-Video-/Bild-Backend.

ComfyUI ist ein Node-Graph-System (eine Instanz, mehrere Workflows). Ein
konfiguriertes Backend (media_backends[]) trägt eine Liste `workflows`, jeder
mit einem Graph im **API-Format** (`{node_id: {class_type, inputs}}`), einem
`output_node`-Typ (SaveImage / SaveAnimatedWEBP) und `placeholders`, die Felder
im Graph adressieren (z.B. "6.inputs.text" = Prompt).

API (verifiziert gegen ComfyUI script_examples):
  POST /prompt            {"prompt": graph, "client_id": ...} -> {"prompt_id"}
  GET  /history/{id}      -> {id: {"outputs": {node: {"images"|"gifs": [...] }}}}
  GET  /view?filename&subfolder&type=output  -> Bytes (PNG / animiertes WebP)

Video-Workflows liefern WebP/Frames -> ffmpeg -> MP4. Bild-Workflows liefern PNG
direkt.
"""
from __future__ import annotations

import base64
import copy
import logging
import uuid
from pathlib import Path

import httpx

from hydrahive.llm.video_backends._base import (
    JobRef,
    JobStatus,
    VideoModel,
    VideoParams,
)

logger = logging.getLogger(__name__)


def _api_base(provider: dict) -> str:
    base = (provider.get("api_base") or "").rstrip("/")
    if not base:
        raise RuntimeError("ComfyUI-Backend ohne api_base")
    return base


def _workflows(provider: dict) -> list[dict]:
    return provider.get("workflows", []) or []


def _find_workflow(provider: dict, workflow_id: str) -> dict:
    for w in _workflows(provider):
        if w.get("id", "") == workflow_id:
            return w
    raise RuntimeError(f"Workflow '{workflow_id}' nicht im ComfyUI-Backend konfiguriert")


def _apply_placeholders(
    graph: dict,
    placeholders: dict,
    params: VideoParams,
    *,
    image_name: str | None = None,
    end_image_name: str | None = None,
) -> dict:
    """Setzt Parameter und hochgeladene Bildnamen in den Workflow-Graph.

    placeholders: {"prompt": "6.inputs.text", "image_url": "12.inputs.image"}
    Adressformat: "<node_id>.inputs.<field>". Unbekannte/leere Adressen werden
    still übersprungen (nicht jeder Workflow hat jedes Feld).
    """
    g = copy.deepcopy(graph)
    values = {
        "prompt": params.prompt,
        "seed": params.seed,
        "width": params.width,
        "height": params.height,
        "frames": params.frames,
        "image_url": image_name,
        "end_image_url": end_image_name,
    }
    for key, addr in (placeholders or {}).items():
        val = values.get(key)
        if val is None or not addr:
            continue
        parts = addr.split(".")
        # erwartet <node>.inputs.<field>
        if len(parts) != 3 or parts[1] != "inputs":
            logger.warning("ComfyUI: ungültige Platzhalter-Adresse '%s' (key=%s)", addr, key)
            continue
        node_id, _, field = parts
        node = g.get(node_id)
        if not isinstance(node, dict) or "inputs" not in node:
            logger.warning("ComfyUI: Node '%s' fehlt für Platzhalter '%s'", node_id, key)
            continue
        node["inputs"][field] = val
    return g


def _decode_data_uri(value: str) -> tuple[str, bytes]:
    """Dekodiert eine lokale Bild-Data-URI für ComfyUI /upload/image."""
    head, sep, payload = value.partition(",")
    if not sep or ";base64" not in head:
        raise RuntimeError("ComfyUI-Bild muss als base64 Data-URI vorliegen")
    mime = head[5:].split(";", 1)[0] or "image/png"
    try:
        return mime, base64.b64decode(payload, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise RuntimeError("Ungültige Bild-Data-URI für ComfyUI") from exc


async def _upload_image(client: httpx.AsyncClient, base: str, data_uri: str, label: str) -> str:
    """Lädt ein Bild in ComfyUI input/ und gibt den sicheren Dateinamen zurück."""
    mime, content = _decode_data_uri(data_uri)
    suffix = ".jpg" if mime in {"image/jpeg", "image/jpg"} else ".png"
    response = await client.post(
        f"{base}/upload/image",
        files={"image": (f"hydrahive-{label}{suffix}", content, mime)},
        data={"type": "input", "overwrite": "false"},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"ComfyUI /upload/image Fehler {response.status_code}: {response.text[:300]}")
    result = response.json()
    name = str(result.get("name") or "")
    if not name or Path(name).name != name:
        raise RuntimeError("ComfyUI lieferte keinen gültigen Upload-Dateinamen")
    subfolder = str(result.get("subfolder") or "")
    return f"{subfolder}/{name}" if subfolder else name


class ComfyUIVideoBackend:
    type = "comfyui"

    async def list_models(self, provider: dict) -> list[VideoModel]:
        out: list[VideoModel] = []
        for w in _workflows(provider):
            wid = w.get("id", "")
            if not wid:
                continue
            pid = provider.get("id", "")
            out.append(VideoModel(
                id=f"local:{pid}/{wid}",
                name=w.get("label") or wid,
                category=w.get("category", "video"),
                durations=w.get("durations") or [],
                aspect_ratios=w.get("aspect_ratios") or [],
                frame_images=w.get("frame_images") or [],
            ))
        return out

    async def submit(self, provider: dict, model: str, params: VideoParams) -> JobRef:
        # model == "local:<provider_id>/<workflow_id>" → workflow_id extrahieren
        workflow_id = model.split("/", 1)[1] if "/" in model else model
        wf = _find_workflow(provider, workflow_id)
        graph = wf.get("graph") or {}
        if not graph:
            raise RuntimeError(f"Workflow '{workflow_id}' hat keinen Graph")
        client_id = uuid.uuid4().hex
        base = _api_base(provider)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                image_name = None
                end_image_name = None
                if params.image_url:
                    image_name = await _upload_image(client, base, params.image_url, "start")
                if params.end_image_url:
                    end_image_name = await _upload_image(client, base, params.end_image_url, "end")
                filled = _apply_placeholders(
                    graph, wf.get("placeholders") or {}, params,
                    image_name=image_name, end_image_name=end_image_name,
                )
                resp = await client.post(
                    f"{base}/prompt",
                    json={"prompt": filled, "client_id": client_id},
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"ComfyUI /prompt Fehler {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Netzwerk-Fehler beim ComfyUI-Submit: {e}") from e
        prompt_id = data.get("prompt_id") or ""
        if not prompt_id:
            raise RuntimeError(f"Keine prompt_id in ComfyUI-Antwort: {str(data)[:200]}")
        return JobRef(native_id=str(prompt_id),
                      extra={"category": wf.get("category", "video"),
                             "output_node": wf.get("output_node", "")})

    async def poll(self, provider: dict, job: JobRef) -> JobStatus:
        base = _api_base(provider)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(f"{base}/history/{job.native_id}")
                if resp.status_code >= 400:
                    raise RuntimeError(f"ComfyUI /history Fehler {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Netzwerk-Fehler beim ComfyUI-Poll: {e}") from e

        entry = data.get(job.native_id)
        if not entry:
            # noch nicht in der History → läuft/queued
            return JobStatus(state="running", raw=data)
        status = (entry.get("status") or {})
        if status.get("status_str") == "error":
            return JobStatus(state="error",
                             error=str(status.get("messages") or "ComfyUI-Fehler"),
                             raw=entry)
        outputs = entry.get("outputs") or {}
        files = _collect_output_files(outputs)
        if files:
            return JobStatus(state="done", raw={"files": files})
        # in History aber ohne Outputs → noch am Laufen oder fehlgeschlagen
        completed = status.get("completed")
        return JobStatus(state="done" if completed else "running", raw=entry)

    async def fetch_output(self, provider: dict, job: JobRef, dest_dir: Path) -> Path:
        # poll liefert die Datei-Refs in raw["files"] — falls nicht, nochmal pollen
        st = await self.poll(provider, job)
        files = (st.raw or {}).get("files") or []
        if not files:
            raise RuntimeError("ComfyUI-Job ohne Output-Dateien")
        base = _api_base(provider)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Alle Output-Dateien holen
        local_paths: list[Path] = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            for f in files:
                params = {"filename": f["filename"],
                          "subfolder": f.get("subfolder", ""),
                          "type": f.get("type", "output")}
                r = await client.get(f"{base}/view", params=params)
                if r.status_code >= 400 or not r.content:
                    raise RuntimeError(f"ComfyUI /view Fehler für {f['filename']}: {r.status_code}")
                # ComfyUI-Dateinamen sind Remote-Daten: nur den Basename lokal
                # verwenden, damit weder Unterordner noch `../` ausbrechen können.
                safe_name = Path(f["filename"]).name
                if not safe_name:
                    raise RuntimeError("ComfyUI lieferte einen ungültigen Dateinamen")
                p = dest_dir / safe_name
                p.write_bytes(r.content)
                local_paths.append(p)

        category = job.extra.get("category", "video")
        if category == "image":
            # Bild-Workflow → erste PNG direkt zurückgeben
            return local_paths[0]

        # Video-Workflow → WebP/Frames → MP4
        from hydrahive.llm.video_backends._ffmpeg import to_mp4
        return to_mp4(local_paths, dest_dir)


def _collect_output_files(outputs: dict) -> list[dict]:
    """Sammelt alle Output-Datei-Refs (images + gifs/webp) aus einem history-Entry."""
    files: list[dict] = []
    for node_out in (outputs or {}).values():
        if not isinstance(node_out, dict):
            continue
        for key in ("images", "gifs", "videos"):
            for item in node_out.get(key, []) or []:
                if isinstance(item, dict) and item.get("filename"):
                    files.append({
                        "filename": item["filename"],
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    })
    return files
