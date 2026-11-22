"""Client: Katalog-Metadaten an den Hub schicken (docs/specs/federation-catalog.md §Ablauf 2 + 3).

Ein Lauf (``sync``) wird vom Timer, vom Event-Push oder von „Jetzt abgleichen“
gestartet (Einbindung: Teilstück S5). Alle Läufe teilen sich EINE Sperre: es
läuft immer nur ein Versand, Nachrichten gehen streng nacheinander mit
steigender ``seq`` raus, mit mindestens ``GAP_SECONDS`` Abstand (Rate-Limit des
Hubs 30/min). Der Cursor rückt erst vor, wenn ALLE Nachrichten des Laufs
bestätigt sind; bricht der Lauf ab, wiederholt ihn der nächste.

Ohne aktiven Hub, ohne ``enabled`` oder ohne Nutzerauswahl entsteht kein
Netzverkehr. Was geschickt wird, plant ``catalog_plan``.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.db._utils import now_iso
from hydrahive.federation import catalog_plan
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.catalog_plan import KINDS, Plan
from hydrahive.federation.peer_inbound import send_signed

logger = logging.getLogger(__name__)

PUSH_PATH = "/api/peering/catalog/push"
GAP_SECONDS = 2.0          # Abstand zwischen Nachrichten eines Laufs (Tests setzen 0)
FULL_EVERY_RUNS = 12       # jeder zwölfte Timer-Lauf ist ein Abgleich …
FULL_MAX_AGE = timedelta(minutes=60)   # … oder einer, der > 60 min nach last_full_at kommt

_locks: dict[int, asyncio.Lock] = {}


def _lock() -> asyncio.Lock:
    """EINE Sperre für Timer, Event-Push und „Jetzt abgleichen“ (je Event-Loop)."""
    loop = asyncio.get_running_loop()
    lock = _locks.get(id(loop))
    if lock is None:
        _locks.clear()  # alte Loops (Tests, Neustart) vergessen
        lock = _locks[id(loop)] = asyncio.Lock()
    return lock


class SyncFailed(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


def full_due(last_full_at: str | None, timer_runs: int, now: datetime | None = None) -> bool:
    """Ist der stündliche Abgleich fällig? (jeder 12. Timer-Lauf oder > 60 min her)."""
    if timer_runs > 0 and timer_runs % FULL_EVERY_RUNS == 0:
        return True
    if not last_full_at:
        return True
    try:
        last = datetime.fromisoformat(last_full_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - last > FULL_MAX_AGE


def _json(response) -> dict:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


async def send_message(
    hub: dict, interval: int, items: list, deleted: list, full: dict | None,
    *, shared: bool = False, remote_edits: bool = False,
) -> list[dict]:
    """Eine Nachricht senden und das Ack prüfen. Rückgabe: ``resync``-Liste.

    ``peer_replay`` mit ``last_seq`` (z. B. nach Backup-Restore): einmal auf
    ``last_seq + 1`` springen und wiederholen. Wirft SyncFailed(Code).

    ``shared``/``remote_edits``: eigene Schalter (docs/specs/federation-shared-
    tasks.md §Schalter), in jedem Push mitgemeldet.
    """
    for attempt in range(2):
        seq = await asyncio.to_thread(client_db.next_seq)
        payload = proto.new_catalog_push(
            seq, interval, items, deleted, full, shared=shared, remote_edits=remote_edits,
        )
        try:
            response = await send_signed(hub, PUSH_PATH, payload)
        except httpx.HTTPStatusError as e:
            detail = _json(e.response).get("detail")
            detail = detail if isinstance(detail, dict) else {}
            code = detail.get("code") or f"http_{e.response.status_code}"
            last = (detail.get("params") or {}).get("last_seq")
            if code == "peer_replay" and isinstance(last, int) and not isinstance(last, bool) and attempt == 0:
                await asyncio.to_thread(client_db.raise_seq_to, last)
                continue
            raise SyncFailed(code) from e
        except httpx.HTTPError as e:
            raise SyncFailed("hub_unreachable", str(e)) from e
        body = _json(response)
        if body.get("ack_seq") != seq:
            raise SyncFailed("hub_bad_ack", f"ack {body.get('ack_seq')!r} statt {seq}")
        return [x for x in body.get("resync") or [] if isinstance(x, dict)]
    raise SyncFailed("peer_replay")


async def sync(
    *,
    pairs: set[tuple[str, str]] | None = None,
    entries: list[tuple[str, str, str]] | tuple = (),
    full: bool = False,
    heartbeat: bool = True,
    reason: str = "timer",
) -> str:
    """Ein Versand-Lauf unter der gemeinsamen Sperre. Wirft nie.

    ``pairs``: (Nutzer, Art), deren Delta geschickt wird; None = alle
    ausgewählten Nutzer × beide Arten (Timer, Überlauf). ``entries``: Vormerkungen
    aus ``catalog_changes.drain()`` (für ``deleted``). ``full``: Abgleichsliste
    mitschicken. ``heartbeat``: auch ohne Änderungen eine leere Nachricht senden.
    Rückgabe: ``ok`` · ``inactive`` (kein Netzverkehr) · Fehlercode.
    """
    async with _lock():
        try:
            cfg = await asyncio.to_thread(client_db.load_config)
        except Exception as e:
            logger.warning("Katalog-Sync: Einstellungen nicht lesbar: %s", e)
            return "sync_failed"
        if not cfg.active:
            return "inactive"
        users = set(cfg.users)
        wanted = {(u, k) for u in users for k in KINDS} if pairs is None else {
            p for p in pairs if p[0] in users and p[1] in KINDS}
        chosen = [e for e in entries if len(e) == 3 and e[1] in users and e[0] in KINDS]
        try:
            plan = await asyncio.to_thread(catalog_plan.build_plan, cfg, pairs=wanted, entries=chosen, full=full)
            msgs = catalog_plan.messages(plan, heartbeat=heartbeat)
            resync = await _send_all(cfg, msgs)
        except SyncFailed as e:
            logger.info("Katalog-Sync (%s) fehlgeschlagen: %s", reason, e)
            await asyncio.to_thread(client_db.record_status, error=e.code)
            return e.code
        except Exception as e:
            logger.warning("Katalog-Sync (%s) unerwartet fehlgeschlagen: %s", reason, e, exc_info=True)
            await asyncio.to_thread(client_db.record_status, error="sync_failed")
            return "sync_failed"
        await asyncio.to_thread(_finish, plan, resync, bool(msgs))
        return "ok"


async def _pause(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def _send_all(cfg: client_db.SyncConfig, msgs: list) -> list[dict]:
    resync: list[dict] = []
    for i, (items, deleted, full) in enumerate(msgs):
        if i and GAP_SECONDS > 0:
            await _pause(GAP_SECONDS)
        await asyncio.to_thread(client_db.record_status, push_at=now_iso())
        resync += await send_message(
            cfg.hub, cfg.interval_seconds, items, deleted, full,
            shared=cfg.shared, remote_edits=cfg.remote_edits,
        )
    return resync


def _finish(plan: Plan, resync: list[dict], sent: bool) -> None:
    """Alles bestätigt: Cursor vor, resync-Paare zurücksetzen, Status schreiben.

    Ohne gesendete Nachricht (nur Ausgeschlossenes geändert) rücken nur die Cursor.
    """
    client_db.set_cursors(plan.cursors)
    if not sent:
        return
    pairs = [(r.get("username"), r.get("kind")) for r in resync]
    client_db.reset_cursors([p for p in pairs if isinstance(p[0], str) and p[1] in KINDS])
    now = now_iso()
    client_db.record_status(
        ok_at=now, error=", ".join(sorted(set(plan.problems))) or None,
        **({"full_at": now} if plan.full_versions is not None else {}),
    )
