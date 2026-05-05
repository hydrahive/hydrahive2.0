#!/usr/bin/env python3
"""OpenAI Codex OAuth-Login im Bash-Installer (ChatGPT Plus/Pro).

Flow:
  1. Lokalen HTTP-Server auf 127.0.0.1:1455 mit Pfad /auth/callback starten
  2. Browser automatisch mit Authorize-URL öffnen (auth.openai.com)
  3. User autorisiert
  4. Browser wird zu http://localhost:1455/auth/callback?code=…&state=…
     umgeleitet → Server fängt das ab
  5. Token-Exchange (form-encoded), JWT-decode für chatgpt_account_id
  6. llm.json: provider 'openai' bekommt einen oauth-Block

Parallel: stdin-Input für manuellen Code-Paste (wenn Browser anderswo läuft).

Usage:
  python3 oauth_codex_cli.py /etc/hydrahive2/llm.json

Exit-Codes:
  0 = OK
  1 = Timeout / Bind-Fehler / User-Abbruch
  2 = OpenAI-Server hat den Code abgelehnt
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import select
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 1455
CALLBACK_PATH = "/auth/callback"
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"
SCOPE = "openid profile email offline_access"
ORIGINATOR = "hydrahive"

HTTP_HEADERS_AUTH = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "codex_cli_rs/0.55.0",
}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_pkce() -> tuple[str, str, str]:
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = _b64url(secrets.token_bytes(16))
    return verifier, challenge, state


def make_authorize_url(challenge: str, state: str) -> str:
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
        return {"code": qs.get("code", [""])[0], "state": qs.get("state", [""])[0]}
    return {"code": value}


def extract_account_id(access_token: str) -> str:
    try:
        parts = access_token.split(".")
        if len(parts) < 2:
            return ""
        payload_b64 = parts[1]
        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
        return payload.get("https://api.openai.com/auth", {}).get("chatgpt_account_id", "")
    except Exception:
        return ""


def exchange_code(*, code: str, verifier: str) -> dict:
    body = urlencode({
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = Request(TOKEN_URL, data=body, method="POST", headers=HTTP_HEADERS_AUTH)
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    access = data.get("access_token") or ""
    expires_in = int(data.get("expires_in") or 3600)
    return {
        "access": access,
        "refresh": data.get("refresh_token") or "",
        "expires_at": int(time.time()) + expires_in,
        "scope": data.get("scope") or SCOPE,
        "account_id": extract_account_id(access),
    }


_RESULT: dict = {}
_EXPECTED_STATE = ""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        qs = parse_qs(parsed.query)
        code = qs.get("code", [""])[0]
        state = qs.get("state", [""])[0]
        if not code:
            self._html(400, "Kein Code im Callback")
            return
        if _EXPECTED_STATE and state != _EXPECTED_STATE:
            self._html(400, "State stimmt nicht — Flow neu starten")
            return
        _RESULT["code"] = code
        _RESULT["state"] = state
        self._html(200, "Erfolgreich verbunden — du kannst dieses Tab schließen.")

    def _html(self, status: int, msg: str):
        body = f"""<!DOCTYPE html><html><head>
