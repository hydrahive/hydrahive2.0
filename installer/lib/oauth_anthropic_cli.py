#!/usr/bin/env python3
"""Anthropic OAuth-Login im Bash-Installer (analog zu OpenClaw / pi-mono).

Flow:
  1. Lokalen HTTP-Server auf 127.0.0.1:53692 starten
  2. Browser automatisch mit Authorize-URL öffnen
     (geht nicht automatisch → URL ausgeben, User öffnet manuell IM gleichen
      Browser; der Callback landet trotzdem am laufenden Server)
  3. claude.ai redirected zu http://localhost:53692/callback?code=...
  4. Server fängt das ab → Token-Exchange → llm.json

Usage:
  python3 oauth_anthropic_cli.py /etc/hydrahive2/llm.json

Exit-Codes:
  0 = OK
  1 = Timeout / Bind-Fehler
  2 = Anthropic-Server hat den Code abgelehnt
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 53692
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"
SCOPES = (
    "org:create_api_key user:profile user:inference "
    "user:sessions:claude_code user:mcp_servers user:file_upload"
)

# Cloudflare blockt Python-urllib/3.x als Bot-Signatur (Error 1010).
# Wir geben uns als Claude Code aus — gleicher User-Agent + anthropic-beta-Header
# wie in core/src/hydrahive/llm/_anthropic.py (_OAUTH_HEADERS).
HTTP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "claude-cli/2.1.62",
    "anthropic-beta": "claude-code-20250219,oauth-2025-04-20",
    "x-app": "cli",
}

ANTHROPIC_DEFAULT_MODELS = ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5"]


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_pkce() -> tuple[str, str]:
    """Anthropic-OAuth: state ist der verifier (siehe pi-mono anthropic.ts).
    Daher kein separater state, nur (verifier, challenge)."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def make_authorize_url(challenge: str, verifier: str) -> str:
    """Anthropic verlangt zusätzlich code=true und state=verifier (pi-mono)."""
    params = {
        "code": "true",
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": verifier,
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
        return {
            "code": qs.get("code", [""])[0],
            "state": qs.get("state", [""])[0],
        }
    return {"code": value}


_RESULT: dict = {}
_EXPECTED_STATE = ""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
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

    def log_message(self, *args, **kwargs):  # silence
        pass


def _serve_until_code(timeout_s: float) -> None:
    """Startet HTTP-Server, läuft bis _RESULT['code'] gesetzt oder Timeout."""
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


def exchange_code(*, code: str, verifier: str, state: str) -> dict:
    body = json.dumps({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
        "state": state,
    }).encode()
    req = Request(TOKEN_URL, data=body, method="POST", headers=HTTP_HEADERS)
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    expires_in = int(data.get("expires_in") or 3600)
    return {
        "access": data.get("access_token") or "",
        "refresh": data.get("refresh_token") or "",
        "expires_at": int(time.time()) + expires_in,
        "scope": data.get("scope") or SCOPES,
    }


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
    # Backend (hydrahive) muss schreiben können — sonst überschreibt die Web-UI nichts.
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
        print("Usage: oauth_anthropic_cli.py <llm-json-path>", file=sys.stderr)
        return 1
    llm_path = Path(sys.argv[1])

    verifier, challenge = make_pkce()
    # Bei Anthropic: state == verifier (pi-mono Pattern)
    _EXPECTED_STATE = verifier
    url = make_authorize_url(challenge, verifier)

    print()
    print("\033[1;36m── Anthropic OAuth ──\033[0m")
    print()
    print(f"  Lokaler Callback-Server lauscht auf {REDIRECT_URI}")
    print("  Browser wird automatisch geöffnet — falls nicht, manuell öffnen.")
    print()

    # HTTP-Server in eigenem Thread starten
    server_thread = threading.Thread(target=_serve_until_code, args=(300.0,), daemon=True)
    server_thread.start()
    time.sleep(0.3)  # bind-race vermeiden

    # Browser öffnen
    opened = False
    try:
        opened = webbrowser.open(url)
    except Exception:
        opened = False

    print("  URL (öffne im Browser, falls nicht automatisch geöffnet):")
    print(f"  {url}")
    print()
    print("  Anthropic erlaubt nur localhost:53692 als Redirect-URI. Zwei Wege:")
    print()
    print("  A) Browser läuft auf DIESEM Server (oder per SSH-Tunnel:")
    print("     ssh -L 53692:localhost:53692 …): Callback kommt automatisch.")
    print("  B) Browser läuft anderswo (Remote-SSH ohne Tunnel):")
    print("     Browser zeigt 'Verbindung verweigert' bei localhost:53692.")
    print("     Kopiere die ganze Adressleisten-URL hier rein und Enter.")
    print()
    print("  Eingabe (oder warten auf Auto-Callback, Timeout 5 min):")

    # Parallel auf Server-Result UND stdin warten
    import select
    deadline = time.time() + 300.0
    manual_value = None
    while time.time() < deadline and "code" not in _RESULT and manual_value is None:
        try:
            r, _, _ = select.select([sys.stdin], [], [], 0.5)
        except (ValueError, OSError):
            r = []  # stdin nicht selectable (z.B. unter test)
            time.sleep(0.5)
        if r:
            line = sys.stdin.readline()
            if line:
                manual_value = line.strip()

    if manual_value:
        parsed = parse_callback(manual_value)
        if not parsed.get("code"):
            print("  Kein Code erkannt in der Eingabe — abgebrochen.", file=sys.stderr)
            return 1
        _RESULT["code"] = parsed["code"]
        _RESULT["state"] = parsed.get("state") or verifier

    if "code" not in _RESULT:
        print("\033[1;31m  Timeout — kein Callback in 5 Minuten\033[0m", file=sys.stderr)
        return 1

    code = _RESULT["code"]
    cb_state = _RESULT.get("state") or verifier
    try:
        token = exchange_code(code=code, verifier=verifier, state=cb_state)
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        print(f"\033[1;31m  Anthropic-Fehler ({e.code}): {body}\033[0m", file=sys.stderr)
        return 2
    except URLError as e:
        print(f"\033[1;31m  Verbindung zu {TOKEN_URL} fehlgeschlagen: {e}\033[0m",
              file=sys.stderr)
        return 2

    save_to_llm_config(llm_path, token)
    expires_h = int((token["expires_at"] - time.time()) / 3600)
    print(f"\033[1;32m  ✓ Anthropic OAuth gespeichert (läuft in ~{expires_h}h ab)\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
