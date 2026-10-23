"""macOS-Update (Spec docs/specs/mac-update.md): Verlauf im Update-Fenster, Python-Pakete heil, Frontend-Build.

Befund 20.10.2026: Mac-Nutzer sah im Update-Fenster keinen Verlauf (Backend liest $HH_LOG_DIR, Standard /var/log;
der Mac schreibt nach /usr/local/var/log). Zuvor scheiterte jeder Modellaufruf an gemischten LiteLLM-Dateien.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
LAUNCHD = INSTALLER / "modules-mac" / "50-launchd.sh"
TRIGGERS = INSTALLER / "modules-mac" / "55-launchd-triggers.sh"
UPDATE = INSTALLER / "update-mac.sh"
WRAPPER = INSTALLER / "lib" / "mac-backend-start.sh"
MAC_LOG_DIR = "/usr/local/var/log"


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    """Testumgebung: sudo/launchctl/brew/git/npm als Attrappen, pip im venv als Attrappe mit Steuerdateien."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    calls.write_text("")
    (bin_ / "sudo").write_text('#!/bin/bash\n[ "$1" = "-H" ] && shift; [ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    (bin_ / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{calls}"\n'
                                    'case "$1" in list) echo "123 0 io.hydrahive.backend";; esac\n')
    (bin_ / "brew").write_text("#!/bin/bash\necho /usr/local\n")
    # git: rev-parse liefert alt/neu je nach Aufruf, diff liefert den Inhalt von git_diff.txt
    (bin_ / "git").write_text(f'''#!/bin/bash
echo "git $*" >> "{calls}"
case "$*" in
  *"rev-parse HEAD"*) if [ -f "{tmp_path}/pulled" ]; then echo neu111; else echo alt000; fi;;
  *pull*) touch "{tmp_path}/pulled"; echo "Already up to date.";;
  *diff*) cat "{tmp_path}/git_diff.txt" 2>/dev/null;;
  *"log -1 --format=%H -- frontend/"*) if [ -f "{tmp_path}/git_kaputt" ]; then exit 128; fi
                                       cat "{tmp_path}/frontend_rev.txt" 2>/dev/null || echo fe-rev-1;;
esac
exit 0
''')
    (bin_ / "npm").write_text(f'#!/bin/bash\necho "npm $*" >> "{calls}"\necho "npm-ausgabe $1"\n')
    for f in bin_.iterdir():
        f.chmod(0o755)
    cfg = tmp_path / "etc"
    cfg.mkdir()
    (cfg / "secret_key").write_text("x" * 48 + "\n")
    (cfg / "secret_key").chmod(0o600)
    repo = tmp_path / "repo"
    (repo / "installer" / "lib").mkdir(parents=True)
    (repo / "installer" / "modules-mac").symlink_to(INSTALLER / "modules-mac")
    (repo / "installer" / "lib" / "mac-backend-start.sh").symlink_to(WRAPPER)
    (repo / "installer" / "lib" / "mac-python-heal.sh").symlink_to(INSTALLER / "lib" / "mac-python-heal.sh")
    (repo / "frontend" / "dist").mkdir(parents=True)
    (repo / "frontend" / "dist" / "index.html").write_text("<html/>")
    (repo / "frontend" / "dist" / ".hh-frontend-rev").write_text("fe-rev-1\n")   # Build passt zum Stand
    venv = repo / ".venv" / "bin"
    venv.mkdir(parents=True)
    # pip-Attrappe: Aufrufe protokollieren; `check` meldet den Inhalt von pip_check.txt (dann Exit 1)
    (venv / "pip").write_text(f'''#!/bin/bash
echo "pip $*" >> "{calls}"
if [ "$1" = "check" ]; then
  if [ -s "{tmp_path}/pip_check.txt" ]; then cat "{tmp_path}/pip_check.txt"; exit 1; fi
  echo "No broken requirements found."; exit 0
fi
echo "pip-ausgabe $1"
''')
    # python-Attrappe: `-c import litellm` scheitert, wenn litellm_kaputt existiert
    (venv / "python").write_text(f'''#!/bin/bash
echo "python $*" >> "{calls}"
if [ "$1" = "-c" ] && [[ "$2" == *"import litellm"* ]] && [ -f "{tmp_path}/litellm_kaputt" ]; then
  echo "AttributeError: should_use_litellm_mcp_gateway" >&2; exit 1
fi
exit 0
''')
    for f in venv.iterdir():
        f.chmod(0o755)
    data = tmp_path / "data"
    data.mkdir()
    return {"tmp": tmp_path, "bin": bin_, "cfg": cfg, "repo": repo, "calls": calls, "data": data,
            "plist": tmp_path / "io.hydrahive.backend.plist", "log": tmp_path / "update.log"}


