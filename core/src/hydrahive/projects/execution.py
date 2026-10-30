"""Wo die Befehle eines Projekts laufen (docs/specs/projekt-container-ausfuehrung.md).

`host` (Standard, wie bisher) oder `container` (incus). Setzen nur über diese Funktionen – nicht über
`config.update()` und nicht über das normale PATCH. Ein beschädigter Eintrag wirft `ExecutionError` und fällt nie
still auf den Server zurück.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

_NAME = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
_WORKDIR = re.compile(r"^/(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$")
HOST: dict[str, Any] = {"mode": "host"}
FIELD = "execution"


class ExecutionError(ValueError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def _container_exists(name: str) -> bool:
    incus = shutil.which("incus")
    if not incus:
        return False
    r = subprocess.run([incus, "list", "--format", "csv", "-c", "n", "--", f"^{name}$"],
                       capture_output=True, text=True, timeout=20, check=False)
    return r.returncode == 0 and name in r.stdout.split()


def _check(container: Any, workdir: Any, user: Any) -> dict:
    if not isinstance(container, str) or not _NAME.match(container):
        raise ExecutionError("project_container_invalid", "Containername ungültig")
    if not isinstance(workdir, str) or not _WORKDIR.match(workdir) or ".." in workdir.split("/"):
        raise ExecutionError("project_container_invalid", "Arbeitsverzeichnis ungültig")
    if not isinstance(user, int) or isinstance(user, bool) or not 1 <= user <= 65535:
        raise ExecutionError("project_container_invalid", "Nutzer ungültig")
    return {"mode": "container", "container": container, "workdir": workdir, "user": user}


def of(project: dict | None) -> dict:
    """Wirksame Ausführung eines Projekts. Fehlt das Feld: Server. Kaputt: ExecutionError."""
    if not project or FIELD not in project:
        return dict(HOST)
    raw = project[FIELD]
    if raw == HOST:
        return dict(HOST)
    if not isinstance(raw, dict) or raw.get("mode") != "container":
        raise ExecutionError("project_execution_invalid", "Ausführung des Projekts ist beschädigt")
    try:
        return _check(raw.get("container"), raw.get("workdir", "/work"), raw.get("user", 1000))
    except ExecutionError:
        raise ExecutionError("project_execution_invalid", "Ausführung des Projekts ist beschädigt") from None


def _write(project_id: str, value: dict, actor: str, action: str) -> dict:
    from hydrahive.projects import audit as project_audit
    from hydrahive.projects._config_io import _save_atomic, get
    from hydrahive.projects._paths import config_path
    from hydrahive.db._utils import now_iso
    cfg = get(project_id)
    if not cfg:
        raise ExecutionError("project_not_found")
    cfg[FIELD] = value
    cfg["updated_at"] = now_iso()
    _save_atomic(config_path(project_id), cfg)
    project_audit.log(project_id, actor, action, details=dict(value))
    return cfg


def set_container(project_id: str, container: str, *, actor: str, workdir: str = "/work", user: int = 1000) -> dict:
    value = _check(container, workdir, user)
    if not _container_exists(container):
        raise ExecutionError("project_container_missing", "Container gibt es nicht")
    return _write(project_id, value, actor, "execution_container")


def set_host(project_id: str, *, actor: str, confirm: str) -> dict:
    """Zurück auf den Server – nur mit dem Projektnamen als Bestätigung."""
    from hydrahive.projects._config_io import get
    cfg = get(project_id)
    if not cfg:
        raise ExecutionError("project_not_found")
    if not confirm or confirm != cfg.get("name"):
        raise ExecutionError("project_execution_confirm", "Bestätigung fehlt")
    return _write(project_id, dict(HOST), actor, "execution_host")
