"""OAuth-Login per GUI für ChatGPT Plus/Pro (Codex).

Zwei-Schritt-Flow ohne lokalen Callback-Server (für Remote-Server ohne SSH):

1. /oauth/start  → erzeugt PKCE-Verifier+State, persistiert in pending-File,
                    liefert authorize_url. User öffnet im Browser.
2. /oauth/exchange → User pasted die Redirect-URL (oder den Code) zurück.
                    Server tauscht gegen Token, schreibt OAuth-Block in
                    llm.json unter Provider-id "openai-codex".
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.oauth import openai_codex
from hydrahive.settings import settings

router = APIRouter(prefix="/api/llm/oauth", tags=["llm-oauth"])

PENDING_PATH = settings.oauth_pending_path
PENDING_TTL_SECONDS = 600  # 10 min — nach Login muss User in dem Zeitraum exchange aufrufen

CODEX_DEFAULT_MODELS = [
    "openai-codex/gpt-5.5",
    "openai-codex/gpt-5.4",
    "openai-codex/gpt-5.3-codex",
    "openai-codex/gpt-5.3-codex-spark",
    "openai-codex/gpt-5.2",
    "openai-codex/gpt-5.2-codex",
    "openai-codex/gpt-5.1",
    "openai-codex/gpt-5.1-codex-max",
    "openai-codex/gpt-5.1-codex-mini",
]


class StartRequest(BaseModel):
    provider: str  # nur "openai-codex" derzeit


class StartResponse(BaseModel):
    authorize_url: str
    state: str


class ExchangeRequest(BaseModel):
    provider: str
    code_or_url: str


class ExchangeResponse(BaseModel):
    ok: bool
    account_id: str


def _load_pending() -> dict:
    if not PENDING_PATH.exists():
        return {}
    try:
        return json.loads(PENDING_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def _save_pending(data: dict) -> None:
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    PENDING_PATH.write_text(json.dumps(data))
    PENDING_PATH.chmod(0o600)


def _delete_pending() -> None:
    if PENDING_PATH.exists():
        PENDING_PATH.unlink()


def _write_provider_oauth(oauth_block: dict) -> None:
    path = settings.llm_config
    if path.exists():
        data = json.loads(path.read_text())
    else:
        data = {"providers": [], "default_model": "", "embed_model": ""}
    providers = data.setdefault("providers", [])
    found = next((p for p in providers if p.get("id") == "openai-codex"), None)
    if found is None:
        found = {"id": "openai-codex", "name": "ChatGPT Plus/Pro (Codex)",
                 "api_key": "", "models": list(CODEX_DEFAULT_MODELS)}
        providers.append(found)
    found["oauth"] = oauth_block
    if not data.get("default_model") and found["models"]:
        data["default_model"] = found["models"][0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


@router.post("/start", dependencies=[Depends(require_admin)], response_model=StartResponse)
def oauth_start(req: StartRequest) -> StartResponse:
    if req.provider != "openai-codex":
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_unsupported_provider",
                    message=f"OAuth nicht unterstützt für Provider {req.provider}")
    verifier, challenge = openai_codex.make_pkce()
    state = openai_codex.make_state()
    _save_pending({
        "provider": req.provider,
        "verifier": verifier,
        "state": state,
        "ts": int(time.time()),
    })
    url = openai_codex.authorize_url(challenge=challenge, state=state)
    return StartResponse(authorize_url=url, state=state)


@router.post("/exchange", dependencies=[Depends(require_admin)], response_model=ExchangeResponse)
async def oauth_exchange(req: ExchangeRequest) -> ExchangeResponse:
    if req.provider != "openai-codex":
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_unsupported_provider",
                    message=f"OAuth nicht unterstützt für Provider {req.provider}")
    pending = _load_pending()
    if not pending or pending.get("provider") != req.provider:
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_no_pending",
                    message="Kein laufender OAuth-Flow — bitte erst Login starten")
    if int(time.time()) - int(pending.get("ts") or 0) > PENDING_TTL_SECONDS:
        _delete_pending()
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_expired",
                    message="OAuth-Flow abgelaufen — bitte neu starten")

    parsed = openai_codex.parse_callback_input(req.code_or_url)
    code = parsed.get("code", "")
    if not code:
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_no_code",
                    message="Kein Code im eingefügten Text gefunden")
    received_state = parsed.get("state", "")
    if received_state and received_state != pending.get("state"):
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_state_mismatch",
                    message="OAuth-State stimmt nicht überein — Flow neu starten")

    try:
        token = await openai_codex.exchange_code(code=code, verifier=pending["verifier"])
    except Exception as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_exchange_failed",
                    message=f"Token-Tausch fehlgeschlagen: {e}")

    if not token.get("access"):
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_no_access",
                    message="Token-Antwort ohne access_token")

    _write_provider_oauth(token)
    _delete_pending()
    return ExchangeResponse(ok=True, account_id=token.get("account_id", ""))


@router.delete("/{provider}", dependencies=[Depends(require_admin)])
def oauth_revoke(provider: str) -> dict:
    if provider != "openai-codex":
        raise coded(status.HTTP_400_BAD_REQUEST, "oauth_unsupported_provider",
                    message=f"OAuth nicht unterstützt für Provider {provider}")
    path = settings.llm_config
    if not path.exists():
        return {"ok": True}
    data = json.loads(path.read_text())
    for p in data.get("providers", []):
        if p.get("id") == provider:
            p.pop("oauth", None)
    path.write_text(json.dumps(data, indent=2))
    return {"ok": True}