def _env(m: dict) -> dict:
    return {**os.environ, "PATH": f"{m['bin']}:{os.environ['PATH']}",
            "HH_CONFIG_DIR": str(m["cfg"]), "HH_DATA_DIR": str(m["data"]), "HH_REPO_DIR": str(m["repo"]),
            "HH_USER": "tester", "HH_HOST": "127.0.0.1", "HH_PORT": "8001",
            "HH_BACKEND_PLIST": str(m["plist"]), "HH_UPDATE_LOG": str(m["log"])}


def _launchd(m: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(LAUNCHD)], env=_env(m), capture_output=True, text=True, timeout=60)


def _update(m: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(UPDATE)], env=_env(m), capture_output=True, text=True, timeout=60)


def _calls(m: dict) -> str:
    return m["calls"].read_text()


# --- 1. Verlauf im Update-Fenster ------------------------------------------------------------------

def test_plist_sets_log_dir_to_mac_log_folder(mac):
    r = _launchd(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    env = plistlib.loads(mac["plist"].read_bytes())["EnvironmentVariables"]
    assert env["HH_LOG_DIR"] == MAC_LOG_DIR


def test_backend_reads_the_file_the_mac_update_writes():
    """Was das Backend mit diesem HH_LOG_DIR liest, ist genau die Datei des Mac-Updates."""
    text = UPDATE.read_text() + TRIGGERS.read_text()
    assert f"{MAC_LOG_DIR}/hydrahive2-update.log" in text
    code = ("import os; os.environ['HH_LOG_DIR']=%r; from hydrahive.settings import settings; print(settings.update_log)"
            % MAC_LOG_DIR)
    out = subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=60,
                         env={**os.environ, "PYTHONPATH": str(INSTALLER.parent / "core" / "src")})
    assert out.stdout.strip() == f"{MAC_LOG_DIR}/hydrahive2-update.log", out.stderr


def test_update_rewrites_plist_without_log_dir(mac):
    _launchd(mac)
    raw = mac["plist"].read_text()
    start = raw.index("<key>HH_LOG_DIR</key>")
    old = raw[:start] + raw[raw.index("</string>", start) + len("</string>"):]
    mac["plist"].write_text(old)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "HH_LOG_DIR" in mac["plist"].read_text()


def test_update_leaves_current_plist_alone(mac):
    _launchd(mac)
    before = mac["plist"].read_bytes()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert mac["plist"].read_bytes() == before


# --- 2. Python-Pakete heil -------------------------------------------------------------------------

def test_healthy_packages_are_not_reinstalled(mac):
    _launchd(mac)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "pip install" in calls and "-e " in calls and "pip check" in calls
    assert "--force-reinstall" not in calls


