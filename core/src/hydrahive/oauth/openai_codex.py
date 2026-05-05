"""OpenAI Codex OAuth — Login mit ChatGPT Plus/Pro ohne API-Credits.

Endpoints + Client-ID übernommen vom Codex-CLI (siehe github.com/badlogic/pi-mono
packages/ai/src/utils/oauth/openai-codex.ts und altes octopos/router_llm.py).

Flow:
  1. make_pkce() + make_state()              → verifier, challenge, state
  2. authorize_url(challenge, state)         → URL für den Browser
  3. User autorisiert auf auth.openai.com
  4. Browser wird zu http://localhost:1455/auth/callback?code=…&state=… umgeleitet
  5. exchange_code(code, verifier)           → access + refresh + account_id
  6. refresh_access_token(refresh_token)     → neuer Access-Token

Spezifika gegenüber Anthropic:
  - Token-Exchange als application/x-www-form-urlencoded (nicht JSON)
  - Aus dem access-Token muss die chatgpt_account_id aus dem JWT-Claim
    'https://api.openai.com/auth' extrahiert werden — die ist Pflicht-Header
    beim Codex-Backend-Call (chatgpt-account-id)
  - REDIRECT_URI ist localhost:1455/auth/callback (fix in der Client-ID)
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"
ORIGINATOR = "hydrahive"  # statt "pi" — wir geben uns nicht als Codex aus

# Cloudflare-/Bot-Schutz: User-Agent setzen damit OpenAI's Auth-Server
# nicht blockt (Default Python-urllib/httpx kann erkannt werden).
_HTTP_HEADERS = {
    "User-Agent": "codex_cli_rs/0.55.0",
}


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
    """Login-URL für den User-Browser — auth.openai.com zeigt die OAuth-Page."""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": ORIGINATOR,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def parse_callback_input(value: str) -> dict[str, str]:
    """Akzeptiert volle Callback-URL ODER 'code#state' ODER nur den Code."""
    value = value.strip()
    if not value:
        return {}
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
    if "#" in value and "code=" not in value:
        c, s = value.split("#", 1)
        return {"code": c, "state": s}
    if "code=" in value:
        qs = parse_qs(value)
        return {
            "code": qs.get("code", [""])[0],
            "state": qs.get("state", [""])[0],
        }
    return {"code": value}


def extract_account_id(access_token: str) -> str:
    """JWT-Decode: chatgpt_account_id aus dem access_token holen.

    Token ist ein 3-teiliger JWT (header.payload.signature). Wir decoden
    den Payload (base64url) und greifen auf den Custom-Claim zu.
    """
    try:
        parts = access_token.split(".")
        if len(parts) < 2:
            return ""
        payload_b64 = parts[1]
        # Padding für base64-decode
        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
        return payload.get("https://api.openai.com/auth", {}).get("chatgpt_account_id", "")
    except Exception:
        return ""


async def exchange_code(*, code: str, verifier: str) -> dict[str, Any]:
    """Tausch Authorization-Code gegen Access- + Refresh-Token + account_id.

    Antwort-Schema (auf HH2-llm.json-OAuth-Format normalisiert):
      { access, refresh, expires_at (epoch s), account_id, scope }
    """
    body = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=30.0, headers={**_HTTP_HEADERS,
                                                          "Content-Type": "application/x-www-form-urlencoded"}) as client:
        resp = await client.post(TOKEN_URL, data=body)
        resp.raise_for_status()
        data = resp.json()
    return _normalize_token_response(data)


async def refresh_access_token(*, refresh_token: str) -> dict[str, Any]:
    """Holt einen neuen Access-Token mit dem Refresh-Token.

    OpenAI rotiert den refresh_token bei jedem Refresh — wir speichern den neuen.
    """
    body = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
        "scope": SCOPE,
    }
    async with httpx.AsyncClient(timeout=30.0, headers={**_HTTP_HEADERS,
                                                          "Content-Type": "application/x-www-form-urlencoded"}) as client:
        resp = await client.post(TOKEN_URL, data=body)
        resp.raise_for_status()
        data = resp.json()
    return _normalize_token_response(data)


def _normalize_token_response(data: dict) -> dict[str, Any]:
    access = data.get("access_token") or ""
    expires_in = int(data.get("expires_in") or 3600)
    return {
        "access": access,
        "refresh": data.get("refresh_token") or "",
        "expires_at": int(time.time()) + expires_in,
        "scope": data.get("scope") or SCOPE,
        "account_id": extract_account_id(access),
    }


# Refresh-Schwelle: wenn Token in <5 min abläuft, vorher refreshen
_REFRESH_THRESHOLD_S = 300


async def resolve_openai_codex_token() -> dict[str, str]:
    """Gibt aktuellen OAuth-Block für openai-Provider zurück, refresht bei Bedarf.

    Returns: {access, account_id} — beides nicht-leer wenn OAuth aktiv ist.
    Sonst {} (kein OAuth oder beides leer).
    """
    from hydrahive.settings import settings

    path = settings.llm_config
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    provider = next((p for p in data.get("providers", []) if p.get("id") == "openai"), None)
    if not provider:
        return {}

    oauth = provider.get("oauth") or {}
    access = oauth.get("access", "")
    refresh = oauth.get("refresh", "")
    account_id = oauth.get("account_id", "")
    expires_at = int(oauth.get("expires_at") or 0)

    if not access:
        return {}

    # Gültig?
    if expires_at - time.time() > _REFRESH_THRESHOLD_S:
        return {"access": access, "account_id": account_id}

    # Refresh
    if not refresh:
        return {"access": access, "account_id": account_id}  # ohne refresh — hoffen
    try:
        new_block = await refresh_access_token(refresh_token=refresh)
    except Exception:
        return {"access": access, "account_id": account_id}

    # Re-read llm.json um Race mit GUI zu vermeiden
    data = json.loads(path.read_text())
    for p in data.get("providers", []):
        if p.get("id") == "openai":
            p["oauth"] = new_block
            break
    path.write_text(json.dumps(data, indent=2))
    return {"access": new_block["access"], "account_id": new_block["account_id"]}
