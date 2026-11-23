"""Anmeldung an der Testseite eines Projekts (ziele/projekt-testumgebung.md §4, Etappe E1a; Muster Modul Vibe).

HydraHive meldet per Bearer an – beim Aufruf der Testseite über die nginx-Durchreiche geht davon nichts mit. Darum:
- ``POST /api/projects/{id}/preview/open`` (Projekt-Mitglied) gibt ein Einmal-Ticket (60 s).
- ``GET /api/project-preview/login?t=…`` löst es ein und setzt das Cookie ``hh_project_preview`` (HttpOnly, Secure),
  signiert mit einem eigenen, zweckgebundenen Schlüssel. Im Cookie steht nur, WELCHES Projekt gemeint ist (und für
  wen, damit entzogene Rechte sofort greifen).
- ``GET /api/project-preview/auth`` prüft das Cookie für nginx (auth_request) und nennt den Ziel-Port.

Das Cookie ist kein HydraHive-Login: anderer Name, anderer Schlüssel, anderes Format als das JWT. ``require_auth``
liest nur den Bearer-Header und kennt kein Cookie. Tickets liegen im Speicher (der Kern läuft mit einem Prozess).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time

COOKIE = "hh_project_preview"
MAX_AGE = 8 * 3600
TICKET_TTL = 60
MAX_TICKETS = 200
_CONTEXT = b"hydrahive-project-preview-v1"
_MAX_LEN = 600
_tickets: dict[str, tuple[str, str, float]] = {}
_lock = threading.Lock()


def _key() -> bytes:
    from hydrahive.settings import settings
    return hmac.new(settings.secret_key.encode(), _CONTEXT, hashlib.sha256).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    return _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())


def new_ticket(user_id: str, project_id: str, *, now: float | None = None) -> str:
    now = time.time() if now is None else now
    with _lock:
        for t, (_, _, exp) in list(_tickets.items()):
            if exp < now:
                del _tickets[t]
        while len(_tickets) >= MAX_TICKETS:
            del _tickets[next(iter(_tickets))]          # ältestes zuerst
        ticket = secrets.token_urlsafe(32)
        _tickets[ticket] = (user_id, project_id, now + TICKET_TTL)
    return ticket


def is_member(user_id: str, project_id: str) -> bool:
    """Nutzer gibt es noch und er hat (noch) mindestens Leserecht am Projekt. System-Admins dürfen immer."""
    from hydrahive.api.middleware import users
    from hydrahive.projects import _members_model
    from hydrahive.projects import config as project_config
    user = users.get_by_id(user_id)
    project = project_config.get(project_id)
    if not user or not project:
        return False
    if user.get("role") == "admin":
        return True
    return _members_model.has_at_least(_members_model.role_of(project, user.get("username", "")), "read")


def redeem(ticket: str, *, now: float | None = None) -> tuple[str, str] | None:
    """Einmal: (user_id, project_id), wenn das Ticket gilt und die Rechte noch stimmen. Sonst None."""
    with _lock:
        entry = _tickets.pop(ticket, None)
    if not entry or entry[2] < (time.time() if now is None else now):
        return None
    return (entry[0], entry[1]) if is_member(entry[0], entry[1]) else None


def issue_cookie(user_id: str, project_id: str, *, now: float | None = None) -> str:
    now = time.time() if now is None else now
    body = _b64(json.dumps({"uid": user_id, "pid": project_id, "exp": int(now) + MAX_AGE}).encode())
    return f"{body}.{_sign(body)}"


def project_from(cookie: str | None, *, now: float | None = None) -> str | None:
    """Projekt-ID aus einem gültigen Cookie (Signatur, Ablauf, Mitgliedschaft) – sonst None."""
    if not cookie or len(cookie) > _MAX_LEN or cookie.count(".") != 1:
        return None
    body, sig = cookie.split(".")
    if not hmac.compare_digest(sig, _sign(body)):
        return None
    try:
        data = json.loads(_unb64(body))
        uid, pid, exp = data["uid"], data["pid"], int(data["exp"])
    except (ValueError, KeyError, TypeError):
        return None
    if exp < (time.time() if now is None else now) or not isinstance(uid, str) or not isinstance(pid, str):
        return None
    return pid if is_member(uid, pid) else None


def clear() -> None:
    """Nur für Tests."""
    with _lock:
        _tickets.clear()
