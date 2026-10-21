"""Container anlegen: Fehlversuche hinterlassen keine Waisen in Incus.

Befund Mac .186, 21.10.2026: Scheiterte das Anlegen nach `incus launch`, löschte
HydraHive nur den eigenen Eintrag. Der Container blieb in Incus und belegte die
NAT-IP 10.10.0.10. Weil die IP-Vergabe nur die DB kennt, scheiterte danach jeder
NAT-Container mit „IP address … already defined on another NIC“.
"""
from __future__ import annotations

import asyncio
import json
import logging

import pytest

from hydrahive.containers import incus_client as incus


@pytest.fixture
def fake_incus(monkeypatch):
    """Fake für incus_client._run: Antworten je Befehl, alle Aufrufe mitschreiben."""
    calls: list[tuple] = []
    answers: dict[str, tuple[int, str, str]] = {}

    async def fake_run(*args, timeout=60.0, input_bytes=None):
        calls.append(args)
        return answers.get(args[0], (0, "", ""))

    monkeypatch.setattr(incus, "_run", fake_run)
    monkeypatch.setattr(incus, "host_is_lxc", lambda: False)
    return calls, answers


def _deleted(calls) -> list[tuple]:
    return [c for c in calls if c[0] == "delete"]


# --- launch(): eigene halbfertige Container wieder entfernen ----------------

def test_nat_device_failure_removes_new_container(fake_incus):
    calls, answers = fake_incus
    answers["config"] = (1, "", "Error: IP address already defined")
    with pytest.raises(incus.IncusError) as exc:
        asyncio.run(incus.launch("c1", "images:debian/12", network_mode="nat", ipv4="10.10.0.10"))
    assert exc.value.code == "incus_launch_failed"
    assert _deleted(calls) == [("delete", "c1", "--force")]


def test_nat_restart_failure_is_reported_and_cleaned(fake_incus):
    calls, answers = fake_incus
    answers["restart"] = (1, "", "Error: boom")
    with pytest.raises(incus.IncusError) as exc:
        asyncio.run(incus.launch("c2", "images:debian/12", network_mode="nat", ipv4="10.10.0.11"))
    assert exc.value.code == "incus_restart_failed"
    assert _deleted(calls) == [("delete", "c2", "--force")]


def test_bridged_restart_failure_is_reported_and_cleaned(fake_incus):
    calls, answers = fake_incus
    answers["restart"] = (1, "", "Error: boom")
    with pytest.raises(incus.IncusError):
        asyncio.run(incus.launch("c3", "images:debian/12", network_mode="bridged"))
    assert _deleted(calls) == [("delete", "c3", "--force")]


def test_failed_launch_never_deletes(fake_incus):
    """Scheitert schon `incus launch` (z. B. Name existiert), ist der Container nicht von uns."""
    calls, answers = fake_incus
    answers["launch"] = (1, "", "Error: Instance \"c4\" already exists")
    with pytest.raises(incus.IncusError):
        asyncio.run(incus.launch("c4", "images:debian/12", network_mode="nat", ipv4="10.10.0.12"))
    assert _deleted(calls) == []


def test_successful_nat_launch_keeps_container(fake_incus):
    calls, _ = fake_incus
    asyncio.run(incus.launch("c5", "images:debian/12", network_mode="nat", ipv4="10.10.0.13"))
    assert _deleted(calls) == []


# --- belegte NAT-IPs in Incus ----------------------------------------------

def _instances(*devs: dict) -> str:
    return json.dumps([{"name": f"i{n}", "expanded_devices": d} for n, d in enumerate(devs)])


def test_nat_ips_in_use_reads_incus(fake_incus):
    _, answers = fake_incus
    answers["query"] = (0, _instances(
        {"eth0": {"type": "nic", "network": "hhnat0", "ipv4.address": "10.10.0.10"}},
        {"eth0": {"type": "nic", "network": "incusbr0", "ipv4.address": "10.10.0.11"}},
        {"eth0": {"type": "nic", "network": "hhnat0"}},
        {"root": {"type": "disk", "path": "/"}},
        {"x": {"type": "unix-char", "network": "hhnat0", "ipv4.address": "10.10.0.99"}},
        {"eth1": {"type": "nic", "network": "hhnat0", "ipv4.address": "10.10.0.42"}},
    ), "")
    assert asyncio.run(incus.nat_ips_in_use("hhnat0")) == {"10.10.0.10", "10.10.0.42"}


