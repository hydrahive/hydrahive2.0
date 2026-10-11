"""hh-portforward bei ausgeschaltetem ufw (docs/specs/container-nat-ports.md, „ufw aus/an und Abgleich“).

Befund VPS 06.10.2026: Bei ausgeschaltetem ufw schrieb der Helfer keine Regel, meldete aber Erfolg → nach `ufw enable`
waren alle Freigaben dicht. Das Ersatz-ufw hier bildet das auf Ubuntu 26.04 / ufw 0.36.2 gemessene Verhalten nach:
Regeln werden auch im ausgeschalteten Zustand gespeichert, `show added` listet sie immer, `status` nur wenn aktiv,
`route delete allow <regeltext>` löscht ohne Nummer, doppeltes Anlegen wird übersprungen.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = Path(__file__).parents[2] / "installer" / "lib" / "hh-portforward"
ID = "0192aaaa-bbbb-7ccc-8ddd-eeeeffff0001"
ID2 = "0192aaaa-bbbb-7ccc-8ddd-eeeeffff0002"

FAKE_UFW = r'''#!/usr/bin/env python3
import json, os, shlex, sys
state = os.environ["FAKE_UFW_STATE"]
d = json.load(open(state)) if os.path.exists(state) else {"active": False, "rules": []}
a = sys.argv[1:]
open(os.environ["FAKE_UFW_LOG"], "a").write(" ".join(a) + "\n")
def save(): json.dump(d, open(state, "w"))
def text(r): return "ufw route " + " ".join(shlex.quote(x) if " " in x else x for x in r)
if a[:1] == ["--force"]: a = a[1:]
if a == ["status"]:
    print("Status: active" if d["active"] else "Status: inactive")
    if d["active"]:
        for r in d["rules"]:
            c = r[r.index("comment") + 1] if "comment" in r else ""
            print(f"x ALLOW FWD y # {c}")
elif a == ["status", "numbered"]:
    print("Status: active" if d["active"] else "Status: inactive")
    if d["active"]:
        for i, r in enumerate(d["rules"], 1):
            c = r[r.index("comment") + 1] if "comment" in r else ""
            print(f"[{i:2}] x ALLOW FWD y # {c}")
elif a == ["show", "added"]:
    print("Added user rules (see 'ufw status' for running firewall):")
    for r in d["rules"]: print(text(r))
elif a[:2] in (["route", "allow"], ["route", "limit"]):
    r = a[1:]
    if r in d["rules"]: print("Skipping adding existing rule")
    else: d["rules"].append(r); save(); print("Rules updated")
elif a[:3] == ["route", "delete", "allow"]:
    r = a[2:]
    if r in d["rules"]: d["rules"].remove(r); save(); print("Rules updated")
    else: print("Could not delete non-existent rule"); sys.exit(0)
elif a[:1] == ["delete"] and len(a) == 2 and a[1].isdigit():
    if not d["active"]: print("ERROR: Could not find rule"); sys.exit(1)
    del d["rules"][int(a[1]) - 1]; save()
else:
    print("ERROR: Invalid syntax", file=sys.stderr); sys.exit(1)
'''


@pytest.fixture
def box(tmp_path: Path):
    ufw = tmp_path / "ufw"
    ufw.write_text(FAKE_UFW)
    ufw.chmod(0o755)
    helper = tmp_path / "hh-portforward"
    src = HELPER.read_text()
    assert 'UFW = "/usr/sbin/ufw"' in src
    helper.write_text(src.replace('UFW = "/usr/sbin/ufw"', f'UFW = "{ufw}"'))
    state, log = tmp_path / "ufw.json", tmp_path / "ufw.log"

    def set_state(active: bool, rules: list[list[str]] | None = None) -> None:
        state.write_text(json.dumps({"active": active, "rules": rules or []}))

    def rules() -> list[list[str]]:
        return json.loads(state.read_text())["rules"]

    def run(*args: str) -> subprocess.CompletedProcess:
        env = {"FAKE_UFW_STATE": str(state), "FAKE_UFW_LOG": str(log), "PATH": "/usr/bin:/bin"}
        return subprocess.run([sys.executable, str(helper), *args], capture_output=True, text=True, timeout=20, env=env)

    return run, set_state, rules


def _rule(pid: str, port: str = "30001", ip: str = "10.10.0.10", iface: str = "eth0", proto: str = "tcp") -> list[str]:
    return ["allow", "in", "on", iface, "out", "on", "hhnat0", "to", ip, "port", port, "proto", proto,
            "comment", f"hh-port:{pid}"]


APPLY = ("apply", ID, "tcp", "30001", "30001", "10.10.0.10", "30001", "public", "eth0")


def test_apply_while_ufw_off_still_stores_the_rule(box):
    run, set_state, rules = box
    set_state(active=False)
    r = run(*APPLY)
    assert r.returncode == 0, r.stderr
    assert rules() == [_rule(ID)]          # gespeichert → greift nach `ufw enable`


def test_apply_replaces_an_old_rule_of_the_same_id_while_off(box):
    run, set_state, rules = box
    set_state(active=False, rules=[_rule(ID, iface="tailscale0")])
    assert run(*APPLY).returncode == 0
    assert rules() == [_rule(ID)]


def test_remove_while_ufw_off_deletes_the_rule(box):
    run, set_state, rules = box
    set_state(active=False, rules=[_rule(ID), _rule(ID2, port="30002")])
    r = run("remove", ID)
    assert r.returncode == 0, r.stderr
    assert rules() == [_rule(ID2, port="30002")]


def test_scope_off_removes_rule_while_ufw_off(box):
    run, set_state, rules = box
    set_state(active=False, rules=[_rule(ID)])
    assert run("apply", ID, "tcp", "30001", "30001", "10.10.0.10", "30001", "off", "eth0").returncode == 0
    assert rules() == []


@pytest.mark.parametrize("active", [True, False])
def test_foreign_rules_are_never_touched(box, active):
    run, set_state, rules = box
    foreign = ["allow", "in", "on", "eth0", "out", "on", "hhnat0", "to", "10.10.0.9", "port", "4444", "proto", "tcp",
               "comment", "fremd"]
    lookalike = _rule(ID + "x")             # andere ID mit gleichem Anfang
    set_state(active=active, rules=[foreign, lookalike, _rule(ID)])
    assert run("remove", ID).returncode == 0
    assert rules() == [foreign, lookalike]


def test_list_reports_stored_rules_even_when_off(box):
    run, set_state, _ = box
    set_state(active=False, rules=[_rule(ID), _rule(ID2, port="27000:27015", iface="tailscale0", proto="udp",
                                                    ip="10.10.0.11")])
    r = run("list")
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    assert got == [
        {"id": ID, "in": "eth0", "ip": "10.10.0.10", "port": "30001", "proto": "tcp"},
        {"id": ID2, "in": "tailscale0", "ip": "10.10.0.11", "port": "27000:27015", "proto": "udp"},
    ]


def test_list_ignores_foreign_and_malformed_lines(box):
    run, set_state, _ = box
    set_state(active=True, rules=[
        ["allow", "22/tcp", "comment", "ssh"],
        _rule(ID),
    ])
    assert [x["id"] for x in json.loads(run("list").stdout)] == [ID]


def test_without_ufw_installed_nothing_to_do(tmp_path):
    helper = tmp_path / "hh-portforward"
    helper.write_text(HELPER.read_text().replace('UFW = "/usr/sbin/ufw"', f'UFW = "{tmp_path / "kein-ufw"}"'))
    env = {"PATH": "/usr/bin:/bin"}
    for args in (APPLY, ("remove", ID)):
        r = subprocess.run([sys.executable, str(helper), *args], capture_output=True, text=True, env=env, timeout=20)
        assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, str(helper), "list"], capture_output=True, text=True, env=env, timeout=20)
    assert r.returncode == 0 and json.loads(r.stdout) == []


def test_rule_with_extra_prefix_is_not_ours(box):
    """Nur genau die Form, die apply schreibt, zählt als eigene Regel – eine Regel mit vorangestelltem Teil
    (z. B. `limit …` oder von Hand mit `from …` ergänzt) bleibt unangetastet (Mutanten-Lücke 11.10.)."""
    run, set_state, rules = box
    # Echte ufw-Ausgabe (26.04): `ufw route limit …` – gleicher Kommentar, aber nicht unsere Form.
    foreign = ["limit"] + _rule(ID)[1:]
    set_state(active=True, rules=[foreign])
    assert json.loads(run("list").stdout) == []
    assert run("remove", ID).returncode == 0
    assert rules() == [foreign]
