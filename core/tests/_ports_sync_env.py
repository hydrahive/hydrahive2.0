"""Gemeinsame Umgebung für die Tests des Portfreigaben-Abgleichs (containers/ports_sync.py).

Echte Datenbank der Test-Umgebung; Root-Helfer, incus und ufw-Liste sind durch Aufzeichnungen ersetzt.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def env(client, monkeypatch):
    from hydrahive.containers import db as cdb
    from hydrahive.containers import nat
    from hydrahive.containers import ports as cp
    from hydrahive.containers import ports_sync as ps

    calls: list[tuple] = []
    state = {"ufw": [], "fail": set(), "wan": "eth0", "installed": True}

    async def fake_helper(*args: str) -> None:
        calls.append(args)
        if args[0] == "apply" and args[1] in state["fail"]:
            raise cp.PortError("container_port_apply_failed", detail="ufw kaputt")

    async def fake_list() -> list[dict] | None:
        return list(state["ufw"]) if state["installed"] else None

    async def fake_apply(name, ip, rule):          # vollständiges apply (incus + Helfer) aufzeichnen
        calls.append(("full-apply", rule.id, name, ip, rule.scope))
        if rule.id in state["fail"]:
            cp._mark(rule.id, error="ufw kaputt")
            raise cp.PortError("container_port_apply_failed", detail="ufw kaputt")
        cp._mark(rule.id, error=None)

    monkeypatch.setattr(cp, "_helper", fake_helper)
    monkeypatch.setattr(cp, "apply", fake_apply)
    monkeypatch.setattr(ps, "_list_ufw", fake_list)
    monkeypatch.setattr(ps.nat, "wan_interface", lambda: state["wan"])
    made: list[str] = []

    def container(name: str, *, running: bool = True, mode: str = "nat") -> str:
        c = cdb.create(owner="admin", name=name, image="images:debian/12", network_mode=mode)
        if mode == "nat":
            nat.set_ipv4(c.container_id, nat.allocate_ipv4())
        cdb.update_state(c.container_id, actual="running" if running else "stopped")
        made.append(c.container_id)
        return c.container_id

    yield {"cp": cp, "ps": ps, "nat": nat, "calls": calls, "state": state, "container": container}
    for cid in made:
        for r in cp.list_for(cid):
            cp.delete_row(r.id)
        cdb.delete(cid)


def _ufw_entry(cp, nat, rule, *, iface: str = "eth0") -> dict:
    cend = rule.container_port_start + (rule.host_port_end - rule.host_port_start)
    port = str(rule.container_port_start) if cend == rule.container_port_start else f"{rule.container_port_start}:{cend}"
    return {"id": rule.id, "in": iface, "ip": nat.get_ipv4(rule.container_id), "port": port, "proto": rule.protocol}


def _run(ps):
    import asyncio
    return asyncio.run(ps.sync_once())
