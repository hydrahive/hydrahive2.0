"""Mac-Dateifreigabe (docs/plans/mac-file-sharing.md §2.1, §2.2): Zusatz-Modul 47-filesharing.sh und der root-Daemon
lib/mac-shares-ctl.sh. Nachgebauter Mac: dscl/sharing/launchctl/chmod/pwpolicy zeichnen nur auf.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SETUP = INSTALLER / "modules-mac" / "47-filesharing.sh"
CTL = INSTALLER / "lib" / "mac-shares-ctl.sh"
PID = "0123456789abcdef01234567"


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    b = tmp_path / "bin"
    calls = tmp_path / "calls.log"
    calls.write_text("")
    log = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    users = tmp_path / "users"
    users.mkdir()
    # dscl: -read /Users/x → 0 wenn angelegt; -create /Users/x → anlegen; -list /Users UniqueID → belegte IDs
    _exe(b / "dscl", log + f'''
case "$2" in
  -read) [ -f "{users}/$(basename "$3")" ] && {{ echo "UniqueID: 499"; exit 0; }}; exit 56 ;;
  -create) [ "$#" -eq 3 ] && touch "{users}/$(basename "$3")"; exit 0 ;;
  -list) echo "root 0"; echo "_hydrahive 498"; exit 0 ;;
esac
exit 0
''')
    for name in ("dseditgroup", "pwpolicy", "launchctl", "sharing", "chown", "defaults", "createhomedir"):
        _exe(b / name, log + ("[ -f \"$(dirname \"$0\")/../sharing-fails\" ] && exit 1\n" if name == "sharing" else "")
             + "exit 0\n")
    _exe(b / "chmod", log + 'case "$1" in +a|-a|=a|-N) exit 0;; esac\nexec /bin/chmod "$@"\n')
    _exe(b / "sudo", log + 'exec "$@"\n')
    _exe(b / "id", 'if [ "$1" = "-u" ] && [ "$#" -eq 1 ]; then echo 0; else exec /usr/bin/id "$@"; fi\n')
    data = tmp_path / "data"
    (data / "workspaces" / "projects" / PID).mkdir(parents=True)
    conf = tmp_path / "etc"
    conf.mkdir()
    return {"tmp": tmp_path, "bin": b, "calls": calls, "data": data, "conf": conf, "users": users}


def _env(m: dict, **extra) -> dict:
    return {**os.environ, "PATH": f"{m['bin']}:/usr/bin:/bin", "HH_USER": "_hydrahive", "HH_DATA_DIR": str(m["data"]),
            "HH_CONFIG_DIR": str(m["conf"]), "HH_SHARES_PLIST": str(m["tmp"] / "io.hydrahive.shares.plist"),
            "HH_REPO_DIR": str(INSTALLER.parent), "HH_LOG_DIR": str(m["tmp"] / "log"), **extra}


def _setup(m: dict, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SETUP)], env=_env(m, **extra), capture_output=True, text=True, timeout=60)


def _ctl(m: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(CTL)], env=_env(m), capture_output=True, text=True, timeout=60)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


# --- 47-filesharing.sh ---------------------------------------------------------------------------------------------

def test_setup_legt_konto_ohne_shell_an_und_schaltet_smb_ein(mac) -> None:
    r = _setup(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    c = _calls(mac)
    assert any(x.startswith("dscl . -create /Users/hhshare UserShell /usr/bin/false") for x in c), c
    assert any("dscl . -create /Users/hhshare IsHidden 1" in x for x in c)
    assert not any("staff" in x for x in c), "nicht in staff (keine normale Anmeldung)"
    assert any(x.startswith("launchctl enable system/com.apple.smbd") for x in c)
    pw = mac["conf"] / "samba.password"
    assert pw.exists() and oct(pw.stat().st_mode)[-3:] == "600" and len(pw.read_text().strip()) >= 20
    assert (mac["conf"] / "mac-shares.d").is_dir()
    assert (mac["tmp"] / "io.hydrahive.shares.plist").exists()


def test_setup_passwort_nie_auf_der_kommandozeile(mac) -> None:
    _setup(mac)
    pw = (mac["conf"] / "samba.password").read_text().strip()
    assert not any(pw in x for x in _calls(mac)), "Passwort darf nicht in Prozessliste/Aufrufen stehen"


def test_setup_nur_durchgehen_auf_dem_weg_kein_chown_r(mac) -> None:
    _setup(mac)
    c = _calls(mac)
    acl = [x for x in c if x.startswith("chmod +a")]
    assert any("user:hhshare allow search" in x and x.endswith(str(mac["data"])) for x in acl), acl
    assert any("user:hhshare allow search" in x and x.endswith(str(mac["data"] / "workspaces" / "projects"))
               for x in acl)
    assert not any("chown -R" in x for x in c)
    assert not any("list,add_file" in x and x.endswith(str(mac["data"])) for x in acl), "kein Lesen des Daten-Ordners"


def test_setup_zweimal_aendert_nichts(mac) -> None:
    _setup(mac)
    pw1 = (mac["conf"] / "samba.password").read_text()
    mac["calls"].write_text("")
    r = _setup(mac)
    assert r.returncode == 0
    assert (mac["conf"] / "samba.password").read_text() == pw1, "Passwort bleibt"
    assert not any(x.startswith("dscl . -create /Users/hhshare UniqueID") for x in _calls(mac)), "Konto nicht neu"


# --- mac-shares-ctl.sh ---------------------------------------------------------------------------------------------

def _want(m: dict, pid: str, *lines: str) -> None:
    d = m["conf"] / "mac-shares.d"
    d.mkdir(exist_ok=True)
    (d / f"{pid}.want").write_text("\n".join(lines) + "\n")


def _state(m: dict, pid: str) -> str:
    p = m["conf"] / "mac-shares.d" / f"{pid}.state"
    return p.read_text().strip() if p.exists() else ""


def test_ctl_freigeben(mac) -> None:
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "Mein_Projekt", str(path))
    r = _ctl(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    c = _calls(mac)
    assert any(x == f"sharing -a {path} -S Mein_Projekt -s 001 -g 000" for x in c), c
    assert any(x.startswith("chmod +a user:hhshare allow ") and "file_inherit,directory_inherit" in x
               and x.endswith(str(path)) for x in c)
    assert _state(mac, PID) == "on"


def test_ctl_abschalten(mac) -> None:
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "Mein_Projekt", str(path))
    _ctl(mac)
    _want(mac, PID, "off", "", str(path))
    mac["calls"].write_text("")
    r = _ctl(mac)
    assert r.returncode == 0
    assert any(x == "sharing -r Mein_Projekt" for x in _calls(mac)), _calls(mac)
    assert _state(mac, PID) == "off"


@pytest.mark.parametrize("pid, name, path_kind", [
    ("..", "x", "ok"), ("a b", "x", "ok"), (PID, "a b", "ok"), (PID, "x;id", "ok"), (PID, "", "ok"),
    (PID, "x", "other"), (PID, "x", "dotdot"), (PID, "x", "master"),
])
def test_ctl_lehnt_boese_anfragen_ab(mac, pid, name, path_kind) -> None:
    base = mac["data"] / "workspaces"
    path = {"ok": base / "projects" / pid, "other": mac["tmp"], "dotdot": base / "projects" / PID / ".." / "..",
            "master": base / "master"}[path_kind]
    d = mac["conf"] / "mac-shares.d"
    d.mkdir(exist_ok=True)
    fname = f"{pid}.want" if "/" not in pid else "x.want"
    (d / fname).write_text(f"on\n{name}\n{path}\n")
    _ctl(mac)
    assert not any(x.startswith("sharing -a") or x.startswith("chmod +a") for x in _calls(mac)), _calls(mac)


def test_ctl_symlink_wird_abgelehnt(mac) -> None:
    link = mac["data"] / "workspaces" / "projects" / "linkprojekt"
    link.symlink_to(mac["tmp"])
    _want(mac, "linkprojekt", "on", "x", str(link))
    _ctl(mac)
    assert not any(x.startswith("sharing -a") for x in _calls(mac))
    assert _state(mac, "linkprojekt").startswith("error")


def test_ctl_fehler_von_sharing_wird_gemeldet(mac) -> None:
    (mac["tmp"] / "sharing-fails").write_text("")
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    assert _state(mac, PID).startswith("error")


def test_ctl_ohne_anfragen_tut_nichts(mac) -> None:
    r = _ctl(mac)
    assert r.returncode == 0 and _calls(mac) == []


# --- jede Schutzprüfung einzeln (Mutantenprobe: keine Prüfung darf sich auf eine andere verlassen) -----------------

def test_ctl_fremder_ordner_mit_gueltiger_id(mac) -> None:
    """Gültige ID, gültiger Name, aber der Pfad zeigt woanders hin (nicht der Projektordner der ID)."""
    other = mac["data"] / "workspaces" / "projects" / "anderes"
    other.mkdir()
    _want(mac, PID, "on", "P", str(other))
    _ctl(mac)
    assert not any(x.startswith("sharing -a") or x.startswith("chmod +a") for x in _calls(mac)), _calls(mac)
    assert _state(mac, PID) == "error:path"


def test_ctl_symlink_mit_passendem_pfad(mac) -> None:
    """Der Pfad passt Zeichen für Zeichen, ist aber ein Symlink auf etwas anderes."""
    target = mac["tmp"] / "geheim"
    target.mkdir()
    link = mac["data"] / "workspaces" / "projects" / "projlink"
    link.symlink_to(target)
    _want(mac, "projlink", "on", "P", str(link))
    _ctl(mac)
    assert not any(x.startswith("sharing -a") or x.startswith("chmod +a") for x in _calls(mac)), _calls(mac)
    assert _state(mac, "projlink") == "error:path"


def test_ctl_unterordner_symlink_im_weg(mac) -> None:
    """projects selbst ist ein Symlink-Ziel-Trick: Ordner liegt per Umweg außerhalb → realpath-Prüfung greift."""
    outside = mac["tmp"] / "draussen" / "pX"
    outside.mkdir(parents=True)
    hop = mac["data"] / "workspaces" / "projects" / "hop"
    hop.symlink_to(mac["tmp"] / "draussen")
    _want(mac, "pX", "on", "P", str(mac["data"] / "workspaces" / "projects" / "pX"))
    (mac["data"] / "workspaces" / "projects" / "pX").symlink_to(outside)
    _ctl(mac)
    assert not any(x.startswith("sharing -a") for x in _calls(mac))


def test_ctl_ungueltige_id_im_dateinamen(mac) -> None:
    d = mac["conf"] / "mac-shares.d"
    d.mkdir(exist_ok=True)
    bad = "a b"
    (mac["data"] / "workspaces" / "projects" / bad).mkdir()
    (d / f"{bad}.want").write_text(f"on\nP\n{mac['data'] / 'workspaces' / 'projects' / bad}\n")
    _ctl(mac)
    assert not any(x.startswith("sharing -a") or x.startswith("chmod +a") for x in _calls(mac)), _calls(mac)
    assert not (d / f"{bad}.want").exists(), "verworfene Anfrage wird entfernt"


def test_ctl_pfad_text_fremd_obwohl_echter_ordner(mac) -> None:
    """Nur die Text-Prüfung fängt das: echter Ordner (kein Symlink) im Projektbereich, aber nicht der der ID."""
    other = mac["data"] / "workspaces" / "projects" / "zweites"
    other.mkdir()
    _want(mac, PID, "on", "P", str(mac["data"] / "workspaces" / "projects" / "." / "zweites"))
    _ctl(mac)
    assert not any(x.startswith("sharing -a") for x in _calls(mac)), _calls(mac)


def test_ctl_symlink_im_projektbereich_auf_projektbereich(mac) -> None:
    """Nur die Symlink-Prüfung fängt das: <id> ist ein Symlink auf einen anderen Projektordner (realpath bleibt im
    Projektbereich, Text passt)."""
    other = mac["data"] / "workspaces" / "projects" / "echtes"
    other.mkdir()
    link = mac["data"] / "workspaces" / "projects" / "verweis"
    link.symlink_to(other)
    _want(mac, "verweis", "on", "P", str(link))
    _ctl(mac)
    assert not any(x.startswith("sharing -a") for x in _calls(mac)), _calls(mac)
    assert _state(mac, "verweis") == "error:path"


def test_ctl_projekte_ordner_selbst_umgebogen(mac, tmp_path) -> None:
    """Nur die realpath-Prüfung fängt das: der Ordner der ID ist echt (kein Symlink), aber ein Elternteil des Wegs
    zeigt woanders hin – hier: HH_DATA_DIR/workspaces/projects ist ein Symlink nach draußen."""
    data2 = tmp_path / "data2"
    (data2 / "workspaces").mkdir(parents=True)
    outside = tmp_path / "draussen2"
    (outside / PID).mkdir(parents=True)
    (data2 / "workspaces" / "projects").symlink_to(outside)
    d = mac["conf"] / "mac-shares.d"
    d.mkdir(exist_ok=True)
    (d / f"{PID}.want").write_text(f"on\nP\n{data2 / 'workspaces' / 'projects' / PID}\n")
    r = subprocess.run(["bash", str(CTL)], env=_env(mac, HH_DATA_DIR=str(data2)), capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0
    assert not any(x.startswith("sharing -a") for x in _calls(mac)), _calls(mac)
