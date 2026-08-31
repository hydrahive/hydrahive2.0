"""Native Ollama API client for model inventory and metadata."""
from __future__ import annotations

import asyncio
from urllib.parse import urlsplit, urlunsplit

import httpx

from hydrahive.llm.ollama_common import normalize_model_name

_MAX_RESPONSE_BYTES = 10_000_000


class OllamaUnavailable(RuntimeError):
    pass


class OllamaModelNotFound(RuntimeError):
    pass


def normalized_base_url(provider: dict) -> str:
    raw = str(provider.get("api_base") or "").strip().rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
        raise OllamaUnavailable("ollama_not_configured")
    path = parsed.path
    if path.endswith("/v1"):
        path = path[:-3]
    return urlunsplit((parsed.scheme, parsed.netloc, path.rstrip("/"), "", ""))


def auth_headers(provider: dict) -> dict[str, str]:
    key = str(provider.get("api_key") or "")
    return {"Authorization": f"Bearer {key}"} if key else {}


def parse_tags_response(data: dict) -> list[dict]:
    rows: list[dict] = []
    for raw in data.get("models") or []:
        try:
            name = normalize_model_name(str(raw.get("name") or raw.get("model") or ""))
        except ValueError:
            continue
        details = raw.get("details") or {}
        rows.append({
            "id": f"ollama/{name}",
            "ollama_name": name,
            "installed": True,
            "size": raw.get("size"),
            "digest": raw.get("digest") or "",
            "modified_at": raw.get("modified_at"),
            "family": details.get("family") or name.split(":", 1)[0],
            "parameter_size": details.get("parameter_size") or None,
            "quantization": details.get("quantization_level") or None,
            "context_window": None,
            "capabilities": [],
            "input_modalities": [],
            "output_modalities": [],
        })
    return rows


def parse_show_response(data: dict) -> dict:
    info = data.get("model_info") or {}
    context = next(
        (value for key, value in info.items() if key.endswith(".context_length") and isinstance(value, int)),
        None,
    )
    capabilities = sorted({str(x).lower() for x in (data.get("capabilities") or []) if isinstance(x, str)})
    inputs = ["text"] if "completion" in capabilities or "tools" in capabilities or "thinking" in capabilities else []
    if "vision" in capabilities:
        inputs.append("image")
    if "audio" in capabilities:
        inputs.append("audio")
    outputs = ["embedding"] if any(x in capabilities for x in ("embedding", "embed")) else ["text"]
    return {
        "context_window": context,
        "capabilities": capabilities,
        "input_modalities": inputs,
        "output_modalities": outputs,
    }


async def _json(response: httpx.Response) -> dict:
    if len(response.content) > _MAX_RESPONSE_BYTES:
        raise OllamaUnavailable("ollama_response_too_large")
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise OllamaUnavailable("ollama_invalid_response")
    return data


async def list_installed(provider: dict) -> list[dict]:
    base = normalized_base_url(provider)
    headers = auth_headers(provider)
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            tags = await _json(await client.get(f"{base}/api/tags", headers=headers))
            rows = parse_tags_response(tags)

            async def enrich(row: dict) -> None:
                try:
                    response = await client.post(
                        f"{base}/api/show",
                        headers=headers,
                        json={"model": row["ollama_name"]},
                    )
                    row.update(parse_show_response(await _json(response)))
                except Exception:
                    return

            await asyncio.gather(*(enrich(row) for row in rows))
            return rows
    except OllamaUnavailable:
        raise
    except Exception as exc:
        raise OllamaUnavailable("ollama_unreachable") from exc


async def delete_model(provider: dict, model: str) -> None:
    base = normalized_base_url(provider)
    name = normalize_model_name(model)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.request(
                "DELETE",
                f"{base}/api/delete",
                headers=auth_headers(provider),
                json={"model": name},
            )
            if response.status_code == 404:
                raise OllamaModelNotFound(name)
            await _json(response)
    except (OllamaModelNotFound, OllamaUnavailable):
        raise
    except Exception as exc:
        raise OllamaUnavailable("ollama_unreachable") from exc
