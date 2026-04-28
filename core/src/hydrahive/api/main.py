from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.users import ensure_admin
from hydrahive.api.routes.agents import router as agents_router
from hydrahive.api.routes.auth import router as auth_router
from hydrahive.api.routes.llm import router as llm_router
from hydrahive.api.routes.users import router as users_router
from hydrahive.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    ensure_admin("admin", "changeme")
    agent_config.ensure_master("admin")
    logger.info("HydraHive2 gestartet — Port %s", settings.port)
    yield
    logger.info("HydraHive2 beendet")


app = FastAPI(
    title="HydraHive2",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(agents_router)
app.include_router(llm_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "2.0.0"}
