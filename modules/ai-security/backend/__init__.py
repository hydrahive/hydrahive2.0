"""AI-Security-Modul: authentifizierter, begrenzter AI-Infra-Guard-Adapter."""
from __future__ import annotations

from .jobs import poll_scans
from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    ctx.register_job(
        "poll_scans",
        poll_scans,
        interval_seconds=5.0,
        initial_delay_seconds=10.0,
    )
