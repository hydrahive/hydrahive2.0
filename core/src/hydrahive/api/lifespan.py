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
from hydrahive.api.middleware.users import ensure_admin
from hydrahive.api.routes.system import set_start_time
from hydrahive.api.version import update_check_loop
from hydrahive.butler.registry import load_builtins as load_butler_builtins
from hydrahive.communication import register as register_channel
from hydrahive.communication.whatsapp import (
    BridgeProcess,
    WhatsAppAdapter,
    ensure_secret,
)
from hydrahive.containers import reconciler as container_reconciler
from hydrahive.db import init_db
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    initial_pw = os.environ.get("HH_INITIAL_ADMIN_PASSWORD") or secrets.token_urlsafe(16)
    user_was_new = ensure_admin("admin", initial_pw)
    if user_was_new:
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
    plugin_system.load_all()
    load_butler_builtins()
    set_start_time()

    update_task = asyncio.create_task(update_check_loop())
    vm_reconciler_stop = asyncio.Event()
    vm_reconciler_task = asyncio.create_task(vm_reconciler.run_loop(vm_reconciler_stop))
    container_reconciler_stop = asyncio.Event()
    container_reconciler_task = asyncio.create_task(
        container_reconciler.run_loop(container_reconciler_stop)
    )

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

        agentlink_client.start_listener(_on_event)

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
            wa_adapter = WhatsAppAdapter(settings.whatsapp_bridge_url)
            register_channel(wa_adapter)
            asyncio.create_task(_whatsapp_auto_reconnect(wa_adapter))
        else:
            wa_bridge = None

    logger.info("HydraHive2 gestartet — Port %s", settings.port)
    yield

    if wa_adapter:
        await wa_adapter.aclose()
    if wa_bridge:
        await wa_bridge.stop()
    update_task.cancel()
    vm_reconciler_stop.set()
    container_reconciler_stop.set()
    await agentlink_client.stop_listener()
    for task in (vm_reconciler_task, container_reconciler_task):
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()
    logger.info("HydraHive2 beendet")
