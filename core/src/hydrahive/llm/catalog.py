"""LLM-Modell-Catalog: Live-Listing pro Provider + interne Metadata.

Per Provider hat HH2 eine Liste der gepflegten Metadata (context_window,
tool_use, category, params, hint). Beim Catalog-Aufruf wird live von der
Provider-API die Modell-Liste geholt und mit dieser Metadata gejoint.

Modelle die live verfügbar sind aber nicht in der Metadata stehen, kommen
trotzdem in die Liste — mit `metadata.unknown=True`.

Daten (Provider-Endpoints, Static-Listen, Metadata) liegen in
`_catalog_data.py`; dieses Modul enthält nur die Logik.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

import httpx

from hydrahive.llm._catalog_data import (
    METADATA,
    PROVIDER_ENDPOINTS,
    PROVIDER_PREFIX,
    STATIC_MODELS,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 Minuten (Hermes-Muster)
_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_locks: dict[str, asyncio.Lock] = {}


def _cache_clear() -> None:
    _cache.clear()
    _cache_locks.clear()


def _credential_cache_key(provider_id: str, credential: str) -> str:
    """Isoliert Provider-Listings pro Credential, ohne Tokens im Cache abzulegen."""
    digest = hashlib.sha256(credential.encode()).hexdigest()[:16]
    return f"{provider_id}:{digest}"


async def _cached_fetch(provider_id: str, api_key: str) -> list[dict]:
    """Live-Fetch mit 5-Min-TTL-Cache + Lock gegen parallele Fetches."""
    cache_key = _credential_cache_key(provider_id, api_key)
    now = time.monotonic()
    hit = _cache.get(cache_key)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    lock = _cache_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        hit = _cache.get(cache_key)  # zweiter Check nach Lock
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]
        entries = await _fetch_live_models(provider_id, api_key)
        if entries:  # nur erfolgreiche Fetches cachen
            _cache[cache_key] = (time.monotonic(), entries)
        return entries


def _normalize_id(provider_id: str, raw_id: str) -> str:
    """Live-API gibt 'meta/llama-...' — wir schreiben 'nvidia_nim/meta/llama-...'."""
    prefix = PROVIDER_PREFIX.get(provider_id, "")
    if prefix and not raw_id.startswith(prefix):
        return prefix + raw_id
    return raw_id


def _parse_models_response(provider_id: str, data: dict) -> list[dict]:
    """Extrahiert strukturierte Modell-Einträge aus Provider-Katalogantworten.

    OpenAI-kompatible Provider liefern ``data[].id``. Gemini liefert
    ``models[].name``. Der Codex-Endpoint liefert ``models[].slug`` und
    ``context_window`` sowie Sichtbarkeit/Tool-Metadaten.
    """
    raw: list[dict]
    if isinstance(data.get("data"), list):
        raw = data["data"]
    elif isinstance(data.get("models"), list):
        raw = []
        for model in data["models"]:
            if not isinstance(model, dict):
                continue
            # Codex liefert nur für den aktuellen Account sichtbare Modelle;
            # versteckte/aus der API entfernte Modelle gehören nicht in Picker.
            if provider_id == "openai-codex" and (
                model.get("visibility") not in (None, "list")
                or model.get("supported_in_api") is False
            ):
                continue
            item = dict(model)
            item["id"] = (model.get("slug") or model.get("name", "")).replace("models/", "")
            if "context_length" not in item:
                item["context_length"] = model.get("context_window")
            raw.append(item)
    else:
        raw = []

    out: list[dict] = []
    for m in raw:
        mid = m.get("id", "")
        if not mid:
            continue
        pricing = m.get("pricing") or {}
        prompt = pricing.get("prompt")
        completion = pricing.get("completion")
        is_free: bool | None
        if prompt is None and completion is None:
            is_free = None
        else:
            is_free = (str(prompt) == "0" and str(completion) == "0")
        arch = m.get("architecture") or {}
        tool_use = m.get("tool_use")
        if tool_use is None and provider_id == "openai-codex":
            tool_use = bool(m.get("tool_mode") or m.get("experimental_supported_tools"))
        out.append({
            "id": _normalize_id(provider_id, mid),
            "context_window": m.get("context_length"),
            "is_free": is_free,
            "price_prompt": prompt,
            "price_completion": completion,
            "output_modalities": arch.get("output_modalities") or [],
            "input_modalities": arch.get("input_modalities") or [],
            "tool_use": tool_use,
        })
    return out


def _auth_for(cfg: dict, api_key: str) -> tuple[dict, dict]:
    """Gibt (headers, params) für den Provider-Auth-Modus zurück."""
    kind = cfg.get("auth")
    if kind == "bearer":
        return {"Authorization": f"Bearer {api_key}"}, {}
    if kind == "query":
        return {}, {cfg.get("query_param", "key"): api_key}
    if kind == "x-api-key":  # Anthropic: API-Key oder Claude-Code-OAuth-Token
        if api_key.startswith("sk-ant-oat"):
            from hydrahive.llm._anthropic import _OAUTH_HEADERS
            return {
                "Authorization": f"Bearer {api_key}",
                "anthropic-version": "2023-06-01",
                **_OAUTH_HEADERS,
            }, {}
        return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}, {}
    return {}, {}


async def _fetch_live_models(
    provider_id: str,
    api_key: str,
    *,
    extra_headers: dict[str, str] | None = None,
    extra_params: dict[str, str] | None = None,
) -> list[dict]:
    """Holt strukturierte Modell-Einträge live. Bei Fehler: leere Liste."""
    cfg = PROVIDER_ENDPOINTS.get(provider_id, {})
    url = cfg.get("url")
    if not url or not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers, params = _auth_for(cfg, api_key)
            headers.update(extra_headers or {})
            params.update(extra_params or {})
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        return _parse_models_response(provider_id, data)
    except Exception as e:
        logger.warning("Catalog: live-fetch für %s fehlgeschlagen: %s", provider_id, e)
        return []


async def _fetch_codex_live_models(provider: dict, access_token: str) -> list[dict]:
    """Holt den account-spezifischen Codex-Katalog vom ChatGPT-Backend.

    Der Endpoint ist OpenAI-kompatibel, benötigt für ChatGPT OAuth aber zusätzlich
    die Account-ID und den Codex-Client-Kontext. Ohne Account-ID fällt der Aufrufer
    bewusst auf STATIC_MODELS zurück.
    """
    oauth = provider.get("oauth") or {}
    account_id = oauth.get("account_id", "") or ""
    if not account_id:
        return []
    return await _fetch_live_models(
        "openai-codex",
        access_token,
        extra_headers={
            "chatgpt-account-id": account_id,
            "OpenAI-Beta": "responses=experimental",
            "originator": "hydrahive",
            "User-Agent": "codex_cli_rs/0.55.0",
        },
        extra_params={"client_version": "2.0.0"},
    )


async def _cached_fetch_codex(provider: dict, access_token: str) -> list[dict]:
    """Cached Codex-Live-Fetch mit OAuth-Account-Kontext."""
    cache_key = _credential_cache_key("openai-codex", access_token)
    now = time.monotonic()
    hit = _cache.get(cache_key)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    lock = _cache_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        hit = _cache.get(cache_key)
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]
        entries = await _fetch_codex_live_models(provider, access_token)
        if entries:
            _cache[cache_key] = (time.monotonic(), entries)
        return entries


async def _fetch_ollama_models(provider: dict) -> list[dict]:
    """Holt Ollama-Modelle live vom user-eigenen Endpoint (OpenAI-kompatibel).

    Anders als die Cloud-Provider kommt die Base-URL aus der llm.json (`api_base`),
    nicht aus PROVIDER_ENDPOINTS. Ollama braucht lokal keinen Key; ein optionaler
    Key (Ollama-Cloud) wird als Bearer mitgegeben. Bei Fehler: leere Liste."""
    base = (provider.get("api_base") or "").rstrip("/")
    if not base:
        return []
    key = provider.get("api_key", "") or ""
    url = f"{base}/v1/models"
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            entries = _parse_models_response("ollama", data)
            # Ollamas OpenAI-/v1/models liefert weder context_length noch die
            # Tool-Capability. Beides steht nur im nativen /api/show. Ohne diese
            # Anreicherung landet jedes Modell mit context_window=None im Catalog
            # (-> falsche Compaction-Rechnung -> Dauer-Compact) und tool_use=None.
            await _enrich_ollama_from_show(client, base, headers, entries)
        return entries
    except Exception as e:
        logger.warning("Catalog: Ollama live-fetch (%s) fehlgeschlagen: %s", url, e)
        return []


def _ollama_bare_name(entry_id: str) -> str:
    """'ollama/qwen3:14b' -> 'qwen3:14b' (Name den /api/show erwartet)."""
    return entry_id.split("/", 1)[1] if entry_id.startswith("ollama/") else entry_id


def _parse_ollama_show(data: dict) -> tuple[int | None, bool | None]:
    """Zieht (context_window, tool_use) aus einer /api/show-Antwort.

    context_length steht unter model_info["<arch>.context_length"] (der
    Architektur-Prefix variiert: 'qwen3.', 'llama.', 'gemma3.' …), deshalb
    suchen wir per Suffix. tool_use kommt aus capabilities (enthält "tools").
    """
    info = data.get("model_info") or {}
    ctx: int | None = None
    for k, v in info.items():
        if k.endswith(".context_length") and isinstance(v, int):
            ctx = v
            break
    caps = data.get("capabilities")
    tool_use: bool | None = None
    if isinstance(caps, list):
        tool_use = "tools" in caps
    return ctx, tool_use


def _ollama_embedding_dim(data: dict) -> int | None:
    """Liest die native Ausgabedimension aus Ollamas model_info."""
    info = data.get("model_info") or {}
    return next(
        (v for k, v in info.items() if k.endswith(".embedding_length") and isinstance(v, int) and v > 0),
        None,
    )


async def _enrich_ollama_from_show(client, base, headers, entries: list[dict]) -> None:
    """Reichert jeden Ollama-Eintrag in-place mit /api/show-Daten an.

    Fehler pro Modell werden geschluckt (context_window bleibt dann None) —
    ein einzelnes kaputtes Modell darf nicht die ganze Liste killen.
    """
    show_url = f"{base}/api/show"

    async def one(entry: dict) -> None:
        try:
            r = await client.post(
                show_url, json={"model": _ollama_bare_name(entry["id"])},
                headers=headers,
            )
            r.raise_for_status()
            show = r.json()
            ctx, tool_use = _parse_ollama_show(show)
        except Exception as e:  # noqa: BLE001 - best effort pro Modell
            logger.debug("Catalog: /api/show für %s fehlgeschlagen: %s", entry.get("id"), e)
            return
        if ctx:
            entry["context_window"] = ctx
        if tool_use is not None:
            entry["tool_use"] = tool_use
        # Native Ollama /api/show exposes embedding capability, while /v1/models
        # usually does not. Preserve it for registry modality classification.
        capabilities = {str(x).lower() for x in (show.get("capabilities") or [])}
        if "embedding" in capabilities or "embed" in capabilities:
            entry["output_modalities"] = ["embedding"]
            entry["embed_dim"] = _ollama_embedding_dim(show)

    await asyncio.gather(*(one(e) for e in entries))


def _enrich(provider_id: str, entry: dict) -> dict[str, Any]:
    """Joint Live-Eintrag mit METADATA. Live-context_window hat Vorrang."""
    from hydrahive.llm._anthropic import _uses_effort_param
    md = METADATA.get(entry["id"], {})
    model_id = entry["id"].lower()
    inferred_category = "embed" if any(token in model_id for token in ("embed", "embedding")) else "chat"
    category = entry.get("category") or md.get("category") or inferred_category
    result_id = entry["id"]
    if provider_id == "minimax" and category == "embed" and not result_id.startswith("minimax/"):
        result_id = f"minimax/{result_id}"
    return {
        "id": result_id,
        "context_window": entry.get("context_window") or md.get("context_window"),
        # Live-tool_use (z.B. aus Ollama /api/show capabilities) hat Vorrang vor
        # der statischen METADATA. `entry.get("tool_use")` kann True/False/None
        # sein — nur wenn es None ist, auf METADATA zurückfallen.
        "tool_use": entry["tool_use"] if entry.get("tool_use") is not None else md.get("tool_use"),
        "category": category,
        "family": md.get("family", "?"),
        "is_free": entry.get("is_free"),
        "price_prompt": entry.get("price_prompt"),
        "price_completion": entry.get("price_completion"),
        "output_modalities": entry.get("output_modalities") or [],
        "input_modalities": entry.get("input_modalities") or [],
        "embed_dim": entry.get("embed_dim") or md.get("embed_dim"),
        "supports_effort": _uses_effort_param(entry["id"]),
        "unknown": entry["id"] not in METADATA,
    }


def _catalog_credentials(provider: dict) -> list[str]:
    """Credentials in sicherer Retry-Reihenfolge, ohne sie zu persistieren.

    Für Anthropic wird ein noch gültiger OAuth-Token bevorzugt. Ist er abgelaufen,
    kommt ein paralleler API-Key zuerst. Der zweite Credential bleibt als einmaliger
    Fallback erhalten, falls der bevorzugte widerrufen wurde.
    """
    api_key = provider.get("api_key", "") or ""
    oauth = provider.get("oauth") or {}
    access = oauth.get("access", "") or ""
    if provider.get("id") != "anthropic":
        return [key for key in (api_key or access,) if key]

    expires_at = int(oauth.get("expires_at") or 0)
    oauth_current = bool(access) and (expires_at == 0 or expires_at > time.time())
    ordered = (access, api_key) if oauth_current else (api_key, access)
    return list(dict.fromkeys(key for key in ordered if key))


async def catalog_for_providers(providers: list[dict]) -> list[dict]:
    """Erzeugt Catalog-Einträge pro konfiguriertem Provider parallel.

    `providers` ist die Liste aus llm.json (jeweils {id, api_key, oauth, ...}).
    """
    async def one(p: dict) -> dict:
        pid = p.get("id", "")
        # Ollama: user-eigener Endpoint. api_base statt Cloud-URL, kein Key nötig.
        if pid == "ollama":
            entries = await _fetch_ollama_models(p)
            models = [_enrich(pid, e) for e in entries]
            return {
                "provider_id": pid,
                "provider_name": p.get("name", pid),
                "configured": bool(p.get("api_base")),
                "models": models,
                "live_count": len(entries),
            }
        credentials = _catalog_credentials(p)
        entries: list[dict] = []
        for credential in credentials:
            if pid == "openai-codex":
                entries = await _cached_fetch_codex(p, credential)
            else:
                entries = await _cached_fetch(pid, credential)
            if entries:
                break
        live_count = len(entries)
        if not entries:
            entries = [{"id": _normalize_id(pid, m), "context_window": None,
                        "is_free": None, "price_prompt": None, "price_completion": None}
                       for m in STATIC_MODELS.get(pid, [])]
        # ProviderForm erlaubt bewusst benutzerdefinierte Modell-IDs. Sie müssen
        # auch bei einem fehlenden/verkürzten Live-Katalog in den Pickern bleiben
        # (z.B. Codex OAuth oder ein neuer DeepSeek-NIM-Slug).
        known = {str(e.get("id")) for e in entries}
        for model in p.get("models", []) or []:
            model_id = _normalize_id(pid, str(model).strip())
            if model_id and model_id not in known:
                entries.append({"id": model_id, "context_window": None,
                                "is_free": None, "price_prompt": None,
                                "price_completion": None})
                known.add(model_id)
        models = [_enrich(pid, e) for e in entries]
        return {
            "provider_id": pid,
            "provider_name": p.get("name", pid),
            "configured": bool(credentials),
            "models": models,
            "live_count": live_count,
        }
    return await asyncio.gather(*[one(p) for p in providers])
