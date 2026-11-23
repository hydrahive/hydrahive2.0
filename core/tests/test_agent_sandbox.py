"""Agenten-Sandbox (bubblewrap) – Ziel hydrahive2-modules/ziele/agenten-projekt-isolation.md, Etappe B2a, P1/P2.

Die Angriffe vom 20.11.2026 (ssh-Zugänge, sudo, pg_mirror.dsn, users.json, /proc/*/environ) und der Download vom
22.11. laufen hier ECHT in bwrap – nicht über eine Wortliste. Sie müssen an den Rechten scheitern, auch verschleiert
(base64, python -c), weil die Dateien in der Sandbox gar nicht existieren.
Ohne bwrap (manche CI-Runner) werden die Echt-Tests übersprungen; die reinen Funktionen laufen immer.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from hydrahive.tools import _launcher_sandbox as sb
from hydrahive.tools import _sandbox_select as sel


def _bwrap_works() -> bool:
    if not sb.available():
        return False
    try:
        return subprocess.run([sb._BWRAP, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
                               "--unshare-pid", "true"], capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


needs_bwrap = pytest.mark.skipif(not _bwrap_works(), reason="bubblewrap nicht nutzbar auf diesem Rechner")


def _run(ws: Path, cmd: str, read_only=None, cwd: Path | None = None):
    return asyncio.run(sb.SandboxLauncher(ws, read_only=read_only).run(cmd, cwd=cwd or ws, timeout=30, env={
        "PATH": "/usr/bin:/bin", "HH_SECRET_KEY": "geheim-im-dienst", "GH_TOKEN": "ghp_erlaubt"}))


@pytest.fixture
def secret_tree(tmp_path, monkeypatch):
    """Nachbau: Geheimnisse und fremder Workspace unter einem Pfad, der in der Sandbox versteckt wird."""
    root = tmp_path / "srvroot"
    (root / "secrets").mkdir(parents=True)
    (root / "secrets" / "pg_mirror.dsn").write_text("postgresql://u:pw@h/db")
    (root / "secrets" / "users.json").write_text("{}")
    ws = root / "workspaces" / "p1"
    other = root / "workspaces" / "p2"
    ws.mkdir(parents=True)
    other.mkdir(parents=True)
    (other / "fremd.txt").write_text("fremd")
    monkeypatch.setattr(sb, "_HIDDEN", sb._HIDDEN + (str(root),))
    return root, ws, other


# ---------- reine Funktionen (laufen überall) ----------

def test_argumente_verstecken_geheimnisse_vor_dem_workspace(tmp_path):
    args = sb.sandbox_args(tmp_path, tmp_path)
    for hidden in ("/etc/hydrahive2", "/var/lib/hydrahive2", "/home", "/root", "/srv"):
        if os.path.isdir(hidden):
            assert ["--tmpfs", hidden] == args[args.index(hidden) - 1: args.index(hidden) + 1]
    ws = str(tmp_path.resolve())
    i_ws = len(args) - 1 - args[::-1].index("--bind")
    assert args[i_ws + 1] == ws and args.index("--ro-bind") < i_ws          # Workspace NACH dem Verstecken
    assert "--unshare-pid" in args and "--die-with-parent" in args


def test_umgebung_ohne_dienstgeheimnisse():
    env = sb.sandbox_env({"PATH": "/usr/bin", "HH_SECRET_KEY": "x", "HH_PG_MIRROR_DSN": "y", "GH_TOKEN": "t",
                          "HOME": "/home/hydrahive"})
    assert env == {"PATH": "/usr/bin", "GH_TOKEN": "t", "LANG": "C.UTF-8"}


@pytest.mark.parametrize("flag,kind,expected", [
    ("on", "project", True), ("on", "specialist", True), ("on", None, True), ("on", "master", False),
    ("", "project", False), ("off", "specialist", False),
])
def test_auswahl(monkeypatch, flag, kind, expected):
    monkeypatch.setenv("HH_AGENT_SANDBOX", flag)
    monkeypatch.setattr(sel, "_agent_type", lambda _a: kind)

    class C:
        agent_id = "a"
    assert sel.wants_sandbox(C()) is expected


def test_ohne_bwrap_wird_nicht_ungeschuetzt_ausgefuehrt(monkeypatch, tmp_path):
    monkeypatch.setattr(sb, "available", lambda: False)
    marker = tmp_path / "lief"
    res = asyncio.run(sb.SandboxLauncher(tmp_path).run(f"touch {marker}", cwd=tmp_path))
    assert res.exit_code == -1 and "Sandbox nicht verfügbar" in res.stderr and not marker.exists()


# ---------- echt in bwrap ----------

@needs_bwrap
def test_arbeit_im_workspace_geht(secret_tree):
    _, ws, _ = secret_tree
    res = _run(ws, "echo hallo > a.txt && cat a.txt && echo $HOME && git --version >/dev/null && echo git-ok")
    assert res.exit_code == 0, res.stderr
    assert "hallo" in res.stdout and str(ws / ".home") in res.stdout and "git-ok" in res.stdout
    assert (ws / "a.txt").read_text().strip() == "hallo"


@needs_bwrap
@pytest.mark.parametrize("cmd", [
    "cat {root}/secrets/pg_mirror.dsn",
    "ls {root}/workspaces/p2",
    "cat {root}/workspaces/p2/fremd.txt",
    "echo Y2F0IHtyb290fS9zZWNyZXRzL3VzZXJzLmpzb24K | base64 -d >/dev/null; cat {root}/secrets/users.json",
    "python3 -c \"print(open('{root}/secrets/pg_mirror.dsn').read())\"",
])
def test_geheimnisse_und_fremde_projekte_unsichtbar(secret_tree, cmd):
    root, ws, _ = secret_tree
    res = _run(ws, cmd.format(root=root))
    assert res.exit_code != 0 and "postgresql://" not in res.stdout and "fremd" not in res.stdout, res.stdout


@needs_bwrap
@pytest.mark.parametrize("path", ["/etc/hydrahive2", "/var/lib/hydrahive2", "/home", "/root"])
def test_echte_geheimnis_ordner_sind_leer(tmp_path, path):
    if not os.path.isdir(path):
        pytest.skip(f"{path} gibt es hier nicht")
    res = _run(tmp_path, f"ls -A {path} | wc -l")
    assert res.stdout.strip() == "0", f"{path} sichtbar: {res.stdout}"


@needs_bwrap
def test_dienstumgebung_und_fremde_prozesse_unsichtbar(tmp_path):
    res = _run(tmp_path, "echo \"[$HH_SECRET_KEY]\"; ls /proc | grep -cE '^[0-9]+$'; cat /proc/1/environ | tr '\\0' ' '")
    assert "[geheim-im-dienst]" not in res.stdout and "[]" in res.stdout
    assert int(res.stdout.splitlines()[1]) < 15                          # nur eigene Prozesse
    assert "HH_SECRET_KEY" not in res.stdout


@needs_bwrap
def test_system_nur_lesend(tmp_path):
    res = _run(tmp_path, "touch /usr/hh-probe 2>&1; touch /etc/hh-probe 2>&1; touch /opt/hh-probe 2>&1; echo ende")
    assert "ende" in res.stdout and not Path("/usr/hh-probe").exists() and not Path("/etc/hh-probe").exists()


@needs_bwrap
def test_tmp_der_sandbox_ist_privat_und_fluechtig(tmp_path):
    """Selbst wenn ein Download an der Wortliste vorbeikäme: /tmp der Sandbox ist privat und weg, wenn der Befehl
    endet – nichts landet im /tmp des Servers (Vorfall 22.11.: /tmp/pwsh)."""
    import uuid
    name = f"/tmp/hh-sandbox-probe-{uuid.uuid4().hex}"
    res = _run(tmp_path, f"echo x > {name} && cat {name}")
    assert res.exit_code == 0 and res.stdout.strip() == "x"
    assert not Path(name).exists()


@needs_bwrap
def test_verknuepftes_projekt_nur_lesend(secret_tree):
    _, ws, other = secret_tree
    res = _run(ws, f"cat {other}/fremd.txt && touch {other}/neu 2>&1; echo ende", read_only=[other])
    assert "fremd" in res.stdout and not (other / "neu").exists()


@needs_bwrap
def test_cwd_ausserhalb_wird_auf_workspace_gezogen(secret_tree):
    root, ws, _ = secret_tree
    res = _run(ws, "pwd", cwd=root)
    assert res.stdout.strip() == str(ws.resolve())


@needs_bwrap
def test_shell_exec_eines_projekt_agenten_laeuft_in_der_sandbox(monkeypatch, tmp_path):
    """Ende-zu-Ende über das echte Werkzeug: Schalter an, Projekt-Agent → /etc/hydrahive2 leer, Workspace geht."""
    from hydrahive.tools import _shell_guard, shell
    from hydrahive.tools.base import ToolContext

    monkeypatch.setenv("HH_AGENT_SANDBOX", "on")
    monkeypatch.setattr(sel, "_agent_type", lambda _a: "project")
    monkeypatch.setattr(_shell_guard, "agent_type", lambda _a: "project")
    ctx = ToolContext(session_id="s", agent_id="pa", user_id="till", workspace=tmp_path)
    res = asyncio.run(shell._execute({"cmd": "ls -A /var/lib/hydrahive2 | wc -l; echo $HOME; touch ok.txt"}, ctx))
    assert res.success, res.error
    out = res.output["stdout"]
    assert out.splitlines()[0].strip() == "0" and str(tmp_path.resolve() / ".home") in out
    assert (tmp_path / "ok.txt").exists()


def test_buddy_und_schalter_aus_bleiben_beim_alten_launcher(monkeypatch, tmp_path):
    from hydrahive.tools import _launcher_container
    from hydrahive.tools._launcher import DevLauncher
    from hydrahive.tools.base import ToolContext

    ctx = ToolContext(session_id="s", agent_id="b", user_id="till", workspace=tmp_path)
    monkeypatch.setenv("HH_AGENT_SANDBOX", "on")
    monkeypatch.setattr(sel, "_agent_type", lambda _a: "master")
    assert isinstance(_launcher_container.launcher_for(ctx), DevLauncher)
    monkeypatch.setenv("HH_AGENT_SANDBOX", "")
    monkeypatch.setattr(sel, "_agent_type", lambda _a: "project")
    assert isinstance(_launcher_container.launcher_for(ctx), DevLauncher)
    monkeypatch.setenv("HH_AGENT_SANDBOX", "on")
    assert isinstance(_launcher_container.launcher_for(ctx), sb.SandboxLauncher)
