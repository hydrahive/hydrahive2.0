"""Container NAT + Portfreigaben (docs/specs/container-nat-ports.md)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = Path(__file__).parents[2] / "installer" / "lib" / "hh-portforward"


# --- Root-Helfer: Eingaben werden unabhängig vom Backend geprüft -------------

@pytest.fixture
def fake_ufw(tmp_path, monkeypatch):
    log = tmp_path / "ufw.log"
    ufw = tmp_path / "ufw"
    ufw.write_text(f"""#!/bin/sh
echo "$@" >> {log}
case "$1" in status) echo "Status: active";; esac
""")
    ufw.chmod(0o755)
    src = HELPER.read_text().replace('UFW = "/usr/sbin/ufw"', f'UFW = "{ufw}"')
    helper = tmp_path / "hh-portforward"
    helper.write_text(src)
    return helper, log


def _run(helper: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(helper), *args], capture_output=True, text=True, timeout=20)


ID = "0192aaaa-bbbb-7ccc-8ddd-eeeeffff0001"


def test_helper_public_tcp_writes_route_rule(fake_ufw):
    helper, log = fake_ufw
    r = _run(helper, "apply", ID, "tcp", "25565", "25565", "10.10.0.10", "25565", "public", "eth0")
    assert r.returncode == 0, r.stderr
    route = [line for line in log.read_text().splitlines() if line.startswith("route")]
    assert route == [f"route allow in on eth0 out on hhnat0 to 10.10.0.10 port 25565 proto tcp comment hh-port:{ID}"]


def test_helper_tailnet_uses_tailscale_interface_and_range(fake_ufw):
    helper, log = fake_ufw
    r = _run(helper, "apply", ID, "udp", "27000", "27015", "10.10.0.11", "27000", "tailnet", "eth0")
    assert r.returncode == 0, r.stderr
    assert "in on tailscale0 out on hhnat0 to 10.10.0.11 port 27000:27015 proto udp" in log.read_text()


def test_helper_off_writes_no_rule(fake_ufw):
    helper, log = fake_ufw
    assert _run(helper, "apply", ID, "tcp", "25565", "25565", "10.10.0.10", "25565", "off", "eth0").returncode == 0
    assert "route allow" not in log.read_text()


@pytest.mark.parametrize("args", [
    ("tcp", "22", "22", "10.10.0.10", "22", "public", "eth0"),            # gesperrter Port
    ("tcp", "80", "80", "10.10.0.10", "80", "public", "eth0"),            # < 1024
    ("tcp", "8000", "8002", "10.10.0.10", "8000", "public", "eth0"),      # 8001 im Bereich
    ("tcp", "30000", "30200", "10.10.0.10", "30000", "public", "eth0"),   # Bereich > 100
    ("tcp", "25565", "25565", "192.168.178.2", "25565", "public", "eth0"),  # IP außerhalb NAT
    ("icmp", "25565", "25565", "10.10.0.10", "25565", "public", "eth0"),  # Protokoll
    ("tcp", "25565", "25565", "10.10.0.10", "25565", "world", "eth0"),    # Reichweite
    ("tcp", "25565", "25565", "10.10.0.10", "25565", "public", "eth0;rm"),  # Interface-Injection
])
def test_helper_rejects_bad_input(fake_ufw, args):
    helper, log = fake_ufw
    r = _run(helper, "apply", ID, *args)
    assert r.returncode != 0
    assert not log.exists() or "route allow" not in log.read_text()


def test_helper_rejects_bad_id(fake_ufw):
    helper, _ = fake_ufw
    assert _run(helper, "remove", "../../etc").returncode != 0
    assert _run(helper, "apply", "x;y", "tcp", "25565", "25565", "10.10.0.10", "25565", "public", "eth0").returncode != 0


# --- Backend: Prüfung, IP-Vergabe, API ---------------------------------------

def test_validate_rules(client):
    from hydrahive.containers import ports as cp

    for args, code in [
        (("tcp", 8001, 8001, 8001, "public"), "container_port_reserved"),
        (("tcp", 41640, 41645, 41640, "public"), "container_port_reserved"),
        (("tcp", 900, 900, 900, "public"), "container_port_range_invalid"),
        (("tcp", 30000, 30200, 30000, "public"), "container_port_range_invalid"),
        (("tcp", 30010, 30000, 30000, "public"), "container_port_range_invalid"),
        (("sctp", 30000, 30000, 30000, "public"), "container_port_range_invalid"),
    ]:
        with pytest.raises(cp.PortError) as exc:
            cp.validate(*args)
        assert exc.value.code == code


def _make_nat_container(name: str) -> str:
    from hydrahive.containers import db as cdb
    from hydrahive.containers import nat

    c = cdb.create(owner="admin", name=name, image="images:debian/12", network_mode="nat")
    nat.set_ipv4(c.container_id, nat.allocate_ipv4())
    return c.container_id


def test_ip_allocation_unique(client):
    from hydrahive.containers import db as cdb
    from hydrahive.containers import nat

    a, b = _make_nat_container("nat-ip-a"), _make_nat_container("nat-ip-b")
    try:
        ia, ib = nat.get_ipv4(a), nat.get_ipv4(b)
        assert ia != ib and ia.startswith("10.10.0.") and ib.startswith("10.10.0.")
    finally:
        cdb.delete(a)
        cdb.delete(b)


@pytest.fixture
def no_apply(monkeypatch):
    from hydrahive.containers import ports as cp

    calls: list = []

    async def fake_apply(name, ip, rule):
        calls.append(("apply", name, ip, rule.scope))
        cp._mark(rule.id, error=None)

    async def fake_remove(name, rule):
        calls.append(("remove", name, rule.id))

    monkeypatch.setattr(cp, "apply", fake_apply)
    monkeypatch.setattr(cp, "remove", fake_remove)
    return calls


def test_api_port_flow(client, admin_headers, no_apply):
    from hydrahive.containers import db as cdb

    cid = _make_nat_container("nat-api")
    try:
        r = client.post(f"/api/containers/{cid}/ports", headers=admin_headers,
                        json={"protocol": "tcp", "host_port_start": 25565, "scope": "public", "label": "Minecraft"})
        assert r.status_code == 201, r.text
        rule = r.json()
        assert rule["container_port_start"] == 25565 and rule["host_port_end"] == 25565

        clash = client.post(f"/api/containers/{cid}/ports", headers=admin_headers,
                            json={"protocol": "tcp", "host_port_start": 25560, "host_port_end": 25570})
        assert clash.status_code == 409
        udp_same = client.post(f"/api/containers/{cid}/ports", headers=admin_headers,
                               json={"protocol": "udp", "host_port_start": 25565})
        assert udp_same.status_code == 201

        reserved = client.post(f"/api/containers/{cid}/ports", headers=admin_headers,
                               json={"protocol": "tcp", "host_port_start": 8001})
        assert reserved.status_code == 400

        p = client.patch(f"/api/containers/{cid}/ports/{rule['id']}", headers=admin_headers, json={"scope": "tailnet"})
        assert p.status_code == 200 and p.json()["scope"] == "tailnet"

        listing = client.get(f"/api/containers/{cid}/ports", headers=admin_headers).json()
        assert listing["ipv4"].startswith("10.10.0.") and len(listing["ports"]) == 2

        assert client.delete(f"/api/containers/{cid}/ports/{rule['id']}", headers=admin_headers).status_code == 204
        assert ("remove", "nat-api", rule["id"]) in no_apply
    finally:
        cdb.delete(cid)


def test_api_rejects_ports_on_bridged(client, admin_headers, no_apply):
    from hydrahive.containers import db as cdb

    c = cdb.create(owner="admin", name="bridged-noports", image="images:debian/12", network_mode="bridged")
    try:
        r = client.post(f"/api/containers/{c.container_id}/ports", headers=admin_headers,
                        json={"protocol": "tcp", "host_port_start": 25565})
        assert r.status_code == 400
        assert no_apply == []
    finally:
        cdb.delete(c.container_id)


def test_network_modes_endpoint(client, admin_headers, monkeypatch):
    from hydrahive.containers import nat

    monkeypatch.setattr(nat, "bridge_available", lambda: False)
    monkeypatch.setattr(nat, "nat_available", lambda: True)
    r = client.get("/api/containers/network-modes", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == {"bridged": False, "nat": True, "isolated": True, "default": "nat"}


def test_delete_container_drops_port_rows(client, no_apply):
    from hydrahive.containers import db as cdb
    from hydrahive.containers import ports as cp

    cid = _make_nat_container("nat-del")
    cp.create(cid, "tcp", 31000, 31000, 31000, "off", "x")
    cdb.delete(cid)
    assert cp.list_for(cid) == []
