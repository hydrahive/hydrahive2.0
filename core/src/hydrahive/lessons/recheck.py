"""Bestand nachprüfen (Spec 10d): aktive Lehren gegen ihren Verlauf gegenprüfen; nicht belegte → `contested`.

Lehren mit `contested` werden nicht mehr gezeigt (recall nimmt nur `active`). Nichts wird gelöscht.
Aufruf: python -m hydrahive.lessons.recheck [--undo]
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from hydrahive.lessons import check, prompt, store

logger = logging.getLogger(__name__)


def _model() -> str:
    from hydrahive.llm._config import resolve_lessons_model
    return resolve_lessons_model()


def _messages(session_id: str):
    from hydrahive.db import messages
    return messages.list_for_session(session_id)


async def _complete(msgs: list[dict], model: str | None = None, temperature: float = 0.0, max_tokens: int = 300) -> str:
    from hydrahive.llm import client
    return await client.complete(msgs, model=model, temperature=temperature, max_tokens=max_tokens)


def _agents(agents_dir: Path) -> list[str]:
    return sorted(p.parent.name for p in Path(agents_dir).glob("*/lessons.jsonl"))


async def _one(lesson: dict, llm: str) -> bool | None:
    rec = prompt.record(_messages(lesson["session_id"]), budget=10**9)        # ganzer Verlauf, Fenster schneidet
    around = check.window(rec, lesson["quote"])
    if not around:
        return False                                                        # Zitat gar nicht (mehr) im Verlauf
    raw = await asyncio.wait_for(_complete(check.messages(lesson, around), model=llm), timeout=check.TIMEOUT)
    return check.verdict(raw)


async def run(agents_dir: Path, *, undo: bool = False) -> dict:
    if undo:
        restored = 0
        for aid in _agents(agents_dir):
            for row in store.current(aid):
                if row.get("status") == "contested" and row.get("contested_by") == "recheck":
                    store.set_status(aid, row["id"], "active", by="")
                    restored += 1
        return {"restored": restored}
    llm = _model()
    res = {"checked": 0, "contested": 0, "kept": 0, "errors": 0}
    if not llm:
        return res
    for aid in _agents(agents_dir):
        for row in store.current(aid):
            if row.get("status") != "active":
                continue
            res["checked"] += 1
            try:
                ok = await _one(row, llm)
            except Exception as e:  # noqa: BLE001 – eine Lehre darf den Lauf nicht abbrechen
                logger.warning("recheck: %s/%s fehlgeschlagen: %s", aid, row["id"], e)
                ok = None
            if ok is None:
                res["errors"] += 1
            elif ok:
                res["kept"] += 1
            else:
                store.set_status(aid, row["id"], "contested", by="recheck")
                res["contested"] += 1
    return res


if __name__ == "__main__":  # pragma: no cover
    from hydrahive.settings import settings
    logging.basicConfig(level=logging.INFO)
    logger.info("recheck: %s", asyncio.run(run(settings.agents_dir, undo="--undo" in sys.argv)))
