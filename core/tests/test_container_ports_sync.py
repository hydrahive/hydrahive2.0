"""Abgleich Portfreigaben (Datenbank) ↔ ufw-Regeln (docs/specs/container-nat-ports.md, „ufw aus/an und Abgleich“).

Soll: Freigaben public/tailnet an laufenden nat-Containern mit IP. Ist: `hh-portforward list`. Fehlende oder
abweichende Regeln → apply, verwaiste hh-port-Regeln oder scope=off → remove. Echte Datenbank (Test-Umgebung),
der Root-Helfer ist durch eine Aufzeichnung ersetzt.
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
    state = {"ufw": [], "fail": set(), "wan": "eth0"}

    async def fake_helper(*args: str) -> None:
        calls.append(args)
        if args[0] == "apply" and args[1] in state["fail"]:
            raise cp.PortError("container_port_apply_failed", detail="ufw kaputt")

    async def fake_list() -> list[dict]:
        return list(state["ufw"])

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


def test_missing_rule_is_applied(env):
    cp, ps = env["cp"], env["ps"]
    cid = env["container"]("sync-a")
    r = cp.create(cid, "tcp", 30001, 30001, 30001, "public", "game")
    res = _run(ps)
    assert ("full-apply", r.id, "sync-a", env["nat"].get_ipv4(cid), "public") in env["calls"]
    assert res["applied"] == 1 and res["removed"] == 0


def test_matching_rule_is_left_alone(env):
    cp, ps, nat = env["cp"], env["ps"], env["nat"]
    cid = env["container"]("sync-b")
    r = cp.create(cid, "udp", 27000, 27015, 27000, "tailnet", "")
    env["state"]["ufw"] = [_ufw_entry(cp, nat, r, iface="tailscale0")]
    res = _run(ps)
    assert env["calls"] == []
    assert res == {"applied": 0, "removed": 0, "failed": 0}


def test_wrong_interface_or_ip_is_reapplied(env):
    cp, ps, nat = env["cp"], env["ps"], env["nat"]
    cid = env["container"]("sync-c")
    r = cp.create(cid, "tcp", 30003, 30003, 30003, "public", "")
    env["state"]["ufw"] = [_ufw_entry(cp, nat, r, iface="tailscale0")]       # Reichweite geändert, ufw veraltet
    _run(ps)
    assert [c[0] for c in env["calls"]] == ["full-apply"]
    env["calls"].clear()
    env["state"]["ufw"] = [{**_ufw_entry(cp, nat, r), "ip": "10.10.0.250"}]  # IP passt nicht
    _run(ps)
    assert [c[0] for c in env["calls"]] == ["full-apply"]


def test_orphan_hh_port_rule_is_removed(env):
    ps = env["ps"]
    orphan = "0192ffff-0000-7000-8000-000000000099"
    env["state"]["ufw"] = [{"id": orphan, "in": "eth0", "ip": "10.10.0.77", "port": "40000", "proto": "tcp"}]
    res = _run(ps)
    assert ("remove", orphan) in env["calls"]
    assert res["removed"] == 1


def test_scope_off_rule_in_ufw_is_removed(env):
    cp, ps, nat = env["cp"], env["ps"], env["nat"]
    cid = env["container"]("sync-d")
    r = cp.create(cid, "tcp", 30007, 30007, 30007, "off", "")
    env["state"]["ufw"] = [_ufw_entry(cp, nat, r)]
    _run(ps)
    assert ("remove", r.id) in env["calls"]
    assert not any(c[0] == "full-apply" for c in env["calls"])


def test_stopped_container_gets_no_new_rule_and_keeps_existing(env):
    """Gestoppter Container: keine neue Regel anlegen (kein proxy device möglich), vorhandene aber nicht abräumen –
    sonst wäre der Port nach dem Start bis zum nächsten Abgleich dicht."""
    cp, ps, nat = env["cp"], env["ps"], env["nat"]
    cid = env["container"]("sync-e", running=False)
    r1 = cp.create(cid, "tcp", 30011, 30011, 30011, "public", "")
    r2 = cp.create(cid, "tcp", 30015, 30015, 30015, "public", "")
    env["state"]["ufw"] = [_ufw_entry(cp, nat, r2)]
    _run(ps)
    assert env["calls"] == []
    assert r1.id  # unverändert


def test_bridged_containers_are_ignored(env):
    ps = env["ps"]
    env["container"]("sync-f", mode="bridged")
    assert _run(ps) == {"applied": 0, "removed": 0, "failed": 0}


def test_failure_is_recorded_and_others_continue(env):
    cp, ps = env["cp"], env["ps"]
    cid = env["container"]("sync-g")
    bad = cp.create(cid, "tcp", 30021, 30021, 30021, "public", "")
    good = cp.create(cid, "tcp", 30022, 30022, 30022, "public", "")
    env["state"]["fail"] = {bad.id}
    res = _run(ps)
    assert res == {"applied": 1, "removed": 0, "failed": 1}
    assert cp.get(bad.id).last_error == "ufw kaputt"
    assert cp.get(good.id).applied_at and not cp.get(good.id).last_error


def test_list_failure_skips_the_round(env, monkeypatch):
    """Ist-Stand nicht lesbar (Helfer fehlt, sudo kaputt): nichts tun – lieber keine Änderung als alles neu."""
    cp, ps = env["cp"], env["ps"]
    cid = env["container"]("sync-h")
    cp.create(cid, "tcp", 30031, 30031, 30031, "public", "")

    async def broken() -> list[dict]:
        raise cp.PortError("container_port_apply_failed", detail="sudo: kein Helfer")
    monkeypatch.setattr(ps, "_list_ufw", broken)
    assert _run(ps) is None
    assert env["calls"] == []


def test_interval_comes_from_settings(monkeypatch):
    from hydrahive.containers import ports_sync as ps
    from hydrahive.settings import settings
    monkeypatch.setenv("HH_CONTAINER_PORTS_SYNC_INTERVAL", "123")
    settings.__dict__.pop("container_ports_sync_interval", None)
    assert ps._interval() == 123
    settings.__dict__.pop("container_ports_sync_interval", None)


def test_sync_loop_runs_with_the_container_reconciler(monkeypatch):
    """Der Abgleich läuft mit dem Container-Reconciler mit (Start + Ende), ohne lifespan.py weiter zu vergrößern."""
    import asyncio

    from hydrahive.containers import ports_sync as ps
    from hydrahive.containers import reconciler as rc

    seen: list[str] = []

    async def fake_sync_loop(stop: asyncio.Event) -> None:
        seen.append("start")
        await stop.wait()
        seen.append("stop")

    async def fake_reconcile() -> None:
        pass

    monkeypatch.setattr(ps, "run_loop", fake_sync_loop)
    monkeypatch.setattr(rc, "reconcile_once", fake_reconcile)

    async def go() -> None:
        stop = asyncio.Event()
        task = asyncio.create_task(rc.run_loop(stop))
        await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(task, timeout=5)

    asyncio.run(go())
    assert seen == ["start", "stop"]
