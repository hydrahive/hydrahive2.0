"""Abgleich Portfreigaben (Datenbank) ↔ ufw-Regeln (docs/specs/container-nat-ports.md, „ufw aus/an und Abgleich“).

Soll: Freigaben public/tailnet an laufenden nat-Containern mit IP. Ist: `hh-portforward list`. Fehlende oder
abweichende Regeln → apply, verwaiste hh-port-Regeln oder scope=off → remove. Echte Datenbank (Test-Umgebung),
der Root-Helfer ist durch eine Aufzeichnung ersetzt.
"""
from __future__ import annotations

from tests._ports_sync_env import _run, _ufw_entry

pytest_plugins = ["tests._ports_sync_env"]  # Fixture `env`


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
    """Auch wenn in der Datenbank (fälschlich) eine Freigabe an einem bridged Container hängt: kein ufw-Eingriff."""
    cp, ps = env["cp"], env["ps"]
    cid = env["container"]("sync-f", mode="bridged")
    from hydrahive.containers import nat
    nat.set_ipv4(cid, "10.10.0.198")
    cp.create(cid, "tcp", 30041, 30041, 30041, "public", "")
    assert _run(ps) == {"applied": 0, "removed": 0, "failed": 0}
    assert env["calls"] == []


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
