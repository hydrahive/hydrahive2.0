"""Harakiri-Schutz: Befehle in Containern (docs/specs/harakiri-confirm-noise.md, Punkt 2).

`incus exec <ct> -- …` führt den Befehl im Container aus, nicht auf dem Host.
Pfade darin sind Container-Pfade → keine Geheimnis-Rückfrage. Ausnahme:
HydraHives eigene Container (HH_PROTECTED_CONTAINERS). Alles, was die Host-Shell
selbst ausführt (Umleitungen, $( ), weitere Befehle), bleibt geprüft.
"""
from __future__ import annotations

import pytest

from hydrahive.tools._protected_paths import default_protected, shell_confirm_reason, wants_protected_write

P = default_protected()

# Echter Fall 11.10.2026 (Test der sudoers-Migration im Wegwerf-Container).
REAL = (
    "cd _work/wt/core-sudo && incus file push installer/lib/sudoers-heal.sh hh-sudotest/root/sudoers-heal.sh "
    ">/dev/null && incus exec hh-sudotest -- bash -c '\n"
    "set -uo pipefail; F=/etc/sudoers.d/hydrahive2-extensions\n"
    "cat > $F <<EOF\nDefaults:hydrahive !requiretty\nEOF\n"
    "chmod 0440 $F; ls -la /etc/sudoers.d/; visudo -c'"
)


@pytest.mark.parametrize(
    "cmd",
    [
        REAL,
        "incus exec hh-sudotest -- cat /etc/sudoers.d/hydrahive2-extensions",
        "incus exec hh-sudotest -- bash -c 'cat /etc/shadow; ls /root/.ssh/id_ed25519'",
        "incus exec --user 0 --cwd /root -T ct -- cat /etc/sudoers",
        "incus exec --env A=1 --env=B=2 ct -- cat /etc/ssl/private/k.pem",
        "incus exec remote:ct -- cat /etc/shadow",
        "incus exec ct cat /etc/shadow",
        "lxc exec ct -- cat /etc/shadow",
        "sudo incus exec ct -- cat /etc/sudoers",
        "for i in 1 2; do incus exec ct -- cat /etc/shadow; done",
        "timeout 30 incus exec ct -- cat /etc/shadow",
        "if incus exec ct -- test -f /etc/shadow; then echo ja; fi",
        "incus exec ct -- bash <<'EOF'\ncat /etc/shadow\nEOF",
        "incus exec ct -- bash -c \"cat /etc/shadow\"",
        "incus exec ct -- sh -c 'echo $(cat /etc/shadow)'",
        # Umleitung in Quotes passiert im Container.
        "incus exec ct -- sh -c 'cat x > /etc/sudoers.d/y'",
    ],
)
def test_container_paths_not_flagged(cmd):
    assert shell_confirm_reason(cmd) is None


@pytest.mark.parametrize(
    "cmd",
    [
        # HydraHives eigene Container bleiben geschützt (Standardliste).
        "incus exec hydrahive2-stt -- cat /etc/shadow",
        "incus exec hydrahive2-tts -- cat /root/.ssh/id_rsa",
        "incus exec local:hydrahive2-tts -- cat /etc/shadow",
        # Name aus einer Variable: unbekannt, könnte ein geschützter Container sein.
        "for c in a b; do incus exec $c -- cat /etc/shadow; done",
        "incus exec \"$CT\" -- cat /etc/shadow",
        # Der Wert einer Option ist nicht der Containername.
        "incus exec --user free hydrahive2-stt -- cat /etc/shadow",
        "incus exec --project free hydrahive2-tts -- cat /etc/shadow",
        # Ohne Containernamen vor `--` ist nicht klar, wohin der Befehl geht.
        "incus exec -- hydrahive2-stt cat /etc/shadow",
        "incus exec -T -- free cat /etc/shadow",
        # Host-Shell führt das selbst aus.
        "incus exec ct -- true; cat /etc/shadow",
        "incus exec ct -- true && cp /root/.ssh/id_rsa /tmp/k",
        "incus exec ct -- tee /x < /etc/shadow",
        "incus exec ct -- cat x > /etc/sudoers.d/evil",
        "incus exec ct -- cat $(cat /etc/shadow)",
        "incus exec ct -- cat `cat /etc/shadow`",
        "incus exec ct -- bash -c \"$(cat /etc/shadow)\"",
        "incus exec ct -- diff <(cat /etc/shadow) x",
        # Kein exec: incus file pull liest auf dem Host / schreibt auf den Host.
        "incus file push /etc/shadow ct/tmp/x",
        "cat /etc/shadow | incus exec ct -- tee /tmp/x",
    ],
)
def test_host_side_still_flagged(cmd):
    assert shell_confirm_reason(cmd) is not None


def test_host_write_redirect_still_flagged():
    assert wants_protected_write("incus exec ct -- cat x > /etc/y", P) == "/etc"


def test_protected_containers_from_env(monkeypatch):
    monkeypatch.setenv("HH_PROTECTED_CONTAINERS", "prod-db, hydrahive2-stt")
    assert shell_confirm_reason("incus exec prod-db -- cat /etc/shadow") is not None
    assert shell_confirm_reason("incus exec hydrahive2-stt -- cat /etc/shadow") is not None
    # Nicht mehr in der Liste → Ausnahme greift.
    assert shell_confirm_reason("incus exec hydrahive2-tts -- cat /etc/shadow") is None
    monkeypatch.setenv("HH_PROTECTED_CONTAINERS", "")
    assert shell_confirm_reason("incus exec hydrahive2-stt -- cat /etc/shadow") is None
