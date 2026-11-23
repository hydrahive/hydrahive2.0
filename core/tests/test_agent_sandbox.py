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
    return root, ws, other


# ---------- reine Funktionen (laufen überall) ----------

def test_argumente_allowlist_ohne_wurzel(tmp_path):
    """Kein `--ro-bind / /` mehr: nur System-Ordner, Workspace zuletzt beschreibbar."""
    args = sb.sandbox_args(tmp_path, tmp_path, private=[], system=[Path("/usr"), Path("/etc")])
    pairs = [(args[i], args[i + 1]) for i in range(len(args) - 1)]
    assert ("--ro-bind", "/") not in pairs
    assert ("--ro-bind", "/usr") in pairs and ("--ro-bind", "/etc") in pairs
    ws = str(tmp_path.resolve())
    assert args[len(args) - 1 - args[::-1].index("--bind") + 1] == ws
    assert "--unshare-pid" in args and "--die-with-parent" in args


def test_keine_festen_pfade_dieses_rechners_im_modul():
    """Till 23.11.: nichts nur auf uns gebaut – keine Daten-/Platten-Pfade im Sandbox-Kern."""
    src = Path(sb.__file__).read_text(encoding="utf-8")
    code = src.split('"""', 2)[2]                       # Modul-Doku ausgenommen
    for fixed in ("/var/lib/hydrahive2", "/etc/hydrahive2", "/srv", "/home", "/mnt", "/media", "hh-arbeit"):
        assert f'"{fixed}' not in code, fixed


def test_private_ordner_kommen_aus_den_einstellungen(monkeypatch, tmp_path):
    data, conf, logs = tmp_path / "d", tmp_path / "c", tmp_path / "l"
    for d in (data, conf, logs):
        d.mkdir()
    from hydrahive.settings import settings
    monkeypatch.setattr(type(settings), "data_dir", property(lambda self: data))
    monkeypatch.setattr(type(settings), "config_dir", property(lambda self: conf))
    monkeypatch.setattr(type(settings), "log_dir", property(lambda self: logs))
    monkeypatch.setattr("hydrahive.archive.location.archive_root", lambda: tmp_path / "arch")
    got = sb.private_dirs()
    assert data.resolve() in got and conf.resolve() in got and logs.resolve() in got
    assert (tmp_path / "arch").resolve() in got


def test_system_ordner_in_privatem_ordner_wird_nicht_eingeblendet(tmp_path):
    priv = tmp_path / "daten"
    (priv / "bin").mkdir(parents=True)
    args = sb.sandbox_args(tmp_path / "daten", tmp_path, private=[priv], system=[priv / "bin"])
    assert str((priv / "bin").resolve()) not in [args[i + 1] for i, a in enumerate(args) if a == "--ro-bind"]


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
def test_echte_geheimnis_ordner_sind_leer(tmp_path, monkeypatch, path):
    """Echte Ordner dieses Rechners. Die Testumgebung lenkt HH_CONFIG_DIR/HH_DATA_DIR um; hier gelten die
    Standard-Einstellungen wie im Betrieb (private_dirs liest sonst die Test-Ordner)."""
    if not os.path.isdir(path):
        pytest.skip(f"{path} gibt es hier nicht")
    monkeypatch.setattr(sb, "private_dirs", lambda: [Path("/etc/hydrahive2"), Path("/var/lib/hydrahive2")])
    res = _run(tmp_path, f"ls -A {path} 2>/dev/null | wc -l")
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


# ---------- B3-1/B3-2: fremde Plattenaufteilungen, echt in bwrap ----------