<meta charset='utf-8'><title>HydraHive2 OAuth</title></head>
<body style='font-family:system-ui;max-width:480px;margin:6em auto;text-align:center;color:#222'>
<h2>{'✓ Verbunden' if status == 200 else '⚠ Fehler'}</h2>
<p>{msg}</p></body></html>""".encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        pass


def _serve_until_code(timeout_s: float) -> None:
    server = socketserver.TCPServer((CALLBACK_HOST, CALLBACK_PORT), _Handler,
                                    bind_and_activate=False)
    server.allow_reuse_address = True
    server.server_bind()
    server.server_activate()
    server.timeout = 0.5
    deadline = time.time() + timeout_s
    try:
        while "code" not in _RESULT and time.time() < deadline:
            server.handle_request()
    finally:
        server.server_close()


def save_to_llm_config(path: Path, oauth_block: dict) -> None:
    """Schreibt oauth-Block in den openai-Provider von llm.json."""
    if path.exists():
        data = json.loads(path.read_text())
    else:
        data = {"providers": [], "default_model": "", "embed_model": ""}
    providers = data.setdefault("providers", [])
    found = next((p for p in providers if p.get("id") == "openai"), None)
    if found is None:
        # Default-Modelle: gpt-5 etc. (codex routing erfordert openai-codex/-Prefix
        # oder Variantenname — hier basics)
        found = {"id": "openai", "name": "OpenAI", "api_key": "",
                 "models": ["openai/gpt-5", "openai/gpt-5-mini", "openai/gpt-4o"]}
        providers.append(found)
    found["oauth"] = oauth_block
    if not data.get("default_model") and found["models"]:
        data["default_model"] = found["models"][0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    # Backend-Permissions setzen
    import pwd, os as _os
    try:
        uid = pwd.getpwnam("hydrahive").pw_uid
        gid = pwd.getpwnam("hydrahive").pw_gid
        _os.chown(path, uid, gid)
        _os.chmod(path, 0o640)
    except (KeyError, PermissionError):
        pass


def main() -> int:
    global _EXPECTED_STATE
    if len(sys.argv) != 2:
        print("Usage: oauth_codex_cli.py <llm-json-path>", file=sys.stderr)
        return 1
    llm_path = Path(sys.argv[1])

    verifier, challenge, state = make_pkce()
    _EXPECTED_STATE = state
    url = make_authorize_url(challenge, state)

    print()
    print("\033[1;36m── OpenAI ChatGPT-Plus OAuth (Codex) ──\033[0m")
    print()
    print(f"  Lokaler Callback-Server: {REDIRECT_URI}")
    print("  Browser wird automatisch geöffnet — falls nicht, manuell öffnen.")
    print()
    print("  URL (ggf. manuell im Browser öffnen):")
    print(f"  {url}")
    print()
    print("  Zwei Wege wie der Code zurück kommt:")
    print()
    print("  A) Browser läuft auf DIESEM Server (oder per SSH-Tunnel:")
    print("     ssh -L 1455:localhost:1455 …): Callback kommt automatisch.")
    print("  B) Browser läuft anderswo: 'Verbindung verweigert' bei localhost:1455.")
    print("     Kopiere die ganze Adressleisten-URL hier rein und Enter.")
    print()
    print("  Eingabe (oder warten auf Auto-Callback, Timeout 5 min):")

    server_thread = threading.Thread(target=_serve_until_code, args=(300.0,), daemon=True)
    server_thread.start()
    time.sleep(0.3)

    opened = False
    try:
        opened = webbrowser.open(url)
    except Exception:
        opened = False
    if not opened:
        print("  (Auto-Open nicht möglich, bitte URL oben manuell öffnen)")

    deadline = time.time() + 300.0
    manual_value = None
    while time.time() < deadline and "code" not in _RESULT and manual_value is None:
        try:
            r, _, _ = select.select([sys.stdin], [], [], 0.5)
        except (ValueError, OSError):
            r = []
            time.sleep(0.5)
        if r:
            line = sys.stdin.readline()
            if line:
                manual_value = line.strip()

    if manual_value:
        parsed = parse_callback(manual_value)
        if not parsed.get("code"):
            print("  Kein Code erkannt — abgebrochen.", file=sys.stderr)
            return 1
        _RESULT["code"] = parsed["code"]
        _RESULT["state"] = parsed.get("state") or state

    if "code" not in _RESULT:
        print("\033[1;31m  Timeout — kein Callback in 5 Minuten\033[0m", file=sys.stderr)
        return 1

    code = _RESULT["code"]
    try:
        token = exchange_code(code=code, verifier=verifier)
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        print(f"\033[1;31m  OpenAI-Fehler ({e.code}): {body}\033[0m", file=sys.stderr)
        return 2
    except URLError as e:
        print(f"\033[1;31m  Verbindung zu {TOKEN_URL} fehlgeschlagen: {e}\033[0m",
              file=sys.stderr)
        return 2

    if not token.get("account_id"):
        print("\033[1;31m  account_id konnte nicht aus Token extrahiert werden\033[0m",
              file=sys.stderr)
        return 2

    save_to_llm_config(llm_path, token)
    expires_h = int((token["expires_at"] - time.time()) / 3600)
    print(f"\033[1;32m  ✓ OpenAI-Codex OAuth gespeichert "
          f"(account: {token['account_id'][:12]}…, läuft in ~{expires_h}h ab)\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
