from __future__ import annotations
from fastapi import APIRouter


class ModuleContext:
    """Was ein Modul beim register() registrieren kann."""

    def __init__(self, module_id: str) -> None:
        self.module_id = module_id
        self.routers: list[APIRouter] = []
        self.migrations_rel: str | None = None
        self.service_rel: str | None = None

    def register_router(self, router: APIRouter) -> None:
        self.routers.append(router)

    def register_migrations(self, rel_dir: str) -> None:
        self.migrations_rel = rel_dir

    def register_service(self, rel_dir: str) -> None:
        self.service_rel = rel_dir
