"""Deep-Research-Modul Backend.

register(ctx) →
  - Router    /api/modules/deepresearch/runs*
  - Tool      deep_research
  - Migration 001_deepresearch.sql
"""
from __future__ import annotations

from .routes import router
from .tools import research_run


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_tool(research_run.TOOL)
    ctx.register_migrations("migrations")
