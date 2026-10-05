"""Container: unprivilegiert als Standard + Reconciler hängt nicht mehr fest.

Befund VPS 05.10.2026: Jeder Container lief privilegiert, und ein kurzer
Neustart beim Anlegen hinterließ einen dauerhaften Fehlerstatus.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from hydrahive.containers import incus_client as incus
from hydrahive.containers import reconciler
from hydrahive.containers.models import Container


# --- privilegiert ------------------------------------------------------------

@pytest.fixture
def captured(monkeypatch):
    calls: list[tuple] = []

    async def fake_run(*args, timeout=60.0):
        calls.append(args)
        return 0, "", ""

    monkeypatch.setattr(incus, "_run", fake_run)
    return calls


def _launch_opts(calls) -> list[str]:
    return list(next(c for c in calls if c[0] == "launch"))


def test_default_is_unprivileged_with_nesting(captured, monkeypatch):
    monkeypatch.setattr(incus, "host_is_lxc", lambda: False)
    asyncio.run(incus.launch("c1", "images:debian/12", network_mode="isolated"))
    opts = _launch_opts(captured)
    assert "security.privileged=true" not in opts
    assert "security.nesting=true" in opts


def test_nested_lxc_host_is_privileged(captured, monkeypatch):
    monkeypatch.setattr(incus, "host_is_lxc", lambda: True)
    asyncio.run(incus.launch("c2", "images:debian/12", network_mode="isolated"))
    assert "security.privileged=true" in _launch_opts(captured)


def test_explicit_privileged_wins(captured, monkeypatch):
    monkeypatch.setattr(incus, "host_is_lxc", lambda: False)
    asyncio.run(incus.launch("c3", "images:debian/12", network_mode="isolated", privileged=True))
    assert "security.privileged=true" in _launch_opts(captured)


def test_image_and_name_stay_after_double_dash(captured, monkeypatch):
    monkeypatch.setattr(incus, "host_is_lxc", lambda: False)
    asyncio.run(incus.launch("c4", "images:debian/12", network_mode="isolated", cpu=2, ram_mb=2048))
    opts = _launch_opts(captured)
    assert opts[-3:] == ["--", "images:debian/12", "c4"]


# --- Reconciler --------------------------------------------------------------

def _c(state: str, *, desired: str = "running", error: str | None = None, age_s: int = 0) -> Container:
    ts = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).isoformat()
    return Container(
        container_id=f"id-{state}-{age_s}", owner="admin", name=f"n-{state}-{age_s}",
        image="images:debian/12", network_mode="nat", desired_state=desired, actual_state=state,
        created_at=ts, updated_at=ts, last_error_code=error,
    )


@pytest.fixture
def recon(monkeypatch):
    updates: list[tuple] = []
    state: dict = {"containers": [], "running": set()}

    async def running_names():
        return state["running"]

    monkeypatch.setattr(reconciler.incus, "is_available", lambda: True)
    monkeypatch.setattr(reconciler.incus, "list_running_names", running_names)
    monkeypatch.setattr(reconciler.cdb, "list_", lambda owner=None: state["containers"])
    monkeypatch.setattr(reconciler.cdb, "update_state", lambda cid, **kw: updates.append((cid, kw)))
    return state, updates


def test_starting_container_is_not_marked_error(recon):
    """Der Kern-Bug: launch() startet zum Netz-Setzen neu, Reconciler darf nicht dazwischenfunken."""
    state, updates = recon
    c = _c("starting")
    state["containers"] = [c]
    asyncio.run(reconciler.reconcile_once())
    assert updates == []


def test_error_with_running_container_heals(recon):
    state, updates = recon
    c = _c("error", error="container_not_running")
    state["containers"], state["running"] = [c], {c.name}
    asyncio.run(reconciler.reconcile_once())
    assert updates == [(c.container_id, {"actual": "running", "error_code": None, "error_params": None})]


def test_running_with_stale_error_code_is_cleaned(recon):
    state, updates = recon
    c = _c("running", error="container_not_running")
    state["containers"], state["running"] = [c], {c.name}
    asyncio.run(reconciler.reconcile_once())
    assert updates and updates[0][1]["error_code"] is None


def test_running_container_that_died_becomes_error(recon):
    state, updates = recon
    c = _c("running")
    state["containers"] = [c]
    asyncio.run(reconciler.reconcile_once())
    assert updates[0][1]["actual"] == "error"
    assert updates[0][1]["error_code"] == "container_not_running"


def test_stuck_starting_is_checked_after_timeout(recon):
    state, updates = recon
    c = _c("starting", age_s=reconciler.STALE_TRANSITION_S + 60)
    state["containers"] = [c]
    asyncio.run(reconciler.reconcile_once())
    assert updates and updates[0][1]["actual"] == "error"


def test_error_and_not_running_stays_quiet(recon):
    state, updates = recon
    state["containers"] = [_c("error", error="container_not_running")]
    asyncio.run(reconciler.reconcile_once())
    assert updates == []
