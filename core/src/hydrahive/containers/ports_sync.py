"""Abgleich Portfreigaben (Datenbank) ↔ ufw-Regeln (docs/specs/container-nat-ports.md, „ufw aus/an und Abgleich“).

Läuft beim Start und dann alle `settings.container_ports_sync_interval` Sekunden. Soll sind Freigaben public/tailnet an
laufenden nat-Containern mit fester IP; Ist liefert `hh-portforward list` (auch bei ausgeschaltetem ufw). Fehlende oder
abweichende Regeln werden über das normale `ports.apply` gesetzt (proxy device + ufw), verwaiste hh-port-Regeln und
Regeln für `off` entfernt. Nur hh-port-Regeln werden angefasst; fremde ufw-Regeln sieht der Abgleich gar nicht.
"""
from __future__ import annotations

import asyncio
import json
import logging

from hydrahive.containers import db as cdb
from hydrahive.containers import nat
from hydrahive.containers import ports as cports
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def _interval() -> int:
    return max(30, settings.container_ports_sync_interval)


async def _list_ufw() -> list[dict] | None:
    """Gespeicherte hh-port-Regeln; None, wenn ufw nicht installiert ist (dann gibt es nichts abzugleichen)."""
    proc = await asyncio.create_subprocess_exec(
        "sudo", "-n", cports.HELPER, "list",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
    if proc.returncode != 0:
        raise cports.PortError("container_port_apply_failed", detail=err.decode(errors="replace")[:200])
    data = json.loads(out.decode() or "{}")
    return data.get("rules", []) if data.get("ufw") else None


def _expected(rule: cports.PortRule, ip: str, wan_if: str) -> dict:
    cend = rule.container_port_start + (rule.host_port_end - rule.host_port_start)
    port = str(rule.container_port_start) if cend == rule.container_port_start else f"{rule.container_port_start}:{cend}"
    return {"id": rule.id, "in": wan_if if rule.scope == "public" else "tailscale0",
            "ip": ip, "port": port, "proto": rule.protocol}


async def sync_once() -> dict | None:
    """Ein Durchlauf. None, wenn der Ist-Stand nicht lesbar war (dann wird nichts geändert)."""
    try:
        listed = await _list_ufw()
    except (cports.PortError, OSError, ValueError, asyncio.TimeoutError) as exc:
        logger.warning("Portfreigaben-Abgleich übersprungen: ufw-Regeln nicht lesbar (%s)", exc)
        return None
    if listed is None:
        return None
    actual = {r["id"]: r for r in listed}
    wan_if = nat.wan_interface() or "eth0"
    known: set[str] = set()
    res = {"applied": 0, "removed": 0, "failed": 0}
    for c in cdb.list_(owner=None):
        if c.node_id != "local" or c.network_mode != "nat":
            continue
        ip = nat.get_ipv4(c.container_id)
        for rule in cports.list_for(c.container_id):
            known.add(rule.id)
            have = actual.get(rule.id)
            if rule.scope == "off":
                if have:
                    await _remove(rule.id, res)
                continue
            # Gestoppt/ohne IP: kein proxy device möglich → nichts neu anlegen, Vorhandenes stehen lassen.
            if c.actual_state != "running" or not ip:
                continue
            if have == _expected(rule, ip, wan_if):
                continue
            try:
                await cports.apply(c.name, ip, rule)
                res["applied"] += 1
                logger.info("Portfreigabe %s (%s) nachgezogen", rule.id, c.name)
            except Exception as exc:  # apply hat last_error schon gesetzt; nächste Freigabe trotzdem prüfen
                res["failed"] += 1
                logger.warning("Portfreigabe %s (%s) nicht nachgezogen: %s", rule.id, c.name, exc)
    for orphan in sorted(set(actual) - known):
        await _remove(orphan, res)
    return res


async def _remove(port_id: str, res: dict) -> None:
    try:
        await cports._helper("remove", port_id)
        res["removed"] += 1
        logger.info("Verwaiste/abgeschaltete ufw-Regel hh-port:%s entfernt", port_id)
    except Exception as exc:
        res["failed"] += 1
        logger.warning("ufw-Regel hh-port:%s nicht entfernt: %s", port_id, exc)


async def run_loop(stop: asyncio.Event) -> None:
    logger.info("Portfreigaben-Abgleich gestartet (Intervall %ss)", _interval())
    while not stop.is_set():
        if nat.nat_available():
            try:
                await sync_once()
            except Exception:
                logger.exception("Portfreigaben-Abgleich fehlgeschlagen")
        try:
            await asyncio.wait_for(stop.wait(), timeout=_interval())
        except asyncio.TimeoutError:
            pass
    logger.info("Portfreigaben-Abgleich beendet")