@pytest.fixture
def fremder_rechner(tmp_path, monkeypatch):
    """Nachbau einer anderen Installation: System-Ordner `sys/`, Konfig MITTEN darin (wie /etc/hydrahive2),
    Daten unter einem „Programm“-Ordner (wie /opt/…), Archiv auf einer fremden Platte (`platte2/`)."""
    root = tmp_path / "rechner"
    sysdir = root / "sys"
    conf = sysdir / "hydrahive"
    prog = root / "opt-hh"
    data = prog / "daten"
    archiv = root / "platte2" / "hydrahive-archiv"
    for d in (conf, data / "workspaces" / "p1", data / "workspaces" / "p2", archiv, sysdir / "share"):
        d.mkdir(parents=True)
    (conf / "api_keys.json").write_text('{"k": "sk-geheim"}')
    (data / "sessions.db").write_text("db")
    (data / "workspaces" / "p2" / "fremd.txt").write_text("fremd")
    (archiv / "alt.tar").write_text("archiv")
    (sysdir / "share" / "ok.txt").write_text("system-ok")
    (root / "platte2" / "sonstiges.txt").write_text("platte2")
    monkeypatch.setattr(sb, "private_dirs", lambda: [data.resolve(), conf.resolve(), archiv.resolve()])
    monkeypatch.setattr(sb, "system_ro", lambda: [Path(d) for d in sb._SYSTEM_RO] + [sysdir, prog])
    return {"root": root, "sys": sysdir, "conf": conf, "prog": prog, "data": data, "archiv": archiv,
            "ws": data / "workspaces" / "p1"}


@needs_bwrap
def test_fremde_installation_geheimnisse_unsichtbar(fremder_rechner):
    f = fremder_rechner
    probes = [
        ("system", f"cat {f['sys']}/share/ok.txt"),
        ("konfig", f"ls -A {f['conf']} | wc -l"),
        ("schluessel", f"cat {f['conf']}/api_keys.json 2>/dev/null || echo FEHLT"),
        ("daten", f"ls -A {f['data']} | tr '\\n' ' '"),
        ("workspaces", f"ls -A {f['data']}/workspaces | tr '\\n' ' '"),
        ("archiv", f"cat {f['archiv']}/alt.tar 2>/dev/null || echo FEHLT"),
        ("platte2", f"cat {f['root']}/platte2/sonstiges.txt 2>/dev/null || echo FEHLT"),
        ("schreiben", "echo hallo > neu.txt && echo ok"),
    ]
    cmd = "; ".join(f"echo \"{k}=$({c})\"" for k, c in probes)
    res = _run(f["ws"], cmd)
    got = dict(line.split("=", 1) for line in res.stdout.splitlines() if "=" in line)
    assert got["system"] == "system-ok"                     # System-Ordner sichtbar
    assert got["konfig"].strip() == "0"                     # Konfig mitten im System-Ordner: leer
    assert got["schluessel"] == "FEHLT"
    assert got["daten"].split() == ["workspaces"]           # sessions.db u. a. fehlen
    assert got["workspaces"].split() == ["p1"]              # fremder Workspace fehlt
    assert got["archiv"] == "FEHLT" and got["platte2"] == "FEHLT"
    assert got["schreiben"] == "ok" and (f["ws"] / "neu.txt").exists()


@needs_bwrap
@pytest.mark.parametrize("path", ["/srv", "/mnt", "/media", "/home", "/root", "/var/lib", "/var/log"])
def test_nicht_eingeblendete_orte_fehlen(tmp_path, path):
    """B3-2: Orte außerhalb der Allowlist gibt es in der Sandbox nicht – ohne dass sie im Kern stehen."""
    res = _run(tmp_path, f"ls -A {path} 2>/dev/null | wc -l")
    assert res.stdout.strip() == "0", f"{path}: {res.stdout}"


@needs_bwrap
def test_programmordner_lesend_und_python_laeuft(tmp_path):
    from hydrahive.settings import settings
    base = Path(settings.base_dir)
    if not (base / ".venv" / "bin" / "python").exists():
        pytest.skip("kein installierter Programmordner")
    res = _run(tmp_path, f"{base}/.venv/bin/python -c 'import sys; print(sys.version_info[0])'; "
                         f"touch {base}/hh-probe 2>&1; echo ende")
    assert res.stdout.splitlines()[0] == "3" and not (base / "hh-probe").exists()


@needs_bwrap
def test_namensaufloesung_geht(tmp_path):
    res = _run(tmp_path, "getent hosts localhost >/dev/null && echo dns-ok; cat /etc/resolv.conf >/dev/null && echo rc")
    assert "dns-ok" in res.stdout and "rc" in res.stdout
