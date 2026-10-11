"""Portfreigaben-Abgleich: Rahmen – Intervall, Mitlauf mit dem Container-Reconciler, Ist-Stand nicht lesbar / ohne ufw.

Die eigentliche Soll/Ist-Logik prüft test_container_ports_sync.py (gleiche Fixture `env`).
"""
from __future__ import annotations

from tests._ports_sync_env import _run

pytest_plugins = ["tests._ports_sync_env"]  # Fixture `env`


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


def test_without_ufw_nothing_is_reapplied(env):
    """Ohne installiertes ufw gibt es nichts abzugleichen. Sonst sähe jede Freigabe wie „Regel fehlt“ aus und würde alle
    paar Minuten neu gesetzt – samt kurzem Abriss durch das neu angelegte proxy device."""
    cp, ps = env["cp"], env["ps"]
    cid = env["container"]("sync-i")
    cp.create(cid, "tcp", 30051, 30051, 30051, "public", "")
    env["state"]["installed"] = False
    assert _run(ps) is None
    assert env["calls"] == []

