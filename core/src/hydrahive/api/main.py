from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hydrahive.api.lifespan import lifespan
from hydrahive.api.routes.agents import router as agents_router
from hydrahive.api.routes.auth import router as auth_router
from hydrahive.api.routes.backup import router as backup_router
from hydrahive.api.routes.butler import router as butler_router
from hydrahive.api.routes.communication import router as communication_router
from hydrahive.api.routes.container_console import router as container_console_router
from hydrahive.api.routes.containers import router as containers_router
from hydrahive.api.routes.llm import router as llm_router
from hydrahive.api.routes.mcp import router as mcp_router
from hydrahive.api.routes.plugins import router as plugins_router
from hydrahive.api.routes.projects import router as projects_router
from hydrahive.api.routes.sessions import router as sessions_router
from hydrahive.api.routes.stt import router as stt_router
from hydrahive.api.routes.system import router as system_router
from hydrahive.api.routes.tts import router as tts_router
from hydrahive.api.routes.users import router as users_router
from hydrahive.api.routes.vms import router as vms_router
from hydrahive.api.version import current_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

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
app.include_router(backup_router)
app.include_router(users_router)
app.include_router(agents_router)
app.include_router(communication_router)
app.include_router(llm_router)
app.include_router(mcp_router)
app.include_router(plugins_router)
app.include_router(projects_router)
app.include_router(sessions_router)
app.include_router(stt_router)
app.include_router(tts_router)
app.include_router(vms_router)
app.include_router(containers_router)
app.include_router(container_console_router)
app.include_router(butler_router)
app.include_router(system_router)


@app.get("/api/health")
def health() -> dict:
    commit, behind = current_status()
    return {
        "status": "ok",
        "version": "2.0.0",
        "commit": commit,
        "update_behind": behind,
    }
