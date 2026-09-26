"""Embedding-Aufrufe und technische Metadaten.

Welche Modelle angeboten werden, entscheidet der Live-Modellkatalog. Die Tabelle in
diesem Modul enthält nur bekannte Dimensionen und Provider-spezifisches Routing.
Provider mit api_base nutzen den OpenAI-kompatiblen Client direkt.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.llm._embed_models import (
    _BY_MODEL,
    _PROVIDER_BY_MODEL as _PROVIDER_BY_MODEL,
    _PROVIDER_PREFIXES,
    _provider_and_api_model,
    dim_for_model,
    litellm_model,
    register_model_dimension,
)

logger = logging.getLogger(__name__)


async def aembed(text: str, model: str, embed_type: str = "db") -> list[float] | None:
    """Erzeugt einen Embedding-Vektor. embed_type: 'db' für Dokumente, 'query' für Suchanfragen."""
    results = await aembed_batch([text], model, embed_type=embed_type)
    return results[0] if results else None


async def ensure_model_dimension(model: str) -> int:
    """Ermittelt eine unbekannte Dimension einmalig durch einen echten Probevektor."""
    known = dim_for_model(model)
    if known:
        return known
    vector = await aembed("HydraHive embedding dimension probe", model, embed_type="query")
    if not vector:
        raise RuntimeError(f"Embedding-Modell {model!r} lieferte keinen Probevektor")
    register_model_dimension(model, len(vector))
    return len(vector)


def _is_rate_limit(e: Exception) -> bool:
    msg = str(e).lower()
    return "rate limit" in msg or "ratelimit" in msg or "429" in msg or "too many" in msg


async def aembed_batch(texts: list[str], model: str, embed_type: str = "db", _retry: int = 3) -> list[list[float] | None]:
    """Bettet mehrere Texte in einem einzigen API-Call ein.

    embed_type: 'db' für Dokumente (Backfill), 'query' für Suchanfragen.
    MiniMax und NVIDIA nutzen asymmetrische Embeddings — falscher Typ senkt Suchqualität.
    Provider mit api_base nutzen den openai-Client direkt.
    Bei Rate-Limit-Fehlern: bis zu _retry Versuche mit 60s Pause.
    """
    from hydrahive.llm._config import apply_keys, get_provider_key, load_config
    if not texts:
        return []
    for attempt in range(1, _retry + 1):
        try:
            entry = _BY_MODEL.get(model, {})
            config = load_config()
            provider, api_model = _provider_and_api_model(model)
            if not entry and provider in _PROVIDER_PREFIXES:
                p = next((x for x in config.get("providers", []) if x.get("id") == provider), {})
                base = str(p.get("api_base") or "").rstrip("/")
                if provider == "ollama" and base and not base.endswith("/v1"):
                    base += "/v1"
                base = base or {
                    "openai": "https://api.openai.com/v1",
                    "nvidia": "https://integrate.api.nvidia.com/v1",
                    "openrouter": "https://openrouter.ai/api/v1",
                }.get(provider, "")
                entry = {"api_base": base} if base else {}

            if entry.get("api_base"):
                key = get_provider_key(config, provider)

                if provider == "minimax":
                    from hydrahive.llm._config import get_provider_group_id
                    api_model = model.split("/", 1)[-1] if "/" in model else model
                    group_id = get_provider_group_id(config, "minimax")
                    url = f"{entry['api_base']}/embeddings"
                    if group_id:
                        url += f"?GroupId={group_id}"
                    import httpx
                    async with httpx.AsyncClient(timeout=60) as hc:
                        r = await hc.post(
                            url,
                            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                            json={"model": api_model, "texts": texts, "type": embed_type},
                        )
                        r.raise_for_status()
                        data = r.json()
                        if data.get("base_resp", {}).get("status_code", 0) != 0:
                            raise RuntimeError(data["base_resp"].get("status_msg", "MiniMax Fehler"))
                        return [list(v) for v in data["vectors"]]

                import openai
                client = openai.AsyncOpenAI(api_key=key or "ollama", base_url=entry["api_base"])
                # NVIDIA NIM: input_type "passage"/"query" für asymmetrische Embeddings
                extra = {"input_type": "query" if embed_type == "query" else "passage"} if provider == "nvidia" else {}
                resp = await asyncio.wait_for(
                    client.embeddings.create(model=api_model, input=texts, extra_body=extra or None),
                    timeout=30,
                )
                ordered = sorted(resp.data, key=lambda d: d.index)
                return [list(d.embedding) for d in ordered]
            else:
                import litellm
                apply_keys(config)
                resp = await asyncio.wait_for(
                    litellm.aembedding(model=litellm_model(model), input=texts),
                    timeout=30,
                )
                return [d["embedding"] for d in resp.data]
        except Exception as e:
            if _is_rate_limit(e) and attempt < _retry:
                wait = 60 * attempt
                logger.warning("Rate-Limit (model=%s, n=%d, Versuch %d/%d) — warte %ds", model, len(texts), attempt, _retry, wait)
                await asyncio.sleep(wait)
                continue
            logger.warning("Batch-Embedding fehlgeschlagen (model=%s, n=%d): %s", model, len(texts), e)
            return [None] * len(texts)
    return [None] * len(texts)
