"""Read-only adapter for the official Ollama model library."""
from __future__ import annotations

import asyncio
import html
import re
import time

import httpx

from hydrahive.llm.ollama_common import validate_family_name

_LIBRARY_URL = "https://ollama.com/library"
_CACHE_TTL = 900
_MAX_BYTES = 5_000_000
_CAPABILITIES = {"tools", "thinking", "vision", "embedding", "audio"}
_cache: dict[str, tuple[float, list[dict]]] = {}
_lock = asyncio.Lock()


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_library_families(document: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for block in re.findall(r"<li\b[^>]*>.*?</li>", document, re.DOTALL | re.IGNORECASE):
        match = re.search(r'href="/library/([a-z0-9._-]+)"', block)
        if not match or match.group(1) in seen:
            continue
        name = match.group(1)
        seen.add(name)
        desc_match = re.search(r'<p\b[^>]*class="[^"]*text-md[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL)
        description = _text(desc_match.group(1)) if desc_match else ""
        badges = [
            _text(value).lower()
            for value in re.findall(r'<span\b[^>]*class="[^"]*bg-indigo-50[^"]*"[^>]*>(.*?)</span>', block, re.DOTALL)
        ]
        params = [
            _text(value).lower()
            for value in re.findall(r'<span\b[^>]*class="[^"]*bg-\[#ddf4ff\][^"]*"[^>]*>(.*?)</span>', block, re.DOTALL)
        ]
        rows.append({
            "name": name,
            "description": description,
            "capabilities": sorted({x for x in badges if x in _CAPABILITIES}),
            "parameter_sizes": list(dict.fromkeys(x for x in params if x)),
        })
    return rows


def _metric(value: str, *, bytes_value: bool = False) -> int | None:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([KMGT])?B?", value.strip(), re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1))
    suffix = (match.group(2) or "").upper()
    power = {"": 0, "K": 1, "M": 2, "G": 3, "T": 4}[suffix]
    base = 1000 if bytes_value or suffix else 1
    return int(number * (base ** power))


def parse_library_tags(family: str, document: str) -> list[dict]:
    family = validate_family_name(family)
    pattern = rf'<a\b[^>]*href="/library/({re.escape(family)}:[^"/]+)"[^>]*class="[^"]*sm:hidden[^"]*"[^>]*>(.*?)</a>'
    rows: list[dict] = []
    seen: set[str] = set()
    for name, block in re.findall(pattern, document, re.DOTALL | re.IGNORECASE):
        if name in seen:
            continue
        seen.add(name)
        meta_matches = re.findall(r'<p\b[^>]*class="[^"]*text-neutral-500[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL)
        parts = [_text(x) for x in meta_matches[-1].split("·")] if meta_matches else []
        size = _metric(parts[0], bytes_value=True) if parts else None
        context = None
        if len(parts) > 1:
            context = _metric(parts[1].replace("context window", "").strip())
        modalities = []
        if len(parts) > 2:
            modalities = [x.strip().lower() for x in parts[2].split(",") if x.strip()]
        rows.append({
            "name": name,
            "size": size,
            "context_window": context,
            "input_modalities": modalities,
        })
    return rows


async def _fetch(url: str) -> str:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.get(url, headers={"Accept": "text/html", "User-Agent": "HydraHive/2"})
        response.raise_for_status()
        if len(response.content) > _MAX_BYTES:
            raise ValueError("ollama_library_response_too_large")
        return response.text


async def _cached(key: str, loader) -> list[dict]:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < _CACHE_TTL:
        return hit[1]
    async with _lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]
        rows = await loader()
        _cache[key] = (time.monotonic(), rows)
        return rows


async def list_families() -> list[dict]:
    async def load() -> list[dict]:
        return parse_library_families(await _fetch(_LIBRARY_URL))

    return await _cached("families", load)


async def list_tags(family: str) -> list[dict]:
    family = validate_family_name(family)

    async def load() -> list[dict]:
        return parse_library_tags(family, await _fetch(f"{_LIBRARY_URL}/{family}"))

    return await _cached(f"tags:{family}", load)
