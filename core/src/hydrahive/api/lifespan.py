"""Lifespan-Logik (Startup/Shutdown) der FastAPI-App.

Ausgelagert aus main.py damit main.py reine App-Definition bleibt.
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI

from hydrahive.agents import bootstrap as agent_bootstrap
from hydrahive.agentlink import client as agentlink_client
from hydrahive.runner import handoff_receiver
from hydrahive.api.middleware.users import ensure_admin
from hydrahive.api.routes.system import set_start_time
from hydrahive.api.version import update_check_loop
from hydrahive.butler.registry import load_builtins as load_butler_builtins
from hydrahive.communication import register as register_channel
from hydrahive.communication.discord import DiscordAdapter
from hydrahive.communication.whatsapp import (
    BridgeProcess,
    WhatsAppAdapter,
    ensure_secret,
)
from hydrahive.containers import reconciler as container_reconciler
from hydrahive.zahnfee import scheduler as zahnfee_scheduler
from hydrahive.db import init_db
from hydrahive.db import mirror as pg_mirror
from hydrahive import plugins as plugin_system
from hydrahive.settings import settings
from hydrahive.vms import reconciler as vm_reconciler

logger = logging.getLogger(__name__)


async def _whatsapp_auto_reconnect(adapter: WhatsAppAdapter) -> None:
    """Reconnect alle User die bereits gepaart waren (auth/creds.json existiert)
    automatisch nach Backend-Restart. Bridge wartet kurz bis sie HTTP-ready ist."""
    await asyncio.sleep(2)
    wa_dir = settings.whatsapp_data_dir
    if not wa_dir.exists():
        return
    for user_dir in wa_dir.iterdir():
        if not user_dir.is_dir():
            continue
        if not (user_dir / "auth" / "creds.json").exists():
            continue
        username = user_dir.name
        try:
            await adapter.connect(username)
            logger.info("WhatsApp: Auto-Reconnect für '%s' getriggert", username)
        except Exception as e:
            logger.warning("WhatsApp Auto-Reconnect für '%s' fehlgeschlagen: %s", username, e)


async def _agentlink_heartbeat_loop(stop: asyncio.Event) -> None:
    """Register all active HydraHive agents with AgentLink and send heartbeats every 60s."""
    from hydrahive.agents._config_utils import list_all as list_all_agents

    while not stop.is_set():
        try:
            for agent in list_all_agents():
                if agent.get("status") != "active":
                    continue
                try:
                    await agentlink_client.register_agent(
                        agent_id=agent["id"],
                        name=agent.get("name", agent["id"]),
                        agent_type=agent.get("type"),
                        owner=agent.get("owner"),
                    )
                except Exception as e:
                    logger.debug("AgentLink register für %s fehlgeschlagen: %s", agent.get("name"), e)
        except Exception as e:
            logger.warning("AgentLink heartbeat-loop Fehler: %s", e)
        try:
            await asyncio.wait_for(stop.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    if settings.pg_mirror_dsn:
        await pg_mirror.init()
    from hydrahive.skills.loader import install_system_defaults
    install_system_defaults()
    initial_pw = os.environ.get("HH_INITIAL_ADMIN_PASSWORD") or secrets.token_urlsafe(16)
    user_was_new = ensure_admin("admin", initial_pw)
    if user_was_new:
        # Schreibe in Datei damit install.sh es robust auslesen kann (kein
        # journalctl-Race, kein Log-Rotation-Verlust). Datei wird vom Installer
        # gelesen und gelöscht. Mode 0600 — nur root liest.
        try:
            pw_file = settings.config_dir / ".admin_initial_password"
            settings.config_dir.mkdir(parents=True, exist_ok=True)
            pw_file.write_text(initial_pw + "\n")
            os.chmod(pw_file, 0o600)
        except OSError as e:
            logger.warning("Konnte initial password file nicht schreiben: %s", e)
        logger.warning(
            "============================================================\n"
            "  Erster Start — Admin-User angelegt:\n"
            "    Username: admin\n"
            "    Passwort: %s\n"
            "  ↑ Dieses Passwort wird NUR EINMAL angezeigt — bitte sichern.\n"
            "  Bei Bedarf via HH_INITIAL_ADMIN_PASSWORD Env-Var vorgeben.\n"
            "============================================================",
            initial_pw,
        )
    agent_bootstrap.ensure_master("admin")
    agent_bootstrap.migrate_tools()
    plugin_system.load_all()
    from hydrahive.llm import registry as llm_registry
    # Hintergrund-Warm: blockiert den Start nicht (Provider-Fetch-Timeouts);
    # validate ist failopen während des kurzen kalten Fensters.
    asyncio.create_task(llm_registry.awarm())
    load_butler_builtins()
    set_start_time()

    if settings.update_check_enabled:
        update_task: asyncio.Task[None] | None = asyncio.create_task(update_check_loop())
    else:
        update_task = None
        logger.info("Update-Check deaktiviert (HH_UPDATE_CHECK_ENABLED=false)")
    zahnfee_stop = asyncio.Event()
    zahnfee_task = asyncio.create_task(zahnfee_scheduler.run_loop(zahnfee_stop))
    vm_reconciler_stop = asyncio.Event()
    vm_reconciler_task = asyncio.create_task(vm_reconciler.run_loop(vm_reconciler_stop))
    container_reconciler_stop = asyncio.Event()
    container_reconciler_task = asyncio.create_task(
        container_reconciler.run_loop(container_reconciler_stop)
    )

    mail_stop: asyncio.Event | None = None
    mail_task: asyncio.Task[None] | None = None
    if settings.mail_enabled:
        from hydrahive.communication.mail import watcher as mail_watcher
        mail_stop = asyncio.Event()
        mail_task = asyncio.create_task(mail_watcher.run_loop(mail_stop))

    # AgentLink-WS-Listener: persistent connection, subscribed auf agent:{my_id},
    # routet handoff_received-Events via Future-Map an wartende ask_agent-Calls.
    if settings.agentlink_url:
        async def _on_event(event):
            # handoff_received → schau ob jemand auf den Antwort-State wartet.
            # AgentLink schickt state_id im Event; wir laden den State und prüfen
            # ob die handoff.reason ein "reply_to:<id>" enthält.
            if event.type != "handoff_received" or not event.state_id:
                return
            try:
                state = await agentlink_client.get_state(event.state_id)
            except Exception as e:
                logger.warning("AgentLink: get_state(%s) fehlgeschlagen: %s", event.state_id, e)
                return
            if not state or not state.handoff:
                return
            reason = state.handoff.reason or ""
            if reason.startswith("reply_to:"):
                reply_to = reason.split(":", 1)[1].strip()
                if agentlink_client.resolve_pending(reply_to, state):
                    logger.info("AgentLink: Antwort-State auf %s eingetroffen", reply_to)
            else:
                asyncio.create_task(handoff_receiver.handle(event), name=f"handoff-{event.state_id}")

        agentlink_client.start_listener(_on_event)
        agentlink_stop = asyncio.Event()
        agentlink_heartbeat_task: asyncio.Task[None] | None = asyncio.create_task(
            _agentlink_heartbeat_loop(agentlink_stop)
        )
    else:
        agentlink_stop = None
        agentlink_heartbeat_task = None

    discord_adapter: DiscordAdapter | None = None
    if settings.discord_enabled:
        discord_adapter = DiscordAdapter()
        register_channel(discord_adapter)
        asyncio.create_task(discord_adapter.auto_reconnect_all())

    wa_bridge: BridgeProcess | None = None
    wa_adapter: WhatsAppAdapter | None = None
    if settings.whatsapp_enabled:
        wa_secret = ensure_secret(settings.whatsapp_bridge_secret_file)
        wa_bridge = BridgeProcess(
            port=settings.whatsapp_bridge_port,
            data_dir=settings.whatsapp_data_dir,
            backend_url=settings.backend_internal_url,
            secret=wa_secret,
        )
        if await wa_bridge.start():
            wa_adapter = WhatsAppAdapter(settings.whatsapp_bridge_url, wa_secret)
            register_channel(wa_adapter)
            asyncio.create_task(_whatsapp_auto_reconnect(wa_adapter))
        else:
            wa_bridge = None

    logger.info("HydraHive2 gestartet — Port %s", settings.port)
    yield

    await pg_mirror.close()
    if discord_adapter:
        await discord_adapter.aclose()
    if wa_adapter:
        await wa_adapter.aclose()
    if wa_bridge:
        await wa_bridge.stop()
    if update_task is not None:
        update_task.cancel()
    if agentlink_stop is not None:
        agentlink_stop.set()
    if agentlink_heartbeat_task is not None:
        try:
            await asyncio.wait_for(agentlink_heartbeat_task, timeout=3.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            agentlink_heartbeat_task.cancel()
    zahnfee_stop.set()
    vm_reconciler_stop.set()
    container_reconciler_stop.set()
    if mail_stop is not None:
        mail_stop.set()
    await agentlink_client.stop_listener()
    shutdown_tasks = [zahnfee_task, vm_reconciler_task, container_reconciler_task]
    if mail_task is not None:
        shutdown_tasks.append(mail_task)
    for task in shutdown_tasks:
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()
    logger.info("HydraHive2 beendet")
