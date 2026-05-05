"""OAuth-Login-Routes für externe LLM-Provider.

Aktuell nur Anthropic. MiniMax + OpenAI Codex folgen.

Flow Anthropic:
  POST /api/oauth/anthropic/start
    → { authorize_url, state }   (verifier wird serverseitig im Memory gehalten)
  POST /api/oauth/anthropic/exchange { code_or_url }
    → tauscht Code → speichert OAuth-Block in llm.json → { ok, expires_at }

State-Store: in-memory mit 10 min TTL. Reicht für den Single-Server-Use-Case;
bei mehreren Instanzen müsste das in Redis o.ä.
"""
from __future__ import annotations

import json
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.oauth import anthropic as oauth_anthropic
from hydrahive.settings import settings

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

# in-memory state store: { state: (verifier, expires_at) }
_PENDING: dict[str, tuple[str, float]] = {}
_STATE_TTL = 600  # 10 min


def _gc_pending() -> None:
    now = time.time()
    for s in [k for k, (_, exp) in _PENDING.items() if exp < now]:
        _PENDING.pop(s, None)


def _save_oauth_to_llm_config(provider_id: str, oauth_block: dict) -> None:
    """Schreibt den OAuth-Block in llm.json beim passenden Provider.

    Idempotent: wenn Provider noch nicht existiert, wird er angelegt mit
    sinnvollen Defaults (Anthropic: claude-sonnet-4-6 als erstes Modell).
    """
    path = settings.llm_config
    if path.exists():
        data = json.loads(path.read_text())
    else:
        data = {"providers": [], "default_model": "", "embed_model": ""}
    providers = data.setdefault("providers", [])

    found = None
    for p in providers:
        if p.get("id") == provider_id:
            found = p
            break
    if found is None:
        defaults = {
            "anthropic": {
                "name": "Anthropic",
                "models": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5"],
            },
        }.get(provider_id, {"name": provider_id.title(), "models": []})
        found = {"id": provider_id, "name": defaults["name"], "api_key": "",
                 "models": defaults["models"]}
        providers.append(found)

    found["oauth"] = oauth_block
    if not data.get("default_model") and found["models"]:
        data["default_model"] = found["models"][0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


class StartResponse(BaseModel):
    authorize_url: str
    state: str


@router.post("/anthropic/start", response_model=StartResponse,
             dependencies=[Depends(require_admin)])
def anthropic_start() -> dict:
    _gc_pending()
    verifier, challenge = oauth_anthropic.make_pkce()
    state = oauth_anthropic.make_state()
    _PENDING[state] = (verifier, time.time() + _STATE_TTL)
    return {
        "authorize_url": oauth_anthropic.authorize_url(challenge=challenge, state=state),
        "state": state,
    }


class ExchangeRequest(BaseModel):
    code_or_url: str
    state: str | None = None


@router.post("/anthropic/exchange", dependencies=[Depends(require_admin)])
async def anthropic_exchange(req: ExchangeRequest) -> dict:
    _gc_pending()
    parsed = oauth_anthropic.parse_callback_input(req.code_or_url)
    code = parsed.get("code", "")
    if not code:
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_no_code",
                    message="Kein Authorization-Code erkannt")

    # State aus Eingabe ODER aus Body — mindestens einer muss matchen
    callback_state = parsed.get("state") or req.state
    if not callback_state or callback_state not in _PENDING:
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_state_invalid",
                    message="State unbekannt oder abgelaufen — Login erneut starten")
    verifier, _exp = _PENDING.pop(callback_state)

    try:
        token = await oauth_anthropic.exchange_code(
            code=code, verifier=verifier, state=callback_state)
    except httpx.HTTPStatusError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_exchange_failed",
                    message=f"Anthropic hat den Code abgelehnt: {e.response.text[:200]}")

    _save_oauth_to_llm_config("anthropic", token)
    return {"ok": True, "expires_at": token["expires_at"]}


@router.post("/anthropic/refresh", dependencies=[Depends(require_admin)])
async def anthropic_refresh() -> dict:
    """Manueller Refresh — normalerweise macht der Backend-LLM-Call das automatisch."""
    path = settings.llm_config
    if not path.exists():
        raise coded(status.HTTP_404_NOT_FOUND, "no_config")
    data = json.loads(path.read_text())
    for p in data.get("providers", []):
        if p.get("id") == "anthropic":
            oauth = p.get("oauth") or {}
            refresh = oauth.get("refresh", "")
            if not refresh:
                raise coded(status.HTTP_400_BAD_REQUEST, "no_refresh_token",
                            message="Kein Refresh-Token — bitte neu einloggen")
            try:
                new_token = await oauth_anthropic.refresh_access_token(refresh_token=refresh)
            except httpx.HTTPStatusError as e:
                raise coded(status.HTTP_400_BAD_REQUEST, "refresh_failed",
                            message=f"Refresh fehlgeschlagen: {e.response.text[:200]}")
            _save_oauth_to_llm_config("anthropic", new_token)
            return {"ok": True, "expires_at": new_token["expires_at"]}
    raise coded(status.HTTP_404_NOT_FOUND, "anthropic_not_configured")
