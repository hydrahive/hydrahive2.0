"""Vorschau-Port je Projekt (ziele/projekt-testumgebung.md §3 Weg B, Etappe E1a).

Jedes Projekt bekommt beim ersten Bedarf einen festen Port aus einem Bereich (Standard 18100–18999, überschreibbar mit
``HH_PREVIEW_PORT_MIN``/``HH_PREVIEW_PORT_MAX``). Der Port steht in der Projekt-Konfig (``preview_port``) und bleibt
gleich. Vergeben wird der kleinste freie Port im Bereich, den kein anderes Projekt hat – unter einer Sperre, damit zwei
gleichzeitige Anfragen nicht denselben Port bekommen. Bereich voll → ``PreviewPortError`` (kein Rückfall).
"""
from __future__ import annotations

import os
import socket
import threading

FIELD = "preview_port"
DEFAULT_MIN = 18100
DEFAULT_MAX = 18999
CONNECT_TIMEOUT = 0.3
_lock = threading.Lock()


class PreviewPortError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _env_port(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        return default
    return value if 1024 <= value <= 65535 else default


def port_range() -> tuple[int, int]:
    """Bereich aus der Umgebung; ungültig oder vertauscht → Standard."""
    low, high = _env_port("HH_PREVIEW_PORT_MIN", DEFAULT_MIN), _env_port("HH_PREVIEW_PORT_MAX", DEFAULT_MAX)
    return (low, high) if low <= high else (DEFAULT_MIN, DEFAULT_MAX)


def _valid(port: object, low: int, high: int) -> bool:
    return isinstance(port, int) and not isinstance(port, bool) and low <= port <= high


def stored(project: dict | None) -> int | None:
    """Gespeicherter Port, wenn er im aktuellen Bereich liegt – sonst None (wird dann neu vergeben)."""
    low, high = port_range()
    port = (project or {}).get(FIELD)
    return port if _valid(port, low, high) else None


def ensure(project_id: str) -> int:
    """Port des Projekts; beim ersten Mal vergeben und speichern. Stabil bei jedem weiteren Aufruf."""
    from hydrahive.projects import config as project_config
    with _lock:
        project = project_config.get(project_id)
        if project is None:
            raise PreviewPortError("project_not_found")
        own = stored(project)
        low, high = port_range()
        taken = {p.get(FIELD) for p in project_config.list_all() if p.get("id") != project_id}
        if own is not None and own not in taken:
            return own
        for port in range(low, high + 1):
            if port not in taken:
                project_config.update(project_id, **{FIELD: port})
                return port
    raise PreviewPortError("preview_port_exhausted")


def for_shell(project_id: str | None) -> int | None:
    """Port für HH_PREVIEW_PORT – None ohne Projekt oder bei jeder Störung (shell_exec läuft dann wie bisher)."""
    if not project_id:
        return None
    try:
        return ensure(project_id)
    except Exception:  # noqa: BLE001 – die Shell darf daran nie scheitern
        return None


def running(port: int, host: str = "127.0.0.1", timeout: float = CONNECT_TIMEOUT) -> bool:
    """Antwortet unter host:port etwas? Kurzer TCP-Connect, keine Daten."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
