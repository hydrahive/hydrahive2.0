from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hydrahive.api.lifespan import lifespan
from hydrahive.api.routes.agentlink import router as agentlink_router
from hydrahive.api.routes.agents import router as agents_router
from hydrahive.api.routes.agent_memory import router as agent_memory_router
from hydrahive.api.routes.workspace import router as workspace_router
from hydrahive.api.routes.analytics import router as analytics_router
from hydrahive.api.routes.auth import router as auth_router
from hydrahive.api.routes.backup import router as backup_router
from hydrahive.api.routes.buddy import router as buddy_router
from hydrahive.api.routes.butler import router as butler_router
from hydrahive.api.routes.ega import router as ega_router
from hydrahive.api.routes.fhir import router as fhir_router
from hydrahive.api.routes.files import router as files_router
from hydrahive.api.routes.communication import router as communication_router
from hydrahive.api.routes.communication_whatsapp import router as communication_whatsapp_router
from hydrahive.api.routes.communication_discord import router as communication_discord_router
from hydrahive.api.routes.container_console import router as container_console_router
from hydrahive.api.routes.containers import router as containers_router
from hydrahive.api.routes.credentials import router as credentials_router
from hydrahive.api.routes.research_apis import router as research_apis_router
from hydrahive.api.routes.extensions import router as extensions_router
from hydrahive.api.routes.dashboard import router as dashboard_router
from hydrahive.api.routes.datamining import router as datamining_router
from hydrahive.api.routes.datamining_issues import router as datamining_issues_router
from hydrahive.api.routes.datamining_stats import router as datamining_stats_router
from hydrahive.api.routes.datamining_transfer import router as datamining_transfer_router
from hydrahive.api.routes.external_instances import router as external_instances_router
from hydrahive.api.routes.llm import router as llm_router
from hydrahive.api.routes.llm_catalog import router as llm_catalog_router
from hydrahive.api.routes.llm_oauth import router as llm_oauth_router
from hydrahive.api.routes.mcp import router as mcp_router
from hydrahive.api.routes.plugins import router as plugins_router
from hydrahive.api.routes.projects import router as projects_router
from hydrahive.api.routes.projects_info import router as projects_info_router
from hydrahive.api.routes.projects_files import router as projects_files_router
from hydrahive.api.routes.projects_files_write import router as projects_files_write_router
from hydrahive.api.routes.projects_git import router as projects_git_router
from hydrahive.api.routes.projects_samba import router as projects_samba_router
from hydrahive.api.routes.projects_servers import router as projects_servers_router
from hydrahive.api.routes.sessions import router as sessions_router
from hydrahive.api.routes.skills import router as skills_router
from hydrahive.api.routes.stt import router as stt_router
from hydrahive.api.routes.system import router as system_router
from hydrahive.api.routes.system_admin import router as system_admin_router
from hydrahive.api.routes.system_bridge import router as system_bridge_router
from hydrahive.api.routes.system_samba import router as system_samba_router
from hydrahive.api.routes.system_settings import router as system_settings_router
from hydrahive.api.routes.tailscale import router as tailscale_router
from hydrahive.api.routes.tts import router as tts_router
from hydrahive.api.routes.zahnfee import router as zahnfee_router
from hydrahive.api.routes.users import router as users_router
from hydrahive.api.routes.federation import router as federation_router
from hydrahive.api.routes.streaming import router as streaming_router
from hydrahive.api.routes.teamchat import router as teamchat_router
from hydrahive.api.routes.modules import router as modules_admin_router
from hydrahive.api.routes.health_data import router as health_data_router
from hydrahive.api.routes.vms import router as vms_router
from hydrahive.api.version import current_status
from hydrahive import modules as _modules

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

app.include_router(agentlink_router)
app.include_router(auth_router)
app.include_router(backup_router)
app.include_router(users_router)
app.include_router(agents_router)
app.include_router(workspace_router)
app.include_router(external_instances_router)
app.include_router(agent_memory_router)
app.include_router(analytics_router)
app.include_router(communication_router)
app.include_router(communication_whatsapp_router)
app.include_router(communication_discord_router)
app.include_router(llm_router)
app.include_router(llm_catalog_router)
app.include_router(llm_oauth_router)
app.include_router(mcp_router)
app.include_router(plugins_router)
app.include_router(projects_router)
app.include_router(projects_info_router)
app.include_router(projects_files_router)
app.include_router(projects_files_write_router)
app.include_router(projects_git_router)
app.include_router(projects_samba_router)
app.include_router(projects_servers_router)
app.include_router(sessions_router)
app.include_router(skills_router)
app.include_router(stt_router)
app.include_router(tts_router)
app.include_router(vms_router)
app.include_router(containers_router)
app.include_router(credentials_router)
app.include_router(research_apis_router)
app.include_router(extensions_router)
app.include_router(dashboard_router)
app.include_router(datamining_router)
app.include_router(datamining_issues_router)
app.include_router(datamining_stats_router)
app.include_router(datamining_transfer_router)
app.include_router(container_console_router)
app.include_router(butler_router)
app.include_router(buddy_router)
app.include_router(files_router)
app.include_router(system_router)
app.include_router(system_admin_router)
app.include_router(system_bridge_router)
app.include_router(system_samba_router)
app.include_router(system_settings_router)
app.include_router(tailscale_router)
app.include_router(zahnfee_router)
app.include_router(federation_router)
app.include_router(streaming_router)
app.include_router(teamchat_router)
app.include_router(modules_admin_router)
app.include_router(health_data_router)
app.include_router(fhir_router)
app.include_router(ega_router)


def mount_module_routers(target_app: FastAPI) -> None:
    """Hängt die Router aller erfolgreich geladenen Module ein (Prefix pro Modul).
    Wird im Lifespan nach modules.load_all() aufgerufen (REGISTRY ist beim Import leer).
    Fehler beim Einhängen eines Moduls werden isoliert — sie dürfen den Start nicht abbrechen."""
    for entry in _modules.REGISTRY.values():
        if not (entry.loaded and entry.ctx):
            continue
        for r in entry.ctx.routers:
            try:
                target_app.include_router(r, prefix=f"/api/modules/{entry.manifest.id}")
            except Exception as exc:
                logger.error("Modul '%s': include_router fehlgeschlagen — übersprungen: %s",
                             entry.manifest.id, exc)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "internal_error"}},
    )


@app.get("/api/health")
def health() -> dict:
    commit, behind = current_status()
    return {
        "status": "ok",
        "version": "2.0.0",
        "commit": commit,
        "update_behind": behind,
    }


def run() -> None:
    """Python-Entrypoint (console_script `hydrahive`). Liest Host/Port aus den
    Settings — konsistent mit dem Installer, der dieselben HH_HOST/HH_PORT-Env-
    Vars an die uvicorn-CLI gibt (#198). Der frühere Script zeigte auf das
    ASGI-App-Objekt statt auf ein Callable und war damit nicht startbar."""
    import uvicorn

    from hydrahive.settings import settings
    uvicorn.run("hydrahive.api.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
