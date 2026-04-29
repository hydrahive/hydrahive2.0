from __future__ import annotations

import asyncio
import logging
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hydrahive.agents import bootstrap as agent_bootstrap
from hydrahive.api.middleware.users import ensure_admin
from hydrahive import plugins as plugin_system
from hydrahive.api.routes.agents import router as agents_router
from hydrahive.api.routes.auth import router as auth_router
from hydrahive.api.routes.communication import router as communication_router
from hydrahive.api.routes.llm import router as llm_router
from hydrahive.api.routes.mcp import router as mcp_router
from hydrahive.api.routes.plugins import router as plugins_router
from hydrahive.api.routes.projects import router as projects_router
from hydrahive.api.routes.sessions import router as sessions_router
from hydrahive.api.routes.stt import router as stt_router
from hydrahive.api.routes.system import router as system_router, set_start_time
from hydrahive.api.routes.users import router as users_router
from hydrahive.communication import register as register_channel
from hydrahive.communication.whatsapp import (
    BridgeProcess,
    WhatsAppAdapter,
    ensure_secret,
)
from hydrahive.db import init_db
from hydrahive.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    import secrets
    settings.ensure_dirs()
    init_db()
    # First-Run: Admin-Passwort entweder aus ENV oder Random-Generated und ins Log.
    # Niemals "changeme" als Default — Login-by-Default-Credentials wäre verwundbar.
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
    set_start_time()
    update_task = asyncio.create_task(_update_check_loop())

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
        else:
            wa_bridge = None

    logger.info("HydraHive2 gestartet — Port %s", settings.port)
    yield
    if wa_adapter:
        await wa_adapter.aclose()
    if wa_bridge:
        await wa_bridge.stop()
    update_task.cancel()
    logger.info("HydraHive2 beendet")


import os
_DOCS_ENABLED = os.environ.get("HH_ENABLE_DOCS", "").lower() in ("1", "true", "yes")

app = FastAPI(
    title="HydraHive2",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if _DOCS_ENABLED else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if _DOCS_ENABLED else None,
)

_cors_origins_env = os.environ.get("HH_CORS_ORIGINS", "").strip()
_cors_origins = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(agents_router)
app.include_router(communication_router)
app.include_router(llm_router)
app.include_router(mcp_router)
app.include_router(plugins_router)
app.include_router(projects_router)
app.include_router(sessions_router)
app.include_router(stt_router)
app.include_router(system_router)


_REPO_ROOT = Path(__file__).resolve().parents[4]


def _detect_git_commit() -> str | None:
    if not (_REPO_ROOT / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _check_update_behind() -> int | None:
    """Returns 0 if HEAD == origin/main, 1 if behind, None if undetectable.

    Uses git ls-remote (read-only, no .git writes) so it works even when
    the systemd-Unit has ProtectSystem=strict and the repo dir is RO.
    Trade-off: we can detect "update yes/no" but not the exact commit-count.
    """
    if not (_REPO_ROOT / ".git").exists():
        return None
    try:
        ls = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "ls-remote", "origin", "main"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if ls.returncode != 0 or not ls.stdout.strip():
            return None
        remote_sha = ls.stdout.split()[0]
        head = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if head.returncode != 0:
            return None
        local_sha = head.stdout.strip()
        return 0 if local_sha == remote_sha else 1
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


_GIT_COMMIT: str | None = _detect_git_commit()
_UPDATE_BEHIND: int | None = None


async def _update_check_loop() -> None:
    global _UPDATE_BEHIND, _GIT_COMMIT
    while True:
        try:
            _GIT_COMMIT = await asyncio.to_thread(_detect_git_commit)
            _UPDATE_BEHIND = await asyncio.to_thread(_check_update_behind)
        except Exception as e:
            logger.debug("Update-Check fehlgeschlagen: %s", e)
        await asyncio.sleep(300)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "2.0.0",
        "commit": _GIT_COMMIT,
        "update_behind": _UPDATE_BEHIND,
    }
