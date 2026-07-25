"""Verwaltung lokaler Media-Backends (ComfyUI, Switch-Wrapper) — E3.

GUI-getrieben (Spec: docs/specs/local-video-backends.md). Endpoints:
  GET    /api/media-backends              → Liste (ohne Graph-Ballast)
  PUT    /api/media-backends              → ganze Liste speichern
  POST   /api/media-backends/test         → Verbindung testen (ComfyUI/switch)
  POST   /api/media-backends/parse-workflow → Workflow-JSON parsen, Felder +
         Platzhalter-Vorschläge liefern (kein JSON-Handarbeit im UI)

Alles admin-only. Speicherung in llm.json unter `media_backends`.
"""
from __future__ import annotations

import json
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

router = APIRouter(prefix="/api/media-backends", tags=["media-backends"])


def _load() -> dict:
    if not settings.llm_config.exists():
        return {}
    return json.loads(settings.llm_config.read_text())


def _save(data: dict) -> None:
    settings.llm_config.parent.mkdir(parents=True, exist_ok=True)
    settings.llm_config.write_text(json.dumps(data, indent=2))


def _summary(b: dict) -> dict:
    """Backend ohne die schweren Graph-JSONs (für die Listen-Ansicht)."""
    return {
        "id": b.get("id", ""),
        "type": b.get("type", ""),
        "name": b.get("name", ""),
        "api_base": b.get("api_base", ""),
        "workflows": [
            {"id": w.get("id"), "label": w.get("label"),
             "category": w.get("category", "video"),
             "output_node": w.get("output_node", "")}
            for w in (b.get("workflows") or [])
        ],
    }


@router.get("", dependencies=[Depends(require_admin)])
def list_backends() -> dict:
    data = _load()
    return {"media_backends": [_summary(b) for b in data.get("media_backends", [])]}


class BackendsPayload(BaseModel):
    media_backends: list[dict] = []


@router.put("", dependencies=[Depends(require_admin)])
def save_backends(payload: BackendsPayload) -> dict:
    data = _load()
    data["media_backends"] = payload.media_backends
    _save(data)
    return {"ok": True, "count": len(payload.media_backends)}


class TestReq(BaseModel):
    type: str
    api_base: str


@router.post("/test", dependencies=[Depends(require_admin)])
async def test_backend(req: TestReq) -> dict:
    """Prüft Erreichbarkeit eines Backends. ComfyUI: /object_info; switch-http: /health."""
    base = (req.api_base or "").rstrip("/")
    if not base:
        raise coded(400, "no_api_base", message="api_base fehlt")
    if req.type == "comfyui":
        url = f"{base}/object_info"
    elif req.type == "switch-http":
        url = f"{base}/health"
    else:
        raise coded(400, "unknown_type", message=f"Unbekannter Typ '{req.type}'")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return {"ok": False, "status": resp.status_code, "url": url}
            info: dict = {"ok": True, "url": url}
            if req.type == "switch-http":
                try:
                    body = resp.json()
                    info["mode"] = body.get("mode")
                except Exception:
                    pass
            elif req.type == "comfyui":
                try:
                    info["node_count"] = len(resp.json())
                except Exception:
                    pass
            return info
    except httpx.HTTPError as e:
        return {"ok": False, "error": str(e), "url": url}


class ParseReq(BaseModel):
    graph: dict


# ComfyUI-Node-Typen → welches params-Feld sie typischerweise steuern (Heuristik).
_HEURISTICS = {
    "CLIPTextEncode": ("text", "prompt"),
    "KSampler": ("seed", "seed"),
    "KSamplerAdvanced": ("noise_seed", "seed"),
    "EmptyLatentImage": ("width", "width"),
    "EmptyLatentVideo": ("length", "frames"),
    "LTXVBaseSampler": ("seed", "seed"),
}


@router.post("/parse-workflow", dependencies=[Depends(require_admin)])
def parse_workflow(req: ParseReq) -> dict:
    """Zerlegt einen ComfyUI-API-Graph in Felder + schlägt Platzhalter-Mapping vor.

    Rückgabe:
      nodes: [{id, class_type, inputs: [feldnamen]}]
      suggestions: {prompt: "6.inputs.text", seed: "3.inputs.seed", ...}

    Das UI zeigt die Vorschläge vorbelegt, der User kann sie per Dropdown ändern.
    """
    graph = req.graph or {}
    if not isinstance(graph, dict) or not graph:
        raise coded(400, "invalid_graph", message="Graph ist leer oder kein Objekt")

    nodes = []
    suggestions: dict[str, str] = {}
    for node_id, node in graph.items():
        if not isinstance(node, dict):
            continue
        ctype = node.get("class_type", "")
        inputs = node.get("inputs", {}) or {}
        # nur skalar-Felder (keine Node-Referenzen [id, slot]) als mapbar zeigen
        scalar_fields = [k for k, v in inputs.items() if not isinstance(v, list)]
        nodes.append({"id": node_id, "class_type": ctype, "inputs": scalar_fields})
        # Heuristik-Vorschlag
        if ctype in _HEURISTICS:
            field, param = _HEURISTICS[ctype]
            if field in inputs and param not in suggestions:
                suggestions[param] = f"{node_id}.inputs.{field}"

    return {"nodes": nodes, "suggestions": suggestions}
