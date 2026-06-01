"""User-Daten-Restore für DSGVO Art. 20.

Owner-Check: Das Archiv darf nur vom User restored werden der es erstellt hat.
Sessions/Messages werden per INSERT OR IGNORE eingespielt (kein Überschreiben).
Files werden direkt geschrieben — existierende Dateien bleiben erhalten.
"""
from __future__ import annotations

import json
import logging
import shutil
import tarfile
import tempfile
from pathlib import Path

from hydrahive.backup._limits import enforce_archive_limits
from hydrahive.db.connection import db
from hydrahive.projects._paths import project_dir, workspace_path
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


class UserRestoreError(Exception):
    def __init__(self, code: str, **params):
        super().__init__(code)
        self.code = code
        self.params = params


def restore_user_archive(archive_path: Path, username: str) -> None:
    """Restore User-Backup. Wirft UserRestoreError bei Problemen."""
    with tarfile.open(archive_path, "r:gz") as tar:
        manifest = _read_manifest(tar)

        if manifest.get("kind") != "user":
            raise UserRestoreError("backup_wrong_kind")
        if manifest.get("username") != username:
            raise UserRestoreError("backup_wrong_owner")

        enforce_archive_limits(tar)  # Dekompressionsbomben-Schutz (#189)
        with tempfile.TemporaryDirectory(prefix="hh2-user-restore-") as tmp:
            tmp_path = Path(tmp)
            tar.extractall(tmp_path, filter="data")

            _restore_sessions(tmp_path / "sessions.json", username)
            # Agents/Projects vor ihren Workspaces einspielen — die Workspace-
            # Freigabe richtet sich nach der (ggf. frisch wiederhergestellten)
            # DB-Ownership der jeweiligen ID.
            _restore_agents(tmp_path / "agents", username)
            _restore_owned_workspaces(tmp_path / "workspaces" / "master",
                                      settings.data_dir / "workspaces" / "master",
                                      username, is_project=False)
            _restore_owned_workspaces(tmp_path / "workspaces" / "specialists",
                                      settings.data_dir / "workspaces" / "specialists",
                                      username, is_project=False)
            _restore_projects(tmp_path / "projects", username)
            _restore_owned_workspaces(tmp_path / "workspaces" / "projects",
                                      settings.data_dir / "workspaces" / "projects",
                                      username, is_project=True)
            _restore_whatsapp(tmp_path / "whatsapp.json", username)
            _restore_butler(tmp_path / "butler", username)

    logger.info("User-Restore abgeschlossen für %s", username)


def _read_manifest(tar: tarfile.TarFile) -> dict:
    try:
        member = tar.getmember("manifest.json")
        f = tar.extractfile(member)
        return json.loads(f.read()) if f else {}
    except KeyError:
        raise UserRestoreError("backup_no_manifest")


def _restore_sessions(sessions_file: Path, username: str) -> None:
    if not sessions_file.exists():
        return
    data = json.loads(sessions_file.read_text())
    with db() as conn:
        for s in data:
            if s.get("user_id") != username:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO sessions
                   (id, agent_id, project_id, user_id, title,
                    created_at, updated_at, status, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (s["id"], s["agent_id"], s.get("project_id"), s["user_id"],
                 s.get("title"), s["created_at"], s["updated_at"],
                 s.get("status", "active"),
                 json.dumps(s.get("metadata") or {})),
            )
            for m in s.get("messages", []):
                raw = m["content"]
                content_str = raw if isinstance(raw, str) else json.dumps(raw)
                conn.execute(
                    """INSERT OR IGNORE INTO messages
                       (id, session_id, role, content, created_at,
                        token_count, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (m["id"], m["session_id"], m["role"], content_str,
                     m["created_at"], m.get("token_count"),
                     json.dumps(m.get("metadata") or {})),
                )


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _json_field(path: Path, field: str) -> str | None:
    try:
        return json.loads(path.read_text()).get(field)
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def _restore_agents(src: Path, username: str) -> None:
    """Pro Agent-ID gaten: existiert er, muss er dem User gehören; existiert er
    nicht, darf das Archiv ihn nur als dem User gehörend (re-)anlegen (#183)."""
    if not src.exists():
        return
    from hydrahive.agents import config as agent_config
    for agent_dir in src.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_id = agent_dir.name
        existing = agent_config.get(agent_id)
        if existing is not None:
            allowed = existing.get("owner") == username
        else:
            allowed = _json_field(agent_dir / "config.json", "owner") == username
        if not allowed:
            logger.warning("User-Restore: Agent '%s' übersprungen (fremder/ungültiger Owner)", agent_id)
            continue
        _copy_tree(agent_dir, settings.agents_dir / agent_id)


def _restore_projects(projects_src: Path, username: str) -> None:
    if not projects_src.exists():
        return
    from hydrahive.projects import _config_io as project_config
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    for proj_dir in projects_src.iterdir():
        if not proj_dir.is_dir():
            continue
        pid = proj_dir.name
        existing = project_config.get(pid)
        if existing is not None:
            allowed = existing.get("created_by") == username
        else:
            allowed = _json_field(proj_dir / "config.json", "created_by") == username
        if not allowed:
            logger.warning("User-Restore: Projekt '%s' übersprungen (fremder/ungültiger Owner)", pid)
            continue
        _copy_tree(proj_dir, settings.projects_dir / pid)


def _restore_owned_workspaces(src: Path, dst: Path, username: str, *, is_project: bool) -> None:
    """Workspace-Verzeichnisse nur einspielen, wenn die zugehörige Agent-/Projekt-
    ID (jetzt) dem User gehört. Läuft nach dem Agent-/Projekt-Restore."""
    if not src.exists():
        return
    if is_project:
        from hydrahive.projects import _config_io as project_config

        def _owned(eid: str) -> bool:
            return (project_config.get(eid) or {}).get("created_by") == username
    else:
        from hydrahive.agents import config as agent_config

        def _owned(eid: str) -> bool:
            return (agent_config.get(eid) or {}).get("owner") == username

    for entry in src.iterdir():
        if not entry.is_dir():
            continue
        if not _owned(entry.name):
            logger.warning("User-Restore: Workspace '%s' übersprungen (fremder Owner)", entry.name)
            continue
        _copy_tree(entry, dst / entry.name)


def _restore_whatsapp(wa_file: Path, username: str) -> None:
    if not wa_file.exists():
        return
    from hydrahive.communication.whatsapp.config import _config_file
    dst = _config_file(username)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wa_file, dst)


def _restore_butler(butler_src: Path, username: str) -> None:
    if not butler_src.exists():
        return
    from hydrahive.butler import persistence as butler_persistence
    from hydrahive.butler.models import Flow
    for flow_file in butler_src.glob("*.json"):
        try:
            flow = Flow.model_validate_json(flow_file.read_text())
            flow.owner = username
            butler_persistence.save_flow(flow, modified_by=username)
        except Exception as e:
            logger.warning("Butler-Flow %s übersprungen: %s", flow_file.name, e)