@pytest.mark.parametrize("answer", [(1, "", "Error"), (0, "kaputt", ""), (0, "{}", ""), (0, "5", "")])
def test_nat_ips_in_use_tolerates_errors(fake_incus, answer):
    _, answers = fake_incus
    answers["query"] = answer
    assert asyncio.run(incus.nat_ips_in_use("hhnat0")) == set()


@pytest.mark.parametrize("rc,expected", [(0, True), (1, False)])
def test_instance_exists(fake_incus, rc, expected):
    calls, answers = fake_incus
    answers["query"] = (rc, "{}", "" if rc == 0 else "Error: Instance not found")
    assert asyncio.run(incus.instance_exists("abc")) is expected
    assert calls == [("query", "/1.0/instances/abc")]


def test_allocate_skips_excluded(client):
    from hydrahive.containers import nat

    first = nat.allocate_ipv4()
    nxt = nat.allocate_ipv4(exclude={first})
    assert nxt != first and nxt.startswith("10.10.0.")


# --- API: Anlegen -----------------------------------------------------------

@pytest.fixture
def api_env(monkeypatch):
    from hydrahive.api.routes import containers_crud as crud
    from hydrahive.containers import nat

    seen: dict = {}
    monkeypatch.setattr(crud.incus, "is_available", lambda: True)
    monkeypatch.setattr(nat, "network_modes",
                        lambda: {"bridged": False, "nat": True, "isolated": True, "default": "nat"})

    async def no_instance(name):
        return False
    monkeypatch.setattr(crud.incus, "instance_exists", no_instance)

    async def in_use(network):
        return {"10.10.0.10"}
    monkeypatch.setattr(crud.incus, "nat_ips_in_use", in_use)

    async def fake_create(container_id, *, actor):
        seen["ip"] = nat.get_ipv4(container_id)
    monkeypatch.setattr(crud.execution, "create_and_start", fake_create)
    return seen


def _cleanup(client, headers, name):
    for c in client.get("/api/containers", headers=headers).json():
        if c["name"] == name:
            from hydrahive.containers import db as cdb
            cdb.delete(c["container_id"])


def test_api_nat_ip_skips_ip_used_in_incus(client, admin_headers, api_env):
    r = client.post("/api/containers", headers=admin_headers,
                    json={"name": "orphan-ip", "image": "debian/12", "network_mode": "nat"})
    try:
        assert r.status_code == 201, r.text
        assert api_env["ip"] != "10.10.0.10"
    finally:
        _cleanup(client, admin_headers, "orphan-ip")


def test_api_name_existing_in_incus_is_conflict(client, admin_headers, api_env, monkeypatch):
    from hydrahive.api.routes import containers_crud as crud

    async def exists(name):
        return name == "schon-da"
    monkeypatch.setattr(crud.incus, "instance_exists", exists)
    r = client.post("/api/containers", headers=admin_headers,
                    json={"name": "schon-da", "image": "debian/12", "network_mode": "nat"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "container_name_taken"
    assert "schon-da" not in [c["name"] for c in client.get("/api/containers", headers=admin_headers).json()]
    assert "ip" not in api_env


def test_api_create_failure_is_logged(client, admin_headers, api_env, monkeypatch, caplog):
    from hydrahive.api.routes import containers_crud as crud

    async def boom(container_id, *, actor):
        raise incus.IncusError("incus_launch_failed", stderr="Error: kaputt")
    monkeypatch.setattr(crud.execution, "create_and_start", boom)
    with caplog.at_level(logging.WARNING, logger="hydrahive.api.routes.containers_crud"):
        r = client.post("/api/containers", headers=admin_headers,
                        json={"name": "log-mich", "image": "debian/12", "network_mode": "nat"})
    assert r.status_code == 500
    text = caplog.text
    assert "log-mich" in text and "incus_launch_failed" in text and "kaputt" in text
    assert "log-mich" not in [c["name"] for c in client.get("/api/containers", headers=admin_headers).json()]
