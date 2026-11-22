"""Client: Tasks und Ideen der anderen Instanzen beim Hub abholen
(docs/specs/federation-shared-tasks.md §Nachricht catalog_pull, §Wann wird
abgeholt, §Schalter „Der Client leert seine Kopie“).

``pull`` läuft unter DERSELBEN Sperre wie der Push (catalog_sync) und benutzt
denselben ``seq``-Zähler. Jede Antwort wird begrenzt gelesen und mit dem
Schlüssel des Hubs geprüft (``request_signed`` aus peer_outbound, Muster #738).
Eine Seite wird in einer Transaktion in die Kopie geschrieben, erst darin rückt
der Stand vor. Bei ``more`` folgt die nächste Seite mit ``GAP_SECONDS`` Abstand.

Voller Abgleich (stündlich oder vom Hub verlangt): alle Seiten von ``full_keys``
über ``keys_after`` sammeln, erst danach aus der Kopie löschen, was fehlt.
Bricht der Lauf ab, wird nichts gelöscht.

Ohne Hub, ohne ``enabled``, ohne Nutzerauswahl oder ohne ``shared`` entsteht
kein Netzverkehr. ``peer_catalog_not_shared``/``peer_catalog_not_accepted``
leeren die Kopie.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from hydrahive.db import federation_catalog_client as client_db
from hydrahive.db import federation_catalog_mirror as mirror_db
from hydrahive.db._utils import now_iso
from hydrahive.federation import catalog_sync
from hydrahive.federation import peer_protocol as proto
from hydrahive.federation.peer_outbound import ReplyUnavailable, request_signed

logger = logging.getLogger(__name__)

PULL_PATH = "/api/peering/catalog/pull"
GAP_SECONDS = 2.0                  # Abstand zwischen Seiten (Rate-Limit 30/min, Tests setzen 0)
TIMEOUT = 30.0
MAX_PAGES = 200                    # Sicherung gegen einen Hub, der nie „fertig“ sagt
FULL_MAX_AGE = timedelta(minutes=60)
CLEAR_CODES = {"peer_catalog_not_shared", "peer_catalog_not_accepted"}


class PullFailed(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


def full_due(last_full_pull_at: str | None, now: datetime | None = None) -> bool:
    if not last_full_pull_at:
        return True
    try:
        last = datetime.fromisoformat(last_full_pull_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - last > FULL_MAX_AGE


async def _request(cfg: client_db.SyncConfig, payload_args: dict) -> dict:
    """Eine Anfrage, signierte Antwort geprüft. ``peer_replay`` → einmal ``last_seq + 1``."""
    for attempt in range(2):
        seq = await asyncio.to_thread(client_db.next_seq)
        payload = proto.new_catalog_pull(seq, list(cfg.users), **payload_args)
        try:
            body = await request_signed(cfg.hub, PULL_PATH, payload, reply_kind="catalog_items", timeout=TIMEOUT)
        except httpx.HTTPStatusError as e:
            code, last = _error(e.response)
            if code == "peer_replay" and isinstance(last, int) and not isinstance(last, bool) and attempt == 0:
                await asyncio.to_thread(client_db.raise_seq_to, last)
                continue
            raise PullFailed(code) from e
        except ReplyUnavailable as e:
            raise PullFailed("http_404") from e
        except proto.PeerRejected as e:          # Signatur, Typ, in_reply_to, Größe
            raise PullFailed(e.code, str(e)) from e
        except httpx.HTTPError as e:
            raise PullFailed("hub_unreachable", str(e)) from e
        if body.get("ack_seq") != seq:
            raise PullFailed("hub_bad_ack", f"ack {body.get('ack_seq')!r} statt {seq}")
        return body
    raise PullFailed("peer_replay")


def _error(response: httpx.Response) -> tuple[str, object]:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    detail = detail if isinstance(detail, dict) else {}
    return detail.get("code") or f"http_{response.status_code}", (detail.get("params") or {}).get("last_seq")


def _page_ok(body: dict) -> tuple[list, list, int, dict]:
    items, deleted = body.get("items"), body.get("deleted")
    next_rev, local_next = body.get("next_rev"), body.get("local_next")
    if not (isinstance(items, list) and isinstance(deleted, list) and isinstance(local_next, dict)
            and isinstance(next_rev, int) and not isinstance(next_rev, bool)):
        raise PullFailed("hub_bad_reply", "Antwort unvollständig")
    good = [i for i in items if isinstance(i, dict) and all(isinstance(i.get(f), str) and i.get(f)
            for f in ("origin_fp", "kind", "item_id", "owner")) and i["kind"] in mirror_db.KINDS]
    for i in good:
        i["origin_name"] = i.get("origin_name") or "hub"
        i["title"], i["status"] = str(i.get("title") or ""), str(i.get("status") or "")
    dels = [d for d in deleted if isinstance(d, dict)
            and all(isinstance(d.get(f), str) for f in ("origin_fp", "kind", "item_id"))]
    return good, dels, next_rev, local_next


async def _run(cfg: client_db.SyncConfig, full: bool) -> dict:
    rev, local = await asyncio.to_thread(mirror_db.state)
    keys: set[tuple[str, str, str]] = set()
    keys_after = None
    stats = {"pages": 0, "items": 0, "deleted": 0, "full": full, "removed": 0}
    for page in range(MAX_PAGES):
        if page and GAP_SECONDS > 0:
            await asyncio.sleep(GAP_SECONDS)
        body = await _request(cfg, {"after_rev": rev, "local_after": local, "full": full,
                                    "keys_after": keys_after})
        items, dels, rev, local = _page_ok(body)
        if body.get("reset_local"):
            local = {k: None for k in mirror_db.KINDS}
        await asyncio.to_thread(mirror_db.apply_page, items, dels, rev, local, now_iso())
        stats["pages"] += 1
        stats["items"] += len(items)
        stats["deleted"] += len(dels)
        if body.get("full") is True and not full:   # Hub verlangt vollen Abgleich (Löschprotokoll aufgeräumt)
            full, stats["full"] = True, True
        if full:
            for k in body.get("full_keys") or []:
                if isinstance(k, list) and len(k) >= 3:
                    keys.add((str(k[0]), str(k[1]), str(k[2])))
            keys_after = body.get("keys_next")
        if not body.get("more"):
            break
    else:
        raise PullFailed("hub_too_many_pages")
    if full:
        stats["removed"] = await asyncio.to_thread(mirror_db.keep_only, keys)
    return stats


async def pull(*, full: bool | None = None, reason: str = "timer") -> str:
    """Ein Abhol-Lauf unter der gemeinsamen Sperre. Wirft nie.

    ``full``: None = stündlich nach ``last_full_pull_at``. Rückgabe ``ok`` ·
    ``inactive`` (kein Netzverkehr) · Fehlercode. Das ist die Funktion, die auch
    das Anstupsen (``catalog_notify``, V7) aufruft.
    """
    async with catalog_sync._lock():
        try:
            cfg = await asyncio.to_thread(client_db.load_config)
        except Exception as e:
            logger.warning("Katalog-Abholen: Einstellungen nicht lesbar: %s", e)
            return "pull_failed"
        if not (cfg.active and cfg.shared):
            return "inactive"
        if full is None:
            full = full_due(await asyncio.to_thread(mirror_db.last_full_pull_at))
        try:
            stats = await _run(cfg, full)
        except PullFailed as e:
            logger.info("Katalog-Abholen (%s) fehlgeschlagen: %s", reason, e)
            if e.code in CLEAR_CODES:
                await asyncio.to_thread(mirror_db.clear)
            await asyncio.to_thread(mirror_db.record_pull_status, error=e.code)
            return e.code
        except Exception as e:
            logger.warning("Katalog-Abholen (%s) unerwartet fehlgeschlagen: %s", reason, e, exc_info=True)
            await asyncio.to_thread(mirror_db.record_pull_status, error="pull_failed")
            return "pull_failed"
        stamp = now_iso()
        await asyncio.to_thread(mirror_db.record_pull_status, ok_at=stamp, full_at=stamp if stats["full"] else None)
        return "ok"
