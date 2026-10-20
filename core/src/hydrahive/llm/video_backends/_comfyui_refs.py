"""Mehrere Vorlagen für ComfyUI-Bild-Workflows (Nachtrag 19.10.2026, docs/specs/local-video-backends.md).

Platzhalter `reference_1..N` adressieren je ein `LoadImage.inputs.image`. `reference_links.reference_N` nennt den
Eingang, der Vorlage N in den Graph einspeist; fehlt die Vorlage, wird er entfernt (der Graph läuft ohne sie).
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import httpx

logger = logging.getLogger(__name__)

REF_PREFIX = "reference_"
Upload = Callable[[httpx.AsyncClient, str, str, str], Awaitable[str]]


def reference_slots(placeholders: dict) -> list[str]:
    """Vorlagen-Platzhalter des Workflows in Reihenfolge: reference_1, reference_2, …"""
    keys = [k for k in (placeholders or {}) if k.startswith(REF_PREFIX) and k[len(REF_PREFIX):].isdigit()]
    return sorted(keys, key=lambda k: int(k[len(REF_PREFIX):]))


def unlink_unused(graph: dict, links: dict, used: set[str]) -> dict:
    """Entfernt die Eingänge (reference_links) der Vorlagen, die es nicht gibt – der Graph läuft ohne sie."""
    for key, addr in (links or {}).items():
        if key in used or not isinstance(addr, str):
            continue
        parts = addr.split(".")
        node = graph.get(parts[0]) if len(parts) == 3 and parts[1] == "inputs" else None
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
            logger.warning("ComfyUI: ungültige Vorlagen-Verbindung '%s' (key=%s)", addr, key)
            continue
        node["inputs"].pop(parts[2], None)
    return graph


async def upload_references(client: httpx.AsyncClient, base: str, wf: dict, refs: list[str], upload: Upload) -> dict[str, str]:
    """Lädt die Vorlagen in die Plätze reference_1..N des Workflows; überzählige werden ignoriert."""
    slots = reference_slots(wf.get("placeholders") or {})
    if len(refs) > len(slots):
        logger.info("ComfyUI: %d Vorlagen, Workflow '%s' nimmt %d – Rest ignoriert", len(refs), wf.get("id"), len(slots))
    return {slot: await upload(client, base, ref, slot) for slot, ref in zip(slots, refs)}


# Knoten zwischen LoadImage und ReferenceLatent, die das Bild nur durchreichen (Skalieren, Kodieren)
_PASS = {"ImageScaleToTotalPixels", "ImageScale", "ImageScaleBy", "FluxKontextImageScale", "VAEEncode"}


def _feeds(graph: dict, src: str) -> list[tuple[str, str]]:
    """(Knoten, Feld), die den Ausgang von `src` als Eingang nehmen."""
    return [(nid, f) for nid, n in graph.items() if isinstance(n, dict)
            for f, v in (n.get("inputs") or {}).items() if isinstance(v, list) and v[:1] == [src]]


def suggest_references(graph: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Admin-Konsole: LoadImage-Knoten, deren Bild (über Skalieren/Kodieren) in ein ReferenceLatent fließt, werden
    zu reference_1..N (Reihenfolge = Kette der ReferenceLatent vom Text aus) samt Eingang für reference_links."""
    found: list[tuple[str, str, str]] = []                # (LoadImage, ReferenceLatent, Feld)
    for nid, n in graph.items():
        if not (isinstance(n, dict) and n.get("class_type") == "LoadImage"):
            continue
        todo, seen = [nid], set()
        while todo:
            cur = todo.pop()
            for tgt, field in _feeds(graph, cur):
                ctype = (graph.get(tgt) or {}).get("class_type")
                if ctype == "ReferenceLatent" and field == "latent":
                    found.append((nid, tgt, field))
                elif ctype in _PASS and tgt not in seen:
                    seen.add(tgt)
                    todo.append(tgt)
    depth = {}

    def _depth(rid: str) -> int:                          # wie viele ReferenceLatent vor diesem in der Kette
        if rid not in depth:
            prev = ((graph.get(rid) or {}).get("inputs") or {}).get("conditioning")
            depth[rid] = 0
            if isinstance(prev, list) and (graph.get(prev[0]) or {}).get("class_type") == "ReferenceLatent":
                depth[rid] = _depth(prev[0]) + 1
        return depth[rid]

    found.sort(key=lambda x: (_depth(x[1]), x[0]))
    slots, links = {}, {}
    for i, (img, ref, field) in enumerate(found, start=1):
        slots[f"{REF_PREFIX}{i}"] = f"{img}.inputs.image"
        links[f"{REF_PREFIX}{i}"] = f"{ref}.inputs.{field}"
    return slots, links
