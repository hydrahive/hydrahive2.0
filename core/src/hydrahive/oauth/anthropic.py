"""Anthropic OAuth — Login mit Claude Pro/Max ohne API-Credits.

Endpoints + Client-ID übernommen von der Claude-Code-Identität (siehe
github.com/badlogic/pi-mono packages/ai/src/utils/oauth/anthropic.ts).

Flow:
  1. make_pkce()                               → verifier + challenge
  2. authorize_url(challenge, state)           → URL für den User-Browser
  3. User autorisiert auf claude.ai
  4. Browser wird zu localhost:53692/callback?code=…&state=… umgeleitet
     (Connection-Refused-Page — User kopiert URL oder Code-Param)
  5. exchange_code(code, verifier)             → Access + Refresh + ExpiresAt
  6. refresh_access_token(refresh_token)       → neuer Access-Token

Im Server-Setup wird kein lokaler Callback-Server gestartet — der manuelle
Code-Paste-Pfad reicht für headless / remote Installations.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

# Constants — passend zur Claude-Code-Identität
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
REDIRECT_URI = "http://localhost:53692/callback"
SCOPES = (
    "org:create_api_key user:profile user:inference "
    "user:sessions:claude_code user:mcp_servers user:file_upload"
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_pkce() -> tuple[str, str]:
    """PKCE: liefert (verifier, challenge) — challenge ist S256(verifier)."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def make_state() -> str:
    return _b64url(secrets.token_bytes(16))


def authorize_url(*, challenge: str, state: str) -> str:
    """Login-URL für den User-Browser. claude.ai zeigt die Authorize-Page."""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def parse_callback_input(value: str) -> dict[str, str]:
    """Akzeptiert eine Callback-URL ODER einen 'code#state'-String ODER nur den Code.

    Gibt {code, state?} zurück. State ist optional weil pi-ai/OpenClaw das
    auch akzeptieren wenn der User nur den Code-Param paste.
    """
    value = value.strip()
    if not value:
        return {}
    # Volle URL?
    try:
        parsed = urlparse(value)
        if parsed.scheme:
            qs = parse_qs(parsed.query)
            out: dict[str, str] = {}
            if "code" in qs:
                out["code"] = qs["code"][0]
            if "state" in qs:
                out["state"] = qs["state"][0]
            if out:
                return out
    except Exception:
        pass
    # 'code#state'-Format wie pi-ai
    if "#" in value:
        code, state = value.split("#", 1)
        return {"code": code, "state": state}
    # Reiner Query-String?
    if "code=" in value:
        qs = parse_qs(value)
        return {
            "code": qs.get("code", [""])[0],
            "state": qs.get("state", [""])[0],
        }
    # Nackter Code
    return {"code": value}


async def exchange_code(*, code: str, verifier: str, state: str | None = None) -> dict[str, Any]:
    """Tausch Authorization-Code gegen Access- + Refresh-Token.

    Antwort-Schema (sk-ant-oat-Token):
      { access_token, refresh_token, expires_in, token_type, scope, ... }

    Wir normalisieren auf das HH2-llm.json-OAuth-Schema:
      { access, refresh, expires_at (epoch s), scope }
    """
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
    }
    if state:
        body["state"] = state
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(TOKEN_URL, json=body)
        resp.raise_for_status()
        data = resp.json()
    return _normalize_token_response(data)


async def refresh_access_token(*, refresh_token: str) -> dict[str, Any]:
    """Holt einen neuen Access-Token mit dem Refresh-Token.

    Anthropic gibt einen NEUEN refresh_token zurück (rotation). Beide
    speichern. Bei 4xx → Token ist tot, User muss neu einloggen.
    """
    body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(TOKEN_URL, json=body)
        resp.raise_for_status()
        data = resp.json()
    return _normalize_token_response(data)


def _normalize_token_response(data: dict) -> dict[str, Any]:
    """Provider-Antwort → HH2-llm.json-OAuth-Schema."""
    expires_in = int(data.get("expires_in") or 3600)
    return {
        "access": data.get("access_token") or "",
        "refresh": data.get("refresh_token") or "",
        "expires_at": int(time.time()) + expires_in,
        "scope": data.get("scope") or SCOPES,
    }
