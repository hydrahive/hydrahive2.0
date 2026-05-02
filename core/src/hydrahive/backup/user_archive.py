"""User-Daten-Export für DSGVO Art. 20 (Datenportabilität).

Erstellt ein .tar.gz mit allen Daten des Users: Sessions, Agents,
Workspaces, Projects, WhatsApp-Config, Butler-Flows.
"""
from __future__ import annotations

import dataclasses
import io
import json
import logging
import tarfile
import time
from pathlib import Path

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import workspace_for
from hydrahive.backup._paths import is_excluded
from hydrahive.butler import persistence as butler_persistence
from hydrahive.communication.whatsapp.config import _config_file as _wa_config_file
from hydrahive.db import messages, sessions
from hydrahive.projects import _config_io as project_config
from hydrahive.projects._paths import project_dir, workspace_path

logger = logging.getLogger(__name__)

ARCHIVE_VERSION = "1"


def create_user_archive(username: str, target_dir: Path) -> Path:
    """Erstellt ein User-Backup-Archiv. Gibt den Pfad zur .tar.gz zurück."""
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_path = target_dir / f"hydrahive2-user-{username}-{timestamp}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        manifest = {
            "version": ARCHIVE_VERSION,
            "kind": "user",
            "username": username,
            "created_at": timestamp,
        }
        _add_bytes(tar, "manifest.json", json.dumps(manifest, indent=2).encode())

        _export_sessions(tar, username)
        _export_agents(tar, username)
        _export_projects(tar, username)
        _export_whatsapp(tar, username)
        _export_butler(tar, username)

    logger.info("User-Backup erstellt: %s (%.1f MB)",
                archive_path, archive_path.stat().st_size / (1024 * 1024))
    return archive_path


def _export_sessions(tar: tarfile.TarFile, username: str) -> None:
    user_sessions = sessions.list_for_user(username, limit=10000)
    export = []
    for s in user_sessions:
        msgs = messages.list_for_session(s.id)
        export.append({
            **dataclasses.asdict(s),
            "messages": [dataclasses.asdict(m) for m in msgs],
        })
    _add_bytes(tar, "sessions.json", json.dumps(export, indent=2).encode())


def _export_agents(tar: tarfile.TarFile, username: str) -> None:
    for agent in agent_config.list_by_owner(username):
        agent_id = agent["id"]
        from hydrahive.agents._paths import agent_dir
        src = agent_dir(agent_id)
        _add_dir(tar, f"agents/{agent_id}", src)

        ws = workspace_for(agent)
        if agent.get("type") == "master":
            arcname = f"workspaces/master/{agent_id}"
        else:
            arcname = f"workspaces/specialists/{agent_id}"
        _add_dir(tar, arcname, ws)


def _export_projects(tar: tarfile.TarFile, username: str) -> None:
    for proj in project_config.list_for_user(username):
        pid = proj["id"]
        _add_dir(tar, f"projects/{pid}", project_dir(pid))
        _add_dir(tar, f"workspaces/projects/{pid}", workspace_path(pid))


def _export_whatsapp(tar: tarfile.TarFile, username: str) -> None:
    wa_file = _wa_config_file(username)
    if wa_file.exists():
        tar.add(wa_file, arcname="whatsapp.json")


def _export_butler(tar: tarfile.TarFile, username: str) -> None:
    for flow in butler_persistence.list_flows(owner=username):
        data = flow.model_dump_json(indent=2).encode()
        _add_bytes(tar, f"butler/{flow.flow_id}.json", data)


def _add_dir(tar: tarfile.TarFile, arcname: str, source: Path) -> None:
    if not source.exists():
        return
    for item in source.rglob("*"):
        if is_excluded(item):
            continue
        rel = item.relative_to(source)
        tar.add(item, arcname=f"{arcname}/{rel}", recursive=False)


def _add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = int(time.time())
    tar.addfile(info, io.BytesIO(data))
