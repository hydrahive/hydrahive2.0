"""Portfreigaben auf dem Mac (Plan docs/plans/mac-containers.md §4, Weg A – Till 21.10.2026).

Linux: proxy device auf der WAN-/Tailscale-IP + ufw-Regel über den Root-Helfer hh-portforward.
Mac: Incus läuft in einer Colima-VM; WAN- und Tailscale-Adresse gehören dem Mac, nicht der VM, und es gibt weder ufw
noch den Root-Helfer. Darum: proxy device in der VM lauscht auf allen VM-Adressen, der Kern leitet vom Mac
(gewählte Adresse) per TCP an die VM weiter. Nur TCP, nur Ports ≥ 1024 (wie die Linux-Prüfung).
"""
from __future__ import annotations

import asyncio
import socket

import pytest

from hydrahive.containers import _platform, mac_forward
from hydrahive.containers import ports as cp


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _echo_server(port: int) -> asyncio.base_events.Server:
    async def handle(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        data = await r.read(100)
        w.write(b"echo:" + data)
        await w.drain()
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def _ask(port: int, msg: bytes) -> bytes:
    r, w = await asyncio.open_connection("127.0.0.1", port)
    w.write(msg)
    await w.drain()
    data = await asyncio.wait_for(r.read(100), timeout=3)
    w.close()
    return data


# --- Weiterleiter ---------------------------------------------------------------------------------------

def test_forwarder_passes_data_both_ways():
    async def run():
        target = _free_port()
        listen = _free_port()
        srv = await _echo_server(target)
        fw = mac_forward.Forwarder()
        try:
            await fw.open("r1", "127.0.0.1", listen, listen, "127.0.0.1", target)
            assert await _ask(listen, b"hallo") == b"echo:hallo"
            assert fw.active() == {"r1"}
        finally:
            await fw.close_all()
            srv.close()
            await srv.wait_closed()
    asyncio.run(run())


def test_forwarder_range_maps_each_port():
    async def run():
        t1, t2 = _free_port(), _free_port()
        # zusammenhängender Bereich: zwei freie, benachbarte Ports suchen
        for base in range(41000, 41200, 2):
            try:
                for p in (base, base + 1):
                    with socket.socket() as s:
                        s.bind(("127.0.0.1", p))
                break
            except OSError:
                continue
        tbase = None
        for b in range(42000, 42200, 2):
            try:
                for p in (b, b + 1):
                    with socket.socket() as s:
                        s.bind(("127.0.0.1", p))
                tbase = b
                break
            except OSError:
                continue
        s1, s2 = await _echo_server(tbase), await _echo_server(tbase + 1)
        fw = mac_forward.Forwarder()
        try:
            await fw.open("r2", "127.0.0.1", base, base + 1, "127.0.0.1", tbase)
            assert await _ask(base, b"a") == b"echo:a"
            assert await _ask(base + 1, b"b") == b"echo:b"
        finally:
            await fw.close_all()
            for s in (s1, s2):
                s.close()
                await s.wait_closed()
        del t1, t2
    asyncio.run(run())


def test_forwarder_close_frees_port():
    async def run():
        listen = _free_port()
        fw = mac_forward.Forwarder()
        await fw.open("r3", "127.0.0.1", listen, listen, "127.0.0.1", _free_port())
        await fw.close("r3")
        assert fw.active() == set()
        with socket.socket() as s:          # Port wieder frei
            s.bind(("127.0.0.1", listen))
    asyncio.run(run())


def test_forwarder_reopen_replaces_old_listener():
    async def run():
        t_old, t_new, listen = _free_port(), _free_port(), _free_port()
        old = await _echo_server(t_old)

        async def handle(r, w):
            await r.read(100)
            w.write(b"neu")
            await w.drain()
            w.close()
        new = await asyncio.start_server(handle, "127.0.0.1", t_new)
        fw = mac_forward.Forwarder()
        try:
            await fw.open("r4", "127.0.0.1", listen, listen, "127.0.0.1", t_old)
            await fw.open("r4", "127.0.0.1", listen, listen, "127.0.0.1", t_new)   # gleiche Freigabe, neues Ziel
            assert await _ask(listen, b"x") == b"neu"
        finally:
            await fw.close_all()
            for s in (old, new):
                s.close()
                await s.wait_closed()
    asyncio.run(run())


def test_forwarder_busy_port_raises_port_error():
    async def run():
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen()
            port = busy.getsockname()[1]
            fw = mac_forward.Forwarder()
            with pytest.raises(cp.PortError) as e:
                await fw.open("r5", "127.0.0.1", port, port, "127.0.0.1", _free_port())
            assert e.value.code == "container_port_apply_failed"
            assert fw.active() == set()
    asyncio.run(run())


def test_forwarder_target_down_closes_client():
    async def run():
        listen = _free_port()
        fw = mac_forward.Forwarder()
        try:
            await fw.open("r6", "127.0.0.1", listen, listen, "127.0.0.1", _free_port())
            r, w = await asyncio.open_connection("127.0.0.1", listen)
            assert await asyncio.wait_for(r.read(10), timeout=3) == b""      # sauber geschlossen, kein Hängen
            w.close()
        finally:
            await fw.close_all()
    asyncio.run(run())


# --- ports.apply / remove auf dem Mac ------------------------------------------------------------------

@pytest.fixture
def mac_ports(monkeypatch):
    monkeypatch.setattr(_platform, "is_mac", lambda: True)
    calls: list[tuple] = []

    async def remove_device(name, dev):
        calls.append(("remove_device", name, dev))

    async def add_proxy_device(name, dev, *, listen, connect):
        calls.append(("add_proxy_device", name, dev, listen, connect))

    async def helper(*args):
        calls.append(("helper", *args))

    class FW:
        async def open(self, rid, host, start, end, target_host, target_start):
            calls.append(("open", rid, host, start, end, target_host, target_start))

        async def close(self, rid):
            calls.append(("close", rid))

    monkeypatch.setattr(cp.incus, "remove_device", remove_device)
    monkeypatch.setattr(cp.incus, "add_proxy_device", add_proxy_device)
    monkeypatch.setattr(cp, "_helper", helper)
    monkeypatch.setattr(cp, "_mark", lambda rid, error: calls.append(("mark", rid, error)))
    monkeypatch.setattr(mac_forward, "FORWARDER", FW())
    monkeypatch.setattr(mac_forward, "vm_address", lambda: "192.168.64.2")
    monkeypatch.setattr(cp.nat, "wan_ipv4", lambda: "192.168.178.186")

    async def ts():
        return "100.84.1.2"
    monkeypatch.setattr(cp, "_tailscale_ipv4", ts)
    return calls


def _rule(scope: str, proto: str = "tcp", start: int = 30080, end: int = 30080, cstart: int = 80) -> cp.PortRule:
    return cp.PortRule(id="0192aaaa-bbbb-7ccc-8ddd-eeeeffff0001", container_id="c1", protocol=proto,
                       host_port_start=start, host_port_end=end, container_port_start=cstart, scope=scope,
                       label="", created_at="x")


def test_mac_apply_public_forwards_from_lan_address(mac_ports):
    asyncio.run(cp.apply("web", "10.10.0.10", _rule("public")))
    dev = "hhp-eeeeffff0001"
    assert ("add_proxy_device", "web", dev, "tcp:0.0.0.0:30080", "tcp:10.10.0.10:80") in mac_ports
    assert ("open", _rule("public").id, "192.168.178.186", 30080, 30080, "192.168.64.2", 30080) in mac_ports
    assert not any(c[0] == "helper" for c in mac_ports)       # kein sudo hh-portforward / ufw auf dem Mac
    assert mac_ports[-1] == ("mark", _rule("public").id, None)


def test_mac_apply_tailnet_binds_tailscale_address(mac_ports):
    asyncio.run(cp.apply("web", "10.10.0.10", _rule("tailnet")))
    assert ("open", _rule("tailnet").id, "100.84.1.2", 30080, 30080, "192.168.64.2", 30080) in mac_ports


def test_mac_apply_off_closes_forwarder(mac_ports):
    asyncio.run(cp.apply("web", "10.10.0.10", _rule("off")))
    assert ("close", _rule("off").id) in mac_ports
    assert not any(c[0] in ("open", "add_proxy_device") for c in mac_ports)


def test_mac_apply_udp_refused(mac_ports):
    with pytest.raises(cp.PortError) as e:
        asyncio.run(cp.apply("web", "10.10.0.10", _rule("public", proto="udp")))
    assert e.value.params.get("detail") == "mac_udp_unsupported"
    assert ("mark", _rule("public").id, "mac_udp_unsupported") in mac_ports


def test_mac_apply_without_vm_address_fails(mac_ports, monkeypatch):
    monkeypatch.setattr(mac_forward, "vm_address", lambda: None)
    with pytest.raises(cp.PortError):
        asyncio.run(cp.apply("web", "10.10.0.10", _rule("public")))


def test_mac_remove_closes_forwarder_no_helper(mac_ports):
    asyncio.run(cp.remove("web", _rule("public")))
    assert ("close", _rule("public").id) in mac_ports
    assert not any(c[0] == "helper" for c in mac_ports)


def test_linux_apply_unchanged(monkeypatch):
    """Linux: Proxy auf der WAN-Adresse + Root-Helfer, kein Weiterleiter."""
    monkeypatch.setattr(_platform, "is_mac", lambda: False)
    calls: list[tuple] = []

    async def remove_device(name, dev):
        calls.append(("remove_device",))

    async def add_proxy_device(name, dev, *, listen, connect):
        calls.append(("add_proxy_device", listen, connect))

    async def helper(*args):
        calls.append(("helper", *args))

    class FW:
        async def open(self, *a):
            pytest.fail("Weiterleiter unter Linux benutzt")

        async def close(self, *a):
            pytest.fail("Weiterleiter unter Linux benutzt")

    monkeypatch.setattr(cp.incus, "remove_device", remove_device)
    monkeypatch.setattr(cp.incus, "add_proxy_device", add_proxy_device)
    monkeypatch.setattr(cp, "_helper", helper)
    monkeypatch.setattr(cp, "_mark", lambda rid, error: None)
    monkeypatch.setattr(mac_forward, "FORWARDER", FW())
    monkeypatch.setattr(cp.nat, "wan_ipv4", lambda: "203.0.113.5")
    monkeypatch.setattr(cp.nat, "wan_interface", lambda: "eth0")
    asyncio.run(cp.apply("web", "10.10.0.10", _rule("public")))
    assert ("add_proxy_device", "tcp:203.0.113.5:30080", "tcp:10.10.0.10:80") in calls
    assert ("helper", "apply", _rule("public").id, "tcp", "30080", "30080", "10.10.0.10", "80", "public", "eth0") in calls
    calls.clear()
    asyncio.run(cp.remove("web", _rule("public")))
    assert ("helper", "remove", _rule("public").id) in calls


# --- VM-Adresse ----------------------------------------------------------------------------------------------

def test_vm_address_from_colima_ls(tmp_path, monkeypatch):
    """Die VM wird mit --network-address gestartet; `colima ls --json` (eine Zeile je Profil) nennt dann ihre
    Adresse im Mac-Netz. COLIMA_HOME zeigt auf den Ordner der HydraHive-VM (data_dir/colima)."""
    out = ('{"name":"default","status":"Stopped"}\n'
           '{"name":"hydrahive","status":"Running","address":"192.168.64.2","runtime":"incus"}\n')

    class R:
        returncode = 0
        stdout = out

    seen = []
    monkeypatch.setattr(mac_forward.shutil, "which", lambda n: "/usr/local/lib/hydrahive2/containers/bin/colima")
    monkeypatch.setattr(mac_forward.subprocess, "run", lambda args, **kw: (seen.append((args, kw)), R())[1])
    monkeypatch.setenv("COLIMA_HOME", str(tmp_path / "colima"))
    mac_forward._VM_CACHE.clear()
    assert mac_forward.vm_address() == "192.168.64.2"
    args, kw = seen[0]
    assert args == ["/usr/local/lib/hydrahive2/containers/bin/colima", "ls", "--json"]
    assert kw["env"]["COLIMA_HOME"] == str(tmp_path / "colima")
    mac_forward.vm_address()                       # zweiter Aufruf aus dem Zwischenspeicher
    assert len(seen) == 1


def test_vm_address_none_when_not_running(monkeypatch):
    class R:
        returncode = 0
        stdout = '{"name":"hydrahive","status":"Stopped"}\n'

    monkeypatch.setattr(mac_forward.shutil, "which", lambda n: "/x/colima")
    monkeypatch.setattr(mac_forward.subprocess, "run", lambda args, **kw: R())
    mac_forward._VM_CACHE.clear()
    assert mac_forward.vm_address() is None


def test_vm_address_without_colima(monkeypatch):
    monkeypatch.setattr(mac_forward.shutil, "which", lambda n: None)
    monkeypatch.setattr(mac_forward, "TOOLS_BIN", "/gibt/es/nicht")
    mac_forward._VM_CACHE.clear()
    assert mac_forward.vm_address() is None
