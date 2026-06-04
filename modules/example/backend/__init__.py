"""Beispiel-Modul Backend — Walking Skeleton.

Beweist das volle Modul-Vertragsmodell: register(ctx) → Router + Migrationen.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db.connection import db

router = APIRouter()


class NoteIn(BaseModel):
    text: str


@router.get("/notes", dependencies=[Depends(require_auth)])
def list_notes() -> list[dict]:
    with db() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT id, text, created_at FROM module_example_notes ORDER BY id DESC"
            ).fetchall()
        ]


@router.post("/notes", dependencies=[Depends(require_auth)])
def add_note(body: NoteIn) -> dict:
    with db() as c:
        cur = c.execute(
            "INSERT INTO module_example_notes (text) VALUES (?)", (body.text,)
        )
        return {"id": cur.lastrowid, "text": body.text}


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