def test_broken_package_from_pip_check_is_reinstalled(mac):
    _launchd(mac)
    (mac["tmp"] / "pip_check.txt").write_text("litellm 1.106.0 has requirement openai>=2, but you have openai 1.0.\n"
                                             "fastapi 0.120.0 has requirement starlette<0.50, but you have starlette 0.9.\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "pip install --force-reinstall --no-deps litellm" in calls
    assert "pip install --force-reinstall --no-deps fastapi" in calls
    assert calls.count("--force-reinstall") == 2


def test_broken_litellm_import_is_reinstalled(mac):
    """Gemischte Dateien merkt pip check nicht – der Import zeigt es."""
    _launchd(mac)
    (mac["tmp"] / "litellm_kaputt").touch()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pip install --force-reinstall --no-deps litellm" in _calls(mac)
    assert "LiteLLM" in mac["log"].read_text()


def test_package_names_from_pip_check_are_safe(mac):
    """Nur echte Paketnamen werden übernommen, nichts aus dem Text wird als Befehl ausgeführt."""
    _launchd(mac)
    (mac["tmp"] / "pip_check.txt").write_text("$(touch /tmp/boese) 1.0 has requirement x\n;rm -rf / 2 has requirement y\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--force-reinstall" not in _calls(mac)


# --- 3. Frontend ------------------------------------------------------------------------------------

def test_frontend_change_triggers_build(mac):
    """Neuer Frontend-Stand als der gebaute → bauen, danach steht der neue Stand im Vermerk."""
    _launchd(mac)
    (mac["tmp"] / "frontend_rev.txt").write_text("fe-rev-2\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "npm ci" in calls and "npm run build" in calls
    assert (mac["repo"] / "frontend" / "dist" / ".hh-frontend-rev").read_text().strip() == "fe-rev-2"


def test_build_catches_up_even_if_pull_brought_nothing(mac):
    """Befund Test-Mac 20.10.: Pull brachte nichts Neues mehr, Build war aber 65 Frontend-Änderungen alt."""
    _launchd(mac)
    (mac["repo"] / "frontend" / "dist" / ".hh-frontend-rev").unlink()        # alter Build ohne Vermerk
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "npm run build" in _calls(mac)
    assert (mac["repo"] / "frontend" / "dist" / ".hh-frontend-rev").read_text().strip() == "fe-rev-1"


def test_failed_build_writes_no_marker(mac):
    """Scheitert der Build, darf kein Vermerk entstehen – sonst gälte der kaputte Stand als gebaut."""
    _launchd(mac)
    (mac["tmp"] / "frontend_rev.txt").write_text("fe-rev-2\n")
    (mac["bin"] / "npm").write_text(f'#!/bin/bash\necho "npm $*" >> "{mac["calls"]}"\n[ "$1" = run ] && exit 1\nexit 0\n')
    r = _update(mac)
    assert r.returncode != 0
    assert (mac["repo"] / "frontend" / "dist" / ".hh-frontend-rev").read_text().strip() == "fe-rev-1"
    assert "Frontend-Build fehlgeschlagen" in mac["log"].read_text()


def test_unknown_frontend_rev_builds_only_without_dist(mac):
    """git meldet keinen Stand: mit vorhandenem Build nicht bauen (und das sagen), ohne Build trotzdem bauen."""
    _launchd(mac)
    (mac["tmp"] / "git_kaputt").touch()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "npm run build" not in _calls(mac)
    assert "Frontend-Stand unbekannt" in mac["log"].read_text()
    (mac["repo"] / "frontend" / "dist" / "index.html").unlink()
    mac["calls"].write_text("")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "npm run build" in _calls(mac)


def test_no_frontend_change_no_build(mac):
    _launchd(mac)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "npm run build" not in _calls(mac)


def test_missing_dist_triggers_build(mac):
    _launchd(mac)
    (mac["repo"] / "frontend" / "dist" / "index.html").unlink()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "npm run build" in _calls(mac)


def test_git_runs_as_service_user(mac):
    """Alle git-Aufrufe über sudo -u (sonst „dubious ownership“ als root)."""
    (mac["bin"] / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{mac["calls"]}"\n'
                                     '[ "$1" = "-H" ] && shift; [ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    _launchd(mac)
    mac["calls"].write_text("")
    (mac["tmp"] / "frontend_rev.txt").write_text("fe-rev-2\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac).splitlines()
    git_lines = [c for c in calls if c.startswith("git ")]
    sudo_git = [c for c in calls if c.startswith("sudo -H -u tester git ")]
    assert git_lines and len(sudo_git) == len(git_lines)


# --- 4. Alles im Verlauf ----------------------------------------------------------------------------

def test_pip_and_npm_output_land_in_the_log(mac):
    _launchd(mac)
    (mac["tmp"] / "frontend_rev.txt").write_text("fe-rev-2\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    log = mac["log"].read_text()
    assert "pip-ausgabe install" in log
    assert "npm-ausgabe ci" in log and "npm-ausgabe run" in log
    assert "Update abgeschlossen" in log


def test_update_survives_missing_heal_helper(mac):
    """Fehlt die Hilfsdatei (z. B. Sonderfall beim Wechsel), läuft das Update trotzdem durch und sagt es."""
    _launchd(mac)
    (mac["repo"] / "installer" / "lib" / "mac-python-heal.sh").unlink()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    log = mac["log"].read_text()
    assert "Paketprüfung übersprungen" in log and "Update abgeschlossen" in log


def test_package_named_twice_is_reinstalled_once(mac):
    """pip check nennt ein Paket oft mehrfach (eine Zeile je Abhängigkeit) – einmal neu installieren reicht."""
    _launchd(mac)
    (mac["tmp"] / "pip_check.txt").write_text("litellm 1.106.0 has requirement openai>=2, but you have openai 1.0.\n"
                                             "litellm 1.106.0 has requirement httpx>=0.28, but you have httpx 0.1.\n")
    (mac["tmp"] / "litellm_kaputt").touch()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _calls(mac).count("--force-reinstall --no-deps litellm") == 1


def test_frontend_uses_npm_ci_and_never_touches_the_lock_file(mac):
    """npm install schrieb auf dem Test-Mac package-lock.json um → nächstes git pull --ff-only scheiterte."""
    _launchd(mac)
    (mac["tmp"] / "frontend_rev.txt").write_text("fe-rev-2\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "npm ci" in calls and "npm install" not in calls


def test_each_line_once_when_launchd_already_writes_to_the_log(mac):
    """Über den Knopf: launchd leitet stdout schon in die Log-Datei → jede Zeile genau einmal (Befund 21.10. .186).
    Erkennung über die Kennung der Update-plist, nicht über `-ef` (meldet auf macOS „verschieden“)."""
    _launchd(mac)
    with mac["log"].open("a") as out:
        r = subprocess.run(["bash", str(UPDATE)], env={**_env(mac), "HH_UPDATE_VIA_LAUNCHD": "1"}, stdout=out,
                           stderr=subprocess.STDOUT, text=True, timeout=60)
    assert r.returncode == 0, mac["log"].read_text()
    log = mac["log"].read_text()
    for line in ("Update gestartet", "Python-Pakete aktualisieren", "Update abgeschlossen"):
        assert log.count(line) == 1, (line, log)


def test_each_line_in_log_and_on_screen_when_run_in_terminal(mac):
    """Im Terminal: Zeile in der Datei UND auf dem Bildschirm."""
    _launchd(mac)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert mac["log"].read_text().count("Update abgeschlossen") == 1
    assert "Update abgeschlossen" in r.stdout


def test_update_plist_sets_the_marker_and_paths(mac, tmp_path):
    """55-launchd-triggers.sh: Update-plist setzt HH_UPDATE_VIA_LAUNCHD=1 und leitet in die Log-Datei."""
    text = TRIGGERS.read_text()
    start = text.index("<key>Label</key>\n    <string>io.hydrahive.update</string>")
    block = text[start:text.index("</plist>", start)]
    assert "<key>HH_UPDATE_VIA_LAUNCHD</key>\n        <string>1</string>" in block
    assert block.count("/usr/local/var/log/hydrahive2-update.log") == 2       # stdout + stderr


def test_update_rewrites_trigger_plist_without_marker(mac):
    """Alte Update-plist ohne Kennung → update-mac.sh schreibt die Trigger neu (55-launchd-triggers.sh)."""
    _launchd(mac)
    old = mac["tmp"] / "io.hydrahive.update.plist"
    old.write_text("<plist><dict><key>Label</key><string>io.hydrahive.update</string></dict></plist>")
    (mac["bin"] / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{mac["calls"]}"\n'
                                     '[ "$1" = "-H" ] && shift; [ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    (mac["tmp"] / "triggers.sh").write_text(f'#!/bin/bash\necho "triggers neu" >> "{mac["calls"]}"\n')
    r = subprocess.run(["bash", str(UPDATE)], env={**_env(mac), "HH_UPDATE_PLIST": str(old),
                                                   "HH_TRIGGERS_SCRIPT": str(mac["tmp"] / "triggers.sh")},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "triggers neu" in _calls(mac)
    assert "Update-Auslöser neu einrichten" in mac["log"].read_text()


def test_update_keeps_trigger_plist_with_marker(mac):
    _launchd(mac)
    cur = mac["tmp"] / "io.hydrahive.update.plist"
    cur.write_text("<key>HH_UPDATE_VIA_LAUNCHD</key><string>1</string>")
    (mac["tmp"] / "triggers.sh").write_text(f'#!/bin/bash\necho "triggers neu" >> "{mac["calls"]}"\n')
    r = subprocess.run(["bash", str(UPDATE)], env={**_env(mac), "HH_UPDATE_PLIST": str(cur),
                                                   "HH_TRIGGERS_SCRIPT": str(mac["tmp"] / "triggers.sh")},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "triggers neu" not in _calls(mac)


def test_npm_found_under_sudo_with_secure_path(mac, tmp_path):
    """Befund 21.10.2026 (Test-Mac): update-mac.sh läuft als root, `sudo -u <nutzer> npm` → „sudo: npm: command not
    found“ (sudo setzt secure_path ohne Homebrew). Jedes Mac-Update mit Frontend-Änderung brach so ab."""
    brew_bin = tmp_path / "homebrew" / "bin"
    brew_bin.mkdir(parents=True)
    (mac["bin"] / "npm").rename(brew_bin / "npm")
    # sudo wie macOS: eigener PATH ohne Homebrew
    (mac["bin"] / "sudo").write_text(f'#!/bin/bash\n[ "$1" = "-H" ] && shift; [ "$1" = "-u" ] && shift 2\nPATH="{mac["bin"]}:/usr/bin:/bin" exec "$@"\n')
    _launchd(mac)
    (mac["tmp"] / "frontend_rev.txt").write_text("fe-rev-2\n")
    # Wie der echte Update-Dienst (launchd, root): PATH OHNE Homebrew; brew liegt nur unter seinem vollen Pfad.
    (brew_bin / "brew").write_text(f'#!/bin/bash\ncase "$1" in --prefix) echo "{brew_bin.parent}";; esac\n')
    (brew_bin / "brew").chmod(0o755)
    env = {**_env(mac), "PATH": f"{mac['bin']}:/usr/bin:/bin", "HH_BREW": str(brew_bin / "brew")}
    r = subprocess.run(["bash", str(UPDATE)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr + mac["log"].read_text()
    calls = _calls(mac)
    assert "npm ci" in calls and "npm run build" in calls


# --- Knopf tot nach Update (Befund Kollege 22.10.2026) ------------------------------------------------

def test_triggers_script_never_unloads_the_running_update_daemon(tmp_path):
    """Läuft 55-launchd-triggers.sh INNERHALB des Update-Dienstes (Knopf im Cockpit), darf es io.hydrahive.update nicht
    entladen: launchd beendet damit das laufende Update samt Skript, das `load` danach kommt nie → Dienst weg, jeder
    weitere Knopfdruck landet ins Leere (Befund: `launchctl list` ohne io.hydrahive.update, .update_request liegt)."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    calls.write_text("")
    for name in ("sudo",):
        (bin_ / name).write_text('#!/bin/bash\nexec "$@"\n')
    (bin_ / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{calls}"\n')
    (bin_ / "tee").write_text('#!/bin/bash\ncat > /dev/null\n')
    (bin_ / "chmod").write_text("#!/bin/bash\nexit 0\n")
    (bin_ / "touch").write_text("#!/bin/bash\nexit 0\n")
    (bin_ / "mkdir").write_text("#!/bin/bash\nexit 0\n")      # /usr/local/var/log gibt es im Test nicht
    for f in bin_.iterdir():
        f.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_}:/usr/bin:/bin", "HH_REPO_DIR": "/opt/hydrahive2",
           "HH_DATA_DIR": "/usr/local/var/hydrahive2", "HH_USER": "tester", "HH_UPDATE_VIA_LAUNCHD": "1"}
    r = subprocess.run(["bash", str(TRIGGERS)], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = calls.read_text().splitlines()
    assert not any(l.startswith("launchctl unload") and "io.hydrahive.update.plist" in l for l in lines), lines
    assert not any(l.startswith("launchctl bootout") and "io.hydrahive.update" in l for l in lines), lines
    # Restart-Auslöser darf wie bisher neu geladen werden
    assert any("launchctl load" in l and "io.hydrahive.restart.plist" in l for l in lines), lines


def test_triggers_script_detects_old_update_daemon_without_marker(tmp_path):
    """Ältere Update-plist (Mai) setzt HH_UPDATE_VIA_LAUNCHD NICHT – genau die wird ersetzt. launchd setzt aber immer
    XPC_SERVICE_NAME. Live-Befund Intel-Mac 22.10.2026: ohne diese Erkennung entlud sich der Dienst trotzdem."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    calls.write_text("")
    (bin_ / "sudo").write_text('#!/bin/bash\nexec "$@"\n')
    (bin_ / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{calls}"\n')
    (bin_ / "tee").write_text('#!/bin/bash\ncat > /dev/null\n')
    for name in ("chmod", "touch", "mkdir"):
        (bin_ / name).write_text("#!/bin/bash\nexit 0\n")
    for f in bin_.iterdir():
        f.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ("HH_UPDATE_VIA_LAUNCHD", "XPC_SERVICE_NAME")}
    env.update({"PATH": f"{bin_}:/usr/bin:/bin", "HH_REPO_DIR": "/opt/hydrahive2",
                "HH_DATA_DIR": "/usr/local/var/hydrahive2", "HH_USER": "tester",
                "XPC_SERVICE_NAME": "io.hydrahive.update"})
    r = subprocess.run(["bash", str(TRIGGERS)], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = calls.read_text().splitlines()
    assert not any("io.hydrahive.update.plist" in l for l in lines), lines


def test_triggers_script_reloads_update_daemon_when_run_from_terminal(tmp_path):
    """Im Terminal (Installer, Update von Hand) läuft das Skript NICHT im Update-Dienst → dort wie bisher neu laden."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    calls.write_text("")
    (bin_ / "sudo").write_text('#!/bin/bash\nexec "$@"\n')
    (bin_ / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{calls}"\n')
    for name in ("tee",):
        (bin_ / name).write_text('#!/bin/bash\ncat > /dev/null\n')
    for name in ("chmod", "touch", "mkdir"):
        (bin_ / name).write_text("#!/bin/bash\nexit 0\n")
    for f in bin_.iterdir():
        f.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ("HH_UPDATE_VIA_LAUNCHD", "XPC_SERVICE_NAME")}
    env.update({"PATH": f"{bin_}:/usr/bin:/bin", "HH_REPO_DIR": "/opt/hydrahive2",
                "HH_DATA_DIR": "/usr/local/var/hydrahive2", "HH_USER": "tester"})
    r = subprocess.run(["bash", str(TRIGGERS)], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = calls.read_text().splitlines()
    assert any(l.startswith("launchctl load") and "io.hydrahive.update.plist" in l for l in lines), lines


def test_update_reloads_missing_update_daemon(mac):
    """Selbstheilung: Ist der Update-Dienst nicht geladen (Folge des alten Fehlers), lädt das nächste Update (z. B. im
    Terminal) ihn wieder."""
    _launchd(mac)
    plist = mac["tmp"] / "io.hydrahive.update.plist"
    plist.write_text("<key>HH_UPDATE_VIA_LAUNCHD</key><string>1</string>")
    r = subprocess.run(["bash", str(UPDATE)], env={**_env(mac), "HH_UPDATE_PLIST": str(plist)},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"launchctl load {plist}" in _calls(mac)          # list kennt nur io.hydrahive.backend → fehlt


def test_update_leaves_loaded_update_daemon_alone(mac):
    _launchd(mac)
    plist = mac["tmp"] / "io.hydrahive.update.plist"
    plist.write_text("<key>HH_UPDATE_VIA_LAUNCHD</key><string>1</string>")
    (mac["bin"] / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{mac["calls"]}"\n'
                                          'case "$1" in list) echo "123 0 io.hydrahive.backend"; '
                                          'echo "- 0 io.hydrahive.update";; esac\n')
    r = subprocess.run(["bash", str(UPDATE)], env={**_env(mac), "HH_UPDATE_PLIST": str(plist)},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"launchctl load {plist}" not in _calls(mac)


# --- Schlusszeile für das Update-Fenster (HH-UPDATE-ENDE) -------------------------------------------------------

def _last_line(m: dict) -> str:
    return [l for l in m["log"].read_text().splitlines() if l.strip()][-1]


def test_update_ends_with_ok_marker(mac):
    _launchd(mac)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _last_line(mac) == "HH-UPDATE-ENDE: ok"


def test_update_abort_writes_error_marker_with_reason(mac):
    """Abbruch (hier: git pull scheitert) → Fenster soll sofort „fehlgeschlagen“ mit Grund zeigen statt 10 min warten."""
    _launchd(mac)
    (mac["bin"] / "git").write_text('#!/bin/bash\ncase "$*" in *pull*) echo "fatal: kaputt" >&2; exit 1;; esac\nexit 0\n')
    r = _update(mac)
    assert r.returncode != 0
    assert _last_line(mac) == "HH-UPDATE-ENDE: fehler git pull fehlgeschlagen"


def test_update_unexpected_error_still_writes_marker(mac):
    """Auch ein unerwarteter Abbruch (set -e, ohne eigene Meldung) hinterlässt eine Schlusszeile."""
    _launchd(mac)
    (mac["bin"] / "launchctl").write_text('#!/bin/bash\ncase "$1" in list) echo "123 0 io.hydrahive.backend";; '
                                          'load) exit 5;; esac\nexit 0\n')
    r = _update(mac)
    assert r.returncode != 0
    assert _last_line(mac).startswith("HH-UPDATE-ENDE: fehler")


def test_update_marker_only_once(mac):
    _launchd(mac)
    _update(mac)
    assert mac["log"].read_text().count("HH-UPDATE-ENDE:") == 1


# --- Umzug auf das Dienst-Konto (docs/plans/mac-service-user.md, Etappe 3) -----------------------------------------

def _with_migrate(mac: dict, body: str = "exit 0") -> None:
    p = mac["repo"] / "installer" / "lib" / "mac-migrate-service-user.sh"
    p.write_text(f'#!/bin/bash\necho "migrate user=$HH_USER" >> "{mac["calls"]}"\n{body}\n')
    p.chmod(0o755)


def test_update_runs_move_to_service_account_once(mac):
    _with_migrate(mac)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "migrate user=tester" in calls
    # nach pip/Frontend, vor dem Neustart des Backends (der Umzug startet die Dienste selbst neu)
    assert calls.index("pip install") < calls.index("migrate user=")


def test_update_skips_move_when_already_service_account(mac):
    _with_migrate(mac)
    (mac["cfg"] / "install.conf").write_text("HH_SERVICE_USER=_hydrahive\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "migrate" not in _calls(mac)


def test_update_after_move_uses_service_account(mac):
    """Nach dem Umzug gehört das Repo _hydrahive – git/pip laufen dann als Konto (Merker in install.conf)."""
    (mac["cfg"] / "install.conf").write_text("HH_SERVICE_USER=_hydrahive\n")
    (mac["bin"] / "chown").write_text("#!/bin/bash\nexit 0\n")     # Konto gibt es auf dem Test-Rechner nicht
    (mac["bin"] / "chown").chmod(0o755)
    (mac["bin"] / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{mac["calls"]}"\n[ "$1" = "-H" ] && shift; [ "$1" = "-u" ] && shift 2\n'
                                     'exec "$@"\n')
    env = {k: v for k, v in _env(mac).items() if k != "HH_USER"}
    r = subprocess.run(["bash", str(UPDATE)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sudo -H -u _hydrahive git pull" in _calls(mac)


def test_update_move_failure_does_not_fail_update(mac):
    """Neuer Code ist eingespielt – ein gescheiterter Umzug wird gemeldet, das Update gilt trotzdem."""
    _with_migrate(mac, 'echo "kaputt" >&2; exit 1')
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Dienst-Konto" in mac["log"].read_text()
    assert "HH-UPDATE-ENDE: ok" in mac["log"].read_text()


def test_update_successful_move_skips_old_restart(mac):
    """Der Umzug hat die Dienste schon als Konto gestartet – kein Neustart mit der alten plist danach."""
    _with_migrate(mac, f'echo "HH_SERVICE_USER=_hydrahive" >> "{mac["cfg"]}/install.conf"')
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    after = _calls(mac).split("migrate user=")[1]
    assert "launchctl load" not in after


def test_update_runs_tools_with_service_account_home(mac):
    """Befund 23.10.2026 (.186, nach dem Umzug auf _hydrahive): update-mac.sh rief npm/pip per `sudo -u _hydrahive`
    mit dem HOME des Mac-Besitzers auf → „npm error EACCES … /Users/admin/.npm“, jedes Update mit neuem Frontend
    brach ab. git, pip und npm laufen jetzt mit -H (HOME des Kontos)."""
    (mac["bin"] / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{mac["calls"]}"\n'
                                     'while [ $# -gt 0 ]; do case "$1" in -u) shift 2;; -H) shift;; *) break;; esac; done\n'
                                     'exec "$@"\n')
    _launchd(mac)
    (mac["tmp"] / "frontend_rev.txt").write_text("fe-rev-2\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    sudo_u = [c for c in _calls(mac).splitlines() if c.startswith("sudo -u") or c.startswith("sudo -H -u")]
    tools = [c for c in sudo_u if any(w in c for w in (" git ", " npm ", "/pip "))]
    assert tools, _calls(mac)
    assert all(c.startswith("sudo -H -u tester ") for c in tools), tools
