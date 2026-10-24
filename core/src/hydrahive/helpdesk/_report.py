"""Fehlerbericht des Hilfe-Assistenten (docs/plans/help-error-report.md, Task f3ac5dc2).

Der Bericht entsteht hier aus echten Daten – Fehlerprotokoll DIESES Nutzers (letzte 24 h, höchstens 5), Seite,
Versionen, System – nach fester Vorlage. Vom Modell kommt nur die Beschreibung. Nichts darin nennt Nutzer, Sitzung
oder Agent; das Heimverzeichnis wird zu „~“; bekannte Secrets werden geschwärzt.
Entwürfe liegen im Speicher des Dienstes (je Nutzer, TTL), sind einmal sendbar. Gesendet wird nur über die Route.
"""
from __future__ import annotations

import os
import platform
import re
import secrets as _rand
import threading
import time
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db
from hydrahive.helpdesk._context import clean_path

DEFAULT_TO = "issue@hydrahive.org"
TTL = 30 * 60
PER_USER_HOUR = 3
PER_INSTANCE_HOUR = 10
MAX_ERRORS = 5
MAX_DESC = 1000
TB_LINES = 8
_ADDR = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,63}$")
_HOME = re.compile(r"(/home/[^/\s'\"]+|/Users/[^/\s'\"]+|/root)(?=/)")
_DRAFTS: dict[str, dict] = {}
_PAGES: dict[str, str] = {}             # Hilfe-Sitzung → zuletzt gemeldete Seite (vom Fenster, bereinigt)
_SENT: list[tuple[float, str]] = []
_LOCK = threading.Lock()


class ReportError(LookupError):
    pass


class RateLimited(RuntimeError):
    pass


def _now() -> float:
    return time.time()


def enabled() -> bool:
    from hydrahive.settings.overrides import env_or_override
    return env_or_override("help_error_report_enabled", "HH_HELP_ERROR_REPORT", "true").strip().lower() \
        in ("1", "true", "yes", "on")


def recipient() -> str:
    to = os.environ.get("HH_ERROR_REPORT_TO", "").strip()
    return to if _ADDR.match(to) else DEFAULT_TO


def _secrets(user: str) -> set[str]:
    from hydrahive.credentials.redaction import egress_secrets
    return egress_secrets(user)


def _clean(text: str, secrets: set[str]) -> str:
    from hydrahive.credentials.redaction import scrub
    return _HOME.sub("~", scrub(text or "", secrets))


def _errors(user: str) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    with db() as c:
        rows = c.execute("SELECT created_at, source, error_type, error_message, traceback FROM errors_log "
                         "WHERE user_id=? AND created_at>=? ORDER BY created_at DESC LIMIT ?",
                         (user, since, MAX_ERRORS)).fetchall()
    return [dict(r) for r in rows]


def _modules() -> str:
    try:
        from hydrahive.modules.registry import REGISTRY
        items = sorted(f"{m.name} {m.manifest.version}" for m in REGISTRY.values() if m.loaded and m.manifest)
    except Exception:  # noqa: BLE001 - Bericht geht auch ohne Modulliste
        items = []
    return ", ".join(items) or "–"


def _version() -> str:
    from hydrahive.api.version import current_status
    commit, _ = current_status()
    return f"2.0.0 (Commit {(commit or '?')[:8]})"


def _system() -> str:
    mac = platform.mac_ver()[0]
    return f"macOS {mac}" if mac else f"{platform.system()} {platform.release()}"


def _error_block(e: dict, secrets: set[str]) -> str:
    tb = [ln for ln in (e.get("traceback") or "").splitlines() if ln.strip()][-TB_LINES:]
    lines = [f"{(e['created_at'] or '')[:16].replace('T', ' ')}  {e['source']}  {e.get('error_type') or ''}",
             f"   {(e.get('error_message') or '')[:500]}"] + [f"   {ln[:300]}" for ln in tb]
    return _clean("\n".join(lines), secrets)


def build(user: str, description: str, path: str | None) -> dict:
    secrets = _secrets(user)
    page = clean_path(path) or "unbekannt"
    desc = _clean((description or "").strip(), secrets)[:MAX_DESC] or "(keine Beschreibung)"
    errs = _errors(user)
    first = (errs[0].get("error_type") if errs else "") or "Meldung"
    blocks = [f"{i}) " + _error_block(e, secrets) for i, e in enumerate(errs, 1)] or \
             ["keine Einträge im Fehlerprotokoll der letzten 24 Stunden"]
    rid = _rand.token_urlsafe(12)
    body = "\n".join([
        "Beschreibung (Nutzer):", desc, "",
        f"Seite: {page}",
        f"HydraHive: {_version()}   System: {_system()}   Python: {platform.python_version()}",
        f"Module: {_modules()}", "",
        "Fehler (letzte 24 h, dieser Nutzer, geschwärzt):", *blocks, "",
        f"Bericht-ID: {rid}   Gesendet über das Mailkonto der Installation.",
    ])
    subject = _clean(f"[HydraHive-Fehler] {first} – {page} – {_version()}", secrets)[:200]
    return {"id": rid, "subject": subject, "body": body, "errors": len(errs)}


def remember_page(session_id: str, path: str | None) -> None:
    """Vom Hilfe-Fenster (POST /messages): Seite für den Bericht merken – das Modell kann sie nicht setzen."""
    with _LOCK:
        if len(_PAGES) > 5000:
            _PAGES.clear()
        _PAGES[session_id] = clean_path(path) or ""


def page_for(session_id: str) -> str | None:
    with _LOCK:
        return _PAGES.get(session_id) or None


def _gc(now: float) -> None:
    for rid, d in list(_DRAFTS.items()):
        if now > d["expires"]:
            del _DRAFTS[rid]


def prepare(user: str, description: str, path: str | None) -> dict:
    r = build(user, description, path)
    now = _now()
    with _LOCK:
        _gc(now)
        _DRAFTS[r["id"]] = {**r, "user": user, "expires": now + TTL}
    return r


def get(user: str, rid: str) -> dict | None:
    with _LOCK:
        _gc(_now())
        d = _DRAFTS.get(rid)
        return {k: d[k] for k in ("id", "subject", "body")} if d and d["user"] == user else None


def take(user: str, rid: str) -> dict:
    with _LOCK:
        _gc(_now())
        d = _DRAFTS.get(rid)
        if not d or d["user"] != user:
            raise ReportError("not_found")
        del _DRAFTS[rid]
        return {k: d[k] for k in ("id", "subject", "body")}


def restore(user: str, report: dict) -> None:
    """Nach gescheitertem Versand: Entwurf wieder hinlegen (neue Frist)."""
    with _LOCK:
        _DRAFTS[report["id"]] = {**report, "user": user, "expires": _now() + TTL}


def discard(user: str, rid: str) -> bool:
    with _LOCK:
        d = _DRAFTS.get(rid)
        if not d or d["user"] != user:
            return False
        del _DRAFTS[rid]
        return True


def check_limits(user: str) -> None:
    now = _now()
    with _LOCK:
        _SENT[:] = [(t, u) for t, u in _SENT if now - t < 3600]
        if sum(1 for _, u in _SENT if u == user) >= PER_USER_HOUR or len(_SENT) >= PER_INSTANCE_HOUR:
            raise RateLimited("Zu viele Fehlerberichte in der letzten Stunde")


def note_sent(user: str) -> None:
    with _LOCK:
        _SENT.append((_now(), user))
