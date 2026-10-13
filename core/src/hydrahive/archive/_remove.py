"""Schritt 6 „Löschen“ (Spec archiv-system.md, Etappe 2). Jede Funktion ist wiederholbar:
Bricht der Dienst mitten drin ab, macht ein zweiter Aufruf nach dem Neustart einfach weiter.
"""
from __future__ import annotations

import logging
import shutil

from hydrahive.agents import config as agent_config
from hydrahive.archive import _bundle
from hydrahive.archive.safe_rm import remove_tree

logger = logging.getLogger(__name__)


def sessions(session_ids: list[str]) -> None:
    """Chats aus sessions.db (Nachrichten, Werkzeugaufrufe, Läufe hängen per ON DELETE CASCADE dran).
    Das Datamining behält seine Kopie (Entscheidung 1)."""
    from hydrahive.db import sessions as sessions_db
    for sid in session_ids:
        sessions_db.delete(sid)


def agent(agent_id: str) -> None:
    """Agent samt Gedächtnis und eigenem Arbeitsordner (agent_config.delete nimmt ihn seit Etappe 2 mit)."""
    agent_config.delete(agent_id)


def unhook_sessions(session_ids: list[str]) -> None:
    from hydrahive.db import sessions as sessions_db
    for sid in session_ids:
        sessions_db.set_project(sid, None)


def disconnect_channels(username: str) -> None:
    """Laufende Discord-/WhatsApp-Verbindung des Nutzers trennen, bevor seine Daten weg sind."""
    from hydrahive.archive import jobs
    from hydrahive.communication import get
    for name in ("discord", "whatsapp"):
        ch = get(name)
        if ch is None:
            continue
        try:
            jobs.run_async(ch.disconnect(username), timeout=15)
        except Exception:  # noqa: BLE001 – Kanal weg/Bridge aus: Daten werden trotzdem entfernt
            logger.warning("Kanal %s für %s ließ sich nicht trennen", name, username, exc_info=True)


def user_data(username: str, user_id: str) -> None:
    """Alles, was am Namen oder an der ID hängt, außer Agenten, Projekten und Chats (Fehler 2)."""
    disconnect_channels(username)
    from hydrahive.api.middleware import api_keys
    from hydrahive.butler import persistence as butler
    from hydrahive.communication.discord.config import _config_file as discord_file
    from hydrahive.communication.whatsapp.config import _config_file as wa_file
    from hydrahive.credentials import store as cred_store
    from hydrahive.settings import settings
    from hydrahive.skills._paths import user_dir
    from hydrahive.zahnfee.storage import _path as zahnfee_file

    for cred in cred_store.list_credentials(username):
        cred_store.delete_credential(username, cred.name)     # entfernt auch SSH-Schlüssel-Dateien
    cred_store._file_for(username).unlink(missing_ok=True)
    for flow in butler.list_flows(owner=username):
        butler.delete_flow(username, flow.flow_id)
    remove_tree(user_dir(username).parent)                  # data/users/<name> (Skills)
    for f in (discord_file(username), wa_file(username), zahnfee_file(username)):
        f.unlink(missing_ok=True)
    wa_login = settings.whatsapp_data_dir / username       # Baileys-Login – sonst erbt ein Namensvetter das Konto
    if wa_login.is_dir() and wa_login.parent == settings.whatsapp_data_dir:
        shutil.rmtree(wa_login, ignore_errors=True)
    api_keys.delete_for_user(username)
    _user_rows(username, user_id)


def _user_rows(username: str, user_id: str) -> None:
    from hydrahive.db.connection import db
    with db() as conn:
        for table, column, key in _bundle.USER_TABLES:
            if _bundle._table_exists(conn, table):
                conn.execute(f"DELETE FROM {table} WHERE {column} = ?", (username if key == "name" else user_id,))


def memberships(username: str, projects: list[dict]) -> None:
    from hydrahive.projects import members
    for p in projects:
        try:
            members.remove(p["id"], username)
        except KeyError:
            pass


def hand_over_agents(agents: list[dict]) -> None:
    """Agenten des Nutzers in fremden Projekten gehören zum Projekt → an dessen Ersteller."""
    from hydrahive.projects import config as project_config
    for a in agents:
        project = project_config.get(a.get("project_id") or "") or {}
        new_owner = project.get("created_by")
        if new_owner:
            agent_config.update(a["id"], owner=new_owner)
            logger.info("Agent %s geht an %s (Projekt %s)", a["id"], new_owner, project.get("id"))
        else:
            agent_config.delete(a["id"])


def account(username: str, user_id: str, actor_id: str) -> None:
    from hydrahive.access import store as access_store
    from hydrahive.api.middleware import users
    users.delete(username)
    access_store.purge_user(user_id, actor_id=actor_id)
