#!/usr/bin/env python3
"""Anthropic OAuth-Login im Bash-Installer (analog zu OpenClaw onboard).

Wird vom llm-wizard.sh aufgerufen wenn der User OAuth statt API-Key wählt.
Macht den ganzen Flow inkl. Token-Exchange + Schreiben in llm.json.

Usage:
  python3 oauth_anthropic_cli.py /etc/hydrahive2/llm.json

Exit-Codes:
  0 = OAuth erfolgreich, llm.json geschrieben
  1 = User hat abgebrochen oder Eingabe ungültig
  2 = Anthropic-Server hat den Code abgelehnt

Benutzt nur stdlib — keine venv-Abhängigkeit.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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


def make_pkce() -> tuple[str, str, str]:
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = _b64url(secrets.token_bytes(16))
    return verifier, challenge, state


def parse_callback(value: str) -> dict:
    value = value.strip()
    if not value:
        return {}
    try:
        parsed = urlparse(value)
        if parsed.scheme:
            qs = parse_qs(parsed.query)
            out = {}
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


def exchange_code(*, code: str, verifier: str, state: str) -> dict:
    body = json.dumps({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
        "state": state,
    }).encode()
    req = Request(TOKEN_URL, data=body, method="POST",
                  headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    expires_in = int(data.get("expires_in") or 3600)
    return {
        "access": data.get("access_token") or "",
        "refresh": data.get("refresh_token") or "",
        "expires_at": int(time.time()) + expires_in,
        "scope": data.get("scope") or SCOPES,
    }


ANTHROPIC_DEFAULT_MODELS = ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5"]


def save_to_llm_config(path: Path, oauth_block: dict) -> None:
    if path.exists():
        data = json.loads(path.read_text())
    else:
        data = {"providers": [], "default_model": "", "embed_model": ""}
    providers = data.setdefault("providers", [])
    found = next((p for p in providers if p.get("id") == "anthropic"), None)
    if found is None:
        found = {"id": "anthropic", "name": "Anthropic", "api_key": "",
                 "models": list(ANTHROPIC_DEFAULT_MODELS)}
        providers.append(found)
    found["oauth"] = oauth_block
    if not data.get("default_model") and found["models"]:
        data["default_model"] = found["models"][0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: oauth_anthropic_cli.py <llm-json-path>", file=sys.stderr)
        return 1
    llm_path = Path(sys.argv[1])

    verifier, challenge, state = make_pkce()
    params = {
        "client_id": CLIENT_ID, "response_type": "code", "redirect_uri": REDIRECT_URI,
        "scope": SCOPES, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    }
    url = f"{AUTHORIZE_URL}?{urlencode(params)}"

    print()
    print("\033[1;36m── Anthropic OAuth ──\033[0m")
    print()
    print("  1. Öffne diese URL in deinem Browser (Pro/Max-Account):")
    print()
    print(f"     \033[4;37m{url}\033[0m")
    print()
    print("  2. Autorisiere — du wirst zu http://localhost:53692/callback?code=...")
    print("     weitergeleitet. Der Browser zeigt 'Verbindung verweigert' — egal,")
    print("     die URL in der Adressleiste enthält den Code.")
    print()
    print("  3. Kopiere die KOMPLETTE URL (oder nur den code-Param) hierher:")
    print()
    try:
        raw = input("  Callback-URL/Code: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Abgebrochen.", file=sys.stderr)
        return 1
    if not raw:
        print("  Keine Eingabe — abgebrochen.", file=sys.stderr)
        return 1

    parsed = parse_callback(raw)
    code = parsed.get("code", "")
    if not code:
        print(f"\033[1;31m  Kein Code erkannt in: {raw[:80]}\033[0m", file=sys.stderr)
        return 1
    callback_state = parsed.get("state") or state

    try:
        token = exchange_code(code=code, verifier=verifier, state=callback_state)
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        print(f"\033[1;31m  Anthropic hat den Code abgelehnt ({e.code}): {body}\033[0m",
              file=sys.stderr)
        return 2
    except URLError as e:
        print(f"\033[1;31m  Verbindung zu {TOKEN_URL} fehlgeschlagen: {e}\033[0m",
              file=sys.stderr)
        return 2

    save_to_llm_config(llm_path, token)
    expires_h = int((token["expires_at"] - time.time()) / 3600)
    print(f"\033[1;32m  ✓ Anthropic OAuth gespeichert ({llm_path}, läuft in ~{expires_h}h ab)\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
