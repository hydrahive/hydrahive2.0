"""VNC-Token-Files für websockify.

websockify --token-plugin=TokenFile --token-source=<dir> liest pro Verbindung
das File `<dir>/<token>.cfg` mit Inhalt `<token>: <host>:<port>` und proxied
nach Erfolg dorthin.

Beim VM-Start schreiben wir die Datei, beim Stop räumen wir auf.
"""
from __future__ import annotations

import logging
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def _safe_token(token: str) -> bool:
    """Token darf nur URL-safe Base64-Zeichen enthalten — verhindert Path-Tricks."""
    return token != "" and all(
        c.isalnum() or c in ("-", "_") for c in token
    )


def write_token(token: str, vnc_port: int, host: str = "127.0.0.1") -> None:
    if not _safe_token(token):
        raise ValueError(f"unsafe token: {token!r}")
    settings.vms_vnc_tokens_dir.mkdir(parents=True, exist_ok=True)
    path = settings.vms_vnc_tokens_dir / f"{token}.cfg"
    path.write_text(f"{token}: {host}:{vnc_port}\n", encoding="ascii")
    path.chmod(0o600)


def remove_token(token: str | None) -> None:
    if not token or not _safe_token(token):
        return
    path = settings.vms_vnc_tokens_dir / f"{token}.cfg"
    path.unlink(missing_ok=True)


def cleanup_orphans(active_tokens: set[str]) -> None:
    """Räumt Token-Files ab die zu keiner laufenden VM mehr gehören.

    Vom Reconciler aufgerufen damit nach Crashs keine Phantom-Tokens bleiben.
    """
    if not settings.vms_vnc_tokens_dir.exists():
        return
    for f in settings.vms_vnc_tokens_dir.glob("*.cfg"):
        token = f.stem
        if token not in active_tokens:
            f.unlink(missing_ok=True)
