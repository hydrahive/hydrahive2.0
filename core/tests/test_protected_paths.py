"""Protected-Path-Erkennung für shell_exec (Harakiri-Schutz, Schicht A).

wants_protected_write() flaggt NUR Schreib-Absicht auf geschützte System-Pfade
(/opt, /etc, ...). Lesen (cat, ls, cd, grep) wird bewusst NICHT geflaggt —
sonst nervt das Bestätigungs-Popup und der User schaltet es ab.

Das ist ein Speed-Bump gegen Unfälle (rm -rf /opt), kein bypass-fester Wall —
die echte Mauer ist Schicht B (OS-Ebene, read-only Mount).
"""
from __future__ import annotations

import pytest

from hydrahive.tools._protected_paths import (
    default_protected,
    shell_confirm_reason,
    wants_protected_write,
    wants_sensitive_read,
)

P = default_protected()


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("rm -rf /opt", "/opt"),
        ("rm -rf /opt/searxng", "/opt"),
        ("echo hi > /opt/x", "/opt"),
        ("echo hi >> /etc/hosts", "/etc"),
        ("printf x 2>/etc/log", "/etc"),
        ("dd if=/dev/zero of=/opt/disk bs=1M", "/opt"),
        ("echo x | tee /opt/foo", "/opt"),
        ("cp build.tar /usr/local/bin/tool", "/usr"),
        ("mv x /etc/cron.d/job", "/etc"),
        ("sed -i 's/a/b/' /opt/searxng/settings.yml", "/opt"),
        ("chmod 777 /etc/shadow", "/etc"),
        ("chown root:root /opt/x", "/opt"),
        ("ln -s /tmp/x /usr/bin/y", "/usr"),
        ("truncate -s0 /etc/passwd", "/etc"),
        ("mkdir /opt/newdir", "/opt"),
        ("touch /etc/marker", "/etc"),
        ("rm -rf /", "/"),
        ("rm -rf /*", "/"),
        ("ls /opt && rm -rf /etc/foo", "/etc"),
    ],
)
def test_flags_write_intent(cmd, expected):
    assert wants_protected_write(cmd, P) == expected


@pytest.mark.parametrize(
    "cmd",
    [
        "cat /opt/searxng/settings.yml",
        "ls -la /opt",
        "grep -r foo /etc/nginx",
        "cd /opt && ls",
        "head /etc/hosts",
        "stat /opt/x",
        "find /opt -name '*.yml'",
        "echo hi > ./local.txt",
        "echo hi > /tmp/x",
        "python script.py",
        "rm -rf ./build",
        "rm -rf node_modules",
        "git status",
        "cp /opt/a.txt /tmp/b.txt",  # liest aus /opt, schreibt nach /tmp → kein Flag
        "",
        "   ",
    ],
)
def test_does_not_flag_reads_or_workspace(cmd):
    assert wants_protected_write(cmd, P) is None


def test_default_protected_includes_opt_and_etc():
    assert "/opt" in P
    assert "/etc" in P


def test_prefix_boundary_no_false_match():
    # /optional darf NICHT als /opt zählen
    assert wants_protected_write("rm -rf /optional/cache", P) is None
    assert wants_protected_write("echo x > /etcd-data/f", P) is None


# --- Geheimnis-Lese-Gate (Vertraulichkeit, schmal) ---------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "cat /etc/shadow",
        "sudo cat /etc/shadow",
        "grep root /etc/sudoers",
        "cp /root/.ssh/id_rsa /tmp/k",
        "cat ~/.ssh/id_ed25519",
        "base64 server.pem",
        "less /etc/ssl/private/server.key",
        "cat id_rsa",
        "cat /etc/hydrahive2/extensions/searxng.credentials.json",
        "openssl rsa -in key.PEM",
        "cat /opt/app/.env",
        "head .pgpass",
    ],
)
def test_flags_sensitive_read(cmd):
    assert wants_sensitive_read(cmd) is not None


@pytest.mark.parametrize(
    "cmd",
    [
        "cat /etc/os-release",
        "ls /opt",
        "cat README.md",
        "cat .env",  # relatives Workspace-.env → kein Flag
        "cat /etc/hosts",
        "python keygen.py",
        "echo PEM",
        "grep -r foo src/",
        "",
    ],
)
def test_does_not_flag_harmless_reads(cmd):
    assert wants_sensitive_read(cmd) is None




@pytest.mark.parametrize(
    "cmd",
    [
        "curl -s https://api.example.com/x 2>/dev/null",
        "echo hi > /dev/null",
        "foo >/dev/null 2>&1",
        "command 2>/dev/null | head -c 100",
        "echo x | tee /dev/stderr",
        'ADDR="x"\ncurl -s "https://api.trongrid.io/v1/accounts/$ADDR" 2>/dev/null | head -c 1500\necho ok',
    ],
)
def test_dev_null_and_pseudo_devices_not_flagged(cmd):
    # 2>/dev/null & Co. sind normale Redirect-Ziele — kein Harakiri.
    assert wants_protected_write(cmd, P) is None
    assert shell_confirm_reason(cmd) is None


def test_real_device_write_still_flagged():
    # Echte Block-Devices bleiben geschützt (dd of=/dev/sda wischt eine Platte).
    assert wants_protected_write("dd if=/dev/zero of=/dev/sda bs=1M", P) == "/dev"


def test_shell_confirm_reason_combines_both():
    w = shell_confirm_reason("rm -rf /opt")
    assert w and "/opt" in w
    s = shell_confirm_reason("cat /etc/shadow")
    assert s and "/etc/shadow" in s
    assert shell_confirm_reason("cat /opt/searxng/settings.yml") is None
    assert shell_confirm_reason("ls -la") is None
