"""Client: Katalog-Metadaten an den Hub schicken (docs/specs/federation-catalog.md §Ablauf 2 + 3).

Ein Lauf (``sync``) wird vom Timer, vom Event-Push oder nach einem Überlauf
gestartet. Alle Läufe teilen sich EINE Sperre: es läuft immer nur ein Versand,
Nachrichten gehen streng nacheinander mit steigender ``seq`` raus.

Cursor je Nutzer und Art: ab ``updated_at >= cursor`` (die letzte Zeitstufe wird
absichtlich wiederholt, Tasks sind nur sekundengenau), innerhalb des Laufs per
Keyset ``(updated_at, item_id)`` geblättert, höchstens 500 Einträge je Nachricht,
mindestens 2 s Abstand. Der Cursor rückt erst vor, wenn ALLE Nachrichten des
Laufs bestätigt sind. ``updated_at`` wird nur innerhalb derselben Art verglichen.

Ohne aktiven Hub, ohne ``enabled`` oder ohne Nutzerauswahl entsteht kein
Netzverkehr. Quellen kommen über ``catalog_sources.get_source(kind)``.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.db._utils import now_iso
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.peer_inbound import send_signed
from hydrahive.modules import catalog_sources

logger = logging.getLogger(__name__)

KINDS = ("task", "idea")
PAGE = 500                 # Einträge je Nachricht (Spec: höchstens 500)
GAP_SECONDS = 2.0          # Abstand zwischen Nachrichten eines Laufs (Rate-Limit 30/min)
MAX_PAGES = 2_000          # Sicherung gegen eine Quelle, die nie endet
META_FIELDS = ("kind", "item_id", "owner", "title", "status", "priority",
               "project_id", "project_name", "created_at", "updated_at")
MAX_TITLE = 300

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


@dataclass
class Plan:
    items: list[dict] = field(default_factory=list)
    deleted: list[dict] = field(default_factory=list)
    cursors: dict[tuple[str, str], str] = field(default_factory=dict)
    full_versions: dict | None = None
    problems: list[str] = field(default_factory=list)


def _meta(row: object, kind: str, username: str) -> dict | None:
    """Genau die Metadaten der Spec. Fremde Art/fremder Besitzer → verworfen."""
    if not isinstance(row, dict) or row.get("item_id") in (None, "") or not row.get("updated_at"):
        return None
    if row.get("kind", kind) != kind or row.get("owner", username) != username:
        return None
    meta = {f: row.get(f) for f in META_FIELDS}
    meta.update(kind=kind, owner=username, title=str(meta.get("title") or "")[:MAX_TITLE])
    return meta


def _collect_changed(cfg: client_db.SyncConfig, pairs: set[tuple[str, str]], plan: Plan) -> None:
    """Delta je (Nutzer, Art) ab Cursor (``>=``), Keyset-geblättert."""
    cursors = client_db.get_cursors()
    for username, kind in sorted(pairs):
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        cursor = cursors.get((username, kind))
        after = (cursor, "") if cursor else None   # (c, "") == updated_at >= c
        highest = None
        try:
            for _ in range(MAX_PAGES):
                rows = source.list_changed(username, after, PAGE) or []
                for row in rows:
                    meta = _meta(row, kind, username)
                    if meta is None:
                        continue
                    highest = meta["updated_at"] if highest is None or meta["updated_at"] > highest else highest
                    if meta["project_id"] not in cfg.excluded_projects:
                        plan.items.append(meta)
                if len(rows) < PAGE:
                    break
                last = rows[-1]
                after = (last["updated_at"], last["item_id"])
        except Exception as e:  # kaputte Quelle: diese Art auslassen, Cursor bleibt
            logger.warning("Katalog-Sync: Quelle %s für %s fehlgeschlagen: %s", kind, username, e)
            plan.problems.append(f"source_failed:{kind}")
            continue
        if highest is not None:
            plan.cursors[(username, kind)] = highest


def _collect_full(cfg: client_db.SyncConfig, plan: Plan) -> None:
    """Abgleich: (item_id, updated_at) je Nutzer und Art, gefiltert wie der Push.

    Scheitert eine Quelle, geht in diesem Lauf KEINE Liste raus — der Hub würde
    sonst alle Einträge dieser Art löschen.
    """
    full: dict[str, dict[str, list[list[str]]]] = {}
    for username in cfg.users:
        full[username] = {}
        for kind in KINDS:
            source = catalog_sources.get_source(kind)
            if source is None:
                continue
            try:
                versions = source.list_versions(username) or []
            except Exception as e:
                logger.warning("Katalog-Sync: Abgleich %s für %s fehlgeschlagen: %s", kind, username, e)
                plan.problems.append(f"source_failed:{kind}")
                return
            full[username][kind] = [
                [str(v[0]), str(v[1])] for v in versions
                if len(v) >= 3 and v[0] and v[1] and v[2] not in cfg.excluded_projects
            ]
    plan.full_versions = full


def _collect_deleted(cfg: client_db.SyncConfig, entries: list[tuple[str, str, str]], plan: Plan) -> None:
    """Event-Push: gemeldete Einträge, die es nicht mehr gibt, sofort als ``deleted``.

    Das Projekt eines gelöschten Eintrags ist nicht mehr bekannt; es geht nur
    (Art, ID) raus, kein Titel. Der Hub löscht nur, was er von diesem Partner hat.
    """
    for kind, username, item_id in entries:
        source = catalog_sources.get_source(kind)
        if source is None:
            continue
        try:
            gone = source.get_full(username, item_id) is None
        except Exception:
            continue
        if gone:
            plan.deleted.append({"kind": kind, "item_id": item_id})


def build_plan(cfg, *, pairs, entries=(), full=False) -> Plan:
    plan = Plan()
    _collect_deleted(cfg, list(entries), plan)
    _collect_changed(cfg, pairs, plan)
    if full:
        _collect_full(cfg, plan)
    return plan


def _messages(plan: Plan, *, heartbeat: bool) -> list[tuple[list[dict], list[dict], dict | None]]:
    chunks = [plan.items[i:i + PAGE] for i in range(0, len(plan.items), PAGE)]
    dels = [plan.deleted[i:i + PAGE] for i in range(0, len(plan.deleted), PAGE)]
    count = max(len(chunks), len(dels))
    if count == 0 and (heartbeat or plan.full_versions is not None):
        count = 1
    msgs = [(chunks[i] if i < len(chunks) else [], dels[i] if i < len(dels) else [], None) for i in range(count)]
    if msgs and plan.full_versions is not None:  # Abgleich zuletzt: alle Einträge sind dann schon da
        items, deleted, _ = msgs[-1]
        msgs[-1] = (items, deleted, plan.full_versions)
    return msgs


async def _send_one(hub: dict, interval: int, items, deleted, full) -> list[dict]:
    """Eine Nachricht senden; bei ``peer_replay`` einmal mit ``last_seq + 1`` wiederholen."""
    for attempt in range(2):
        seq = client_db.next_seq()
        payload = proto.new_catalog_push(seq, interval, items, deleted, full)
        try:
            r = await send_signed(hub, "/api/peering/catalog/push", payload)
        except httpx.HTTPStatusError as e:
            detail = _detail(e.response)
            code = detail.get("code") or f"http_{e.response.status_code}"
            last = (detail.get("params") or {}).get("last_seq")
            if code == "peer_replay" and isinstance(last, int) and attempt == 0:
                client_db.raise_seq_to(last)
                continue
            raise SyncFailed(code) from e
        except httpx.HTTPError as e:
            raise SyncFailed("hub_unreachable", str(e)) from e
        body = _json(r)
        if body.get("ack_seq") != seq:
            raise SyncFailed("hub_bad_ack", f"ack {body.get('ack_seq')!r} statt {seq}")
        return [x for x in body.get("resync") or [] if isinstance(x, dict)]
    raise SyncFailed("peer_replay")


def _json(response) -> dict:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _detail(response) -> dict:
    detail = _json(response).get("detail")
    return detail if isinstance(detail, dict) else {}


async def sync(*, pairs=None, entries=(), full=False, heartbeat=True, reason="timer") -> str:
    """Ein Lauf. Rückgabe: ``ok`` · ``inactive`` · Fehlercode. Wirft nie."""
    async with _lock():
        cfg = await asyncio.to_thread(client_db.load_config)
        if not cfg.active:
            return "inactive"  # kein Netzverkehr ohne Hub/Sync/Nutzer
        users = set(cfg.users)
        wanted = {(u, k) for u in cfg.users for k in KINDS} if pairs is None else {p for p in pairs if p[0] in users}
        entries = [e for e in entries if e[1] in users]
        try:
            plan = await asyncio.to_thread(build_plan, cfg, pairs=wanted, entries=entries, full=full)
            messages = _messages(plan, heartbeat=heartbeat)
            if not messages:  # nichts zu senden (z. B. nur ausgeschlossene Projekte)
                await asyncio.to_thread(client_db.set_cursors, plan.cursors)
                return "ok"
            resync: list[dict] = []
            for i, (items, deleted, fv) in enumerate(messages):
                if i:
                    await asyncio.sleep(GAP_SECONDS)
                await asyncio.to_thread(client_db.record_status, push_at=now_iso())
                resync += await _send_one(cfg.hub, cfg.interval_seconds, items, deleted, fv)
        except SyncFailed as e:
            logger.info("Katalog-Sync (%s) fehlgeschlagen: %s", reason, e)
            await asyncio.to_thread(client_db.record_status, error=e.code)
            return e.code
        except Exception as e:
            logger.warning("Katalog-Sync (%s) unerwartet fehlgeschlagen: %s", reason, e, exc_info=True)
            await asyncio.to_thread(client_db.record_status, error="sync_failed")
            return "sync_failed"
        await asyncio.to_thread(_finish, plan, resync)
        return "ok"


def _finish(plan: Plan, resync: list[dict]) -> None:
    """Alles bestätigt: Cursor vor, dann resync-Paare zurücksetzen, Status schreiben."""
    client_db.set_cursors(plan.cursors)
    pairs = [(r.get("username"), r.get("kind")) for r in resync]
    client_db.reset_cursors([p for p in pairs if isinstance(p[0], str) and p[1] in KINDS])
    now = now_iso()
    client_db.record_status(
        ok_at=now, error=", ".join(sorted(set(plan.problems))) or None,
        **({"full_at": now} if plan.full_versions is not None else {}),
    )
