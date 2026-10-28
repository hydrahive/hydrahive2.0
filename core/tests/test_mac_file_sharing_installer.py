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
    home = tmp_path / "home"
    home.mkdir()
    _exe(b / "dscl", log + f'''
case "$2" in
  -read) [ "${{4:-}}" = "NFSHomeDirectory" ] && {{ echo "NFSHomeDirectory: {home}"; exit 0; }}
         [ -f "{users}/$(basename "$3")" ] && {{ echo "UniqueID: 499"; exit 0; }}; exit 56 ;;
  -create) [ "$#" -eq 3 ] && touch "{users}/$(basename "$3")"; exit 0 ;;
  -list) echo "root 0"; echo "_hydrahive 498"; exit 0 ;;
esac
exit 0
''')
    for name in ("dseditgroup", "pwpolicy", "launchctl", "sharing", "chown", "defaults", "createhomedir"):
        _exe(b / name, log + ("[ -f \"$(dirname \"$0\")/../sharing-fails\" ] && exit 1\n"
                              "[ \"$1\" = -l ] && cat \"$(dirname \"$0\")/../sharing-list.txt\" 2>/dev/null\n"
                              if name == "sharing" else "")
             + "exit 0\n")
    _exe(b / "chmod", log + '[ "$1" = "-h" ] && shift\ncase "$1" in +a|-a|=a|-N) exit 0;; esac\nexec /bin/chmod "$@"\n')
    _exe(b / "sudo", log + 'while [ "${1:-}" = "-n" ] || [ "${1:-}" = "-u" ]; do [ "$1" = "-u" ] && shift; shift; done\n'
                          'exec "$@"\n')
    _exe(b / "id", 'if [ "$1" = "-u" ] && [ "$#" -eq 1 ]; then echo 0; else exec /usr/bin/id "$@"; fi\n')
    data = tmp_path / "data"
    (data / "workspaces" / "projects" / PID).mkdir(parents=True)
    conf = tmp_path / "etc"
    conf.mkdir()
    return {"tmp": tmp_path, "bin": b, "calls": calls, "data": data, "conf": conf, "users": users, "home": home}


def _env(m: dict, **extra) -> dict:
    return {**os.environ, "PATH": f"{m['bin']}:/usr/bin:/bin", "HH_USER": "_hydrahive", "HH_DATA_DIR": str(m["data"]),
            "HH_CONFIG_DIR": str(m["conf"]), "HH_SHARES_PLIST": str(m["tmp"] / "io.hydrahive.shares.plist"),
            "HH_REPO_DIR": str(INSTALLER.parent), "HH_LOG_DIR": str(m["tmp"] / "log"), "HH_MAC_OWNER": "alex", **extra}


def _setup(m: dict, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SETUP)], env=_env(m, **extra), capture_output=True, text=True, timeout=60)


def _ctl(m: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(CTL)], env=_env(m), capture_output=True, text=True, timeout=60)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


def test_attrappe_dscl_liest_die_eingabe_wie_das_echte_programm(mac) -> None:
    """set_pw schreibt per Pipe in `dscl .`. Liest die Attrappe nicht, bekommt printf unter Last SIGPIPE (141) und
    pipefail+set -e bricht 47-filesharing.sh zufällig ab (Testreihe mit -n 24). Der Schreiber wartet, bis eine nicht
    lesende Attrappe längst beendet wäre – so wird das Rennen zur Gewissheit."""
    sh = f'set -o pipefail; {{ sleep 0.5; printf "passwd /Users/x y\\n"; }} | "{mac["bin"] / "dscl"}" .'
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"rc {r.returncode}: dscl-Attrappe muss stdin lesen"


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


def test_setup_schaltet_smb_passwort_hash_vor_dem_passwort_ein(mac) -> None:
    """Echter Mac (macOS 27, 26.10.): ohne SMB-NT-Hash legt dscl passwd nur PBKDF2/SRP an → NT_STATUS_LOGON_FAILURE.
    Der Hash entsteht erst beim Passwort-Setzen, also muss danach noch einmal gesetzt werden. pwpolicy stürzt aber ab
    (rc 139), wenn das Konto noch gar kein Passwort hat → Reihenfolge passwd, pwpolicy, passwd."""
    _setup(mac)
    c = _calls(mac)
    hashes = [i for i, x in enumerate(c) if x.startswith("pwpolicy -u hhshare sethashtypes SMB-NT on")]
    passwd = [i for i, x in enumerate(c) if x == "dscl ."]
    assert hashes, c
    assert passwd and passwd[0] < hashes[0], "erst ein Passwort, sonst stürzt pwpolicy ab"
    assert hashes[0] < passwd[-1], "nach SMB-NT das Passwort noch einmal setzen, damit der Hash entsteht"


def test_setup_laedt_smbd_wirklich(mac) -> None:
    """Echter Mac: smbd ist nicht geladen (Disabled=true) → kickstart findet den Dienst nicht. load -w lädt ihn."""
    _setup(mac)
    assert any(x == "launchctl load -w /System/Library/LaunchDaemons/com.apple.smbd.plist" for x in _calls(mac)), \
        _calls(mac)


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
    assert any(x == f"sharing -a {path} -S Mein_Projekt -n {PID} -s 001 -g 000" for x in c), c
    assert any(x.startswith("chmod +a user:hhshare allow ") and "file_inherit,directory_inherit" in x
               and x.endswith(str(path)) for x in c)
    assert _state(mac, PID) == "on"


def test_ctl_dienst_konto_bekommt_vererbte_rechte(mac) -> None:
    """Echter Mac 26.10.: was der Kunde per SMB anlegt, gehört hhshare (0600) – der Agent (_hydrahive) kam nicht mehr
    heran. Darum erbt jede neue Datei auch einen Eintrag für das Dienst-Konto."""
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    assert any(x.startswith("chmod +a user:_hydrahive allow ") and "file_inherit,directory_inherit" in x
               and x.endswith(str(path)) for x in _calls(mac)), _calls(mac)


def test_ctl_vorhandene_dateien_als_dienst_konto_ohne_symlinks(mac) -> None:
    """Vorhandene Dateien/Ordner bekommen die Rechte nachträglich – aber nie über einen Symlink (chmod -R folgte am
    echten Mac einem Link nach /tmp und setzte dort die Freigabe-Rechte!) und nur mit den Rechten des Dienst-Kontos,
    damit selbst ein Wettlauf nichts außerhalb dessen erreicht, was dem Dienst-Konto ohnehin gehört."""
    path = mac["data"] / "workspaces" / "projects" / PID
    (path / "unter").mkdir()
    (path / "unter" / "a.txt").write_text("x")
    outside = mac["tmp"] / "draussen"
    outside.mkdir()
    (path / "link").symlink_to(outside)
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    c = _calls(mac)
    plus = [x for x in c if x.startswith("chmod") and "+a" in x]
    assert any(str(path / "unter" / "a.txt") in x.split() and "user:hhshare" in x for x in plus), plus
    assert any(str(path / "unter") in x.split() and "user:_hydrahive" in x for x in plus), plus
    assert not any(str(outside) in x or str(path / "link") in x.split() for x in plus), "nie über/auf einen Symlink"
    assert not any(x.startswith("chmod -R") for x in c), "kein chmod -R (folgt Symlinks)"
    assert any(x.startswith("sudo -n -u _hydrahive find ") for x in c), c


@pytest.mark.parametrize("user", [None, "root", "a b", "-x"])
def test_ctl_ohne_gueltiges_dienst_konto_kein_freigeben(mac, user) -> None:
    """Ohne Dienst-Konto oder mit root würde find/chmod mit vollen Rechten laufen – dann lieber gar nicht."""
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "P", str(path))
    env = {k: v for k, v in _env(mac).items() if k != "HH_USER"}
    if user is not None:
        env["HH_USER"] = user
    subprocess.run(["bash", str(CTL)], env=env, capture_output=True, text=True, timeout=60)
    assert not any(x.startswith("sharing -a") or "find" in x for x in _calls(mac)), _calls(mac)
    assert _state(mac, PID) == "error:user"


def test_setup_gibt_dem_dienst_das_dienst_konto_mit(mac) -> None:
    _setup(mac)
    plist = (mac["tmp"] / "io.hydrahive.shares.plist").read_text()
    assert "<key>HH_USER</key>" in plist and "<string>_hydrahive</string>" in plist


def _sharing_list(m: dict, *records: tuple[str, str]) -> None:
    """Ausgabe von `sharing -l` wie auf macOS 27 (Datensatz-Name, Pfad, smb-Block)."""
    out = "\n\t\t\tList of Share Points\n"
    for name, path in records:
        out += f"name:\t\t{name}\npath:\t\t{path}\n\tsmb:\t{{\n    \t\tname:\tX\n    \t\tshared:\t1\n\t}}\n\n"
    (m["tmp"] / "sharing-list.txt").write_text(out)


def test_ctl_abschalten_entfernt_alle_datensaetze_des_projekts(mac) -> None:
    """Live am Mac (26.10.): `sharing -r` will den Datensatz-Namen (Ordnername), nicht den SMB-Namen – Ausschalten
    entfernte nichts, jedes Einschalten legte einen weiteren Datensatz (<id>-1, …) an. Jetzt: alle Datensätze, deren
    Pfad der Projektordner ist, entfernen – fremde Freigaben bleiben."""
    path = mac["data"] / "workspaces" / "projects" / PID
    _sharing_list(mac, (PID, str(path)), (f"{PID}-1", str(path)), ("Alex Mo’s Public Folder", "/Users/alex/Public"))
    _want(mac, PID, "off", "", str(path))
    r = _ctl(mac)
    assert r.returncode == 0
    c = _calls(mac)
    assert f"sharing -r {PID}" in c and f"sharing -r {PID}-1" in c, c
    assert not any("Public" in x and x.startswith("sharing -r") for x in c), c
    assert _state(mac, PID) == "off"


def test_ctl_einschalten_raeumt_alte_datensaetze_vorher_weg(mac) -> None:
    path = mac["data"] / "workspaces" / "projects" / PID
    _sharing_list(mac, (PID, str(path)), (f"{PID}-1", str(path)))
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    c = _calls(mac)
    add = c.index(f"sharing -a {path} -S P -n {PID} -s 001 -g 000")
    assert c.index(f"sharing -r {PID}") < add and c.index(f"sharing -r {PID}-1") < add, c


# --- Zugang für den Mac-Besitzer im Benutzerordner (Finder verbindet sich nicht mit dem eigenen Mac) --------------

def _link(m: dict, name: str) -> Path:
    return m["home"] / "HydraHive" / name


def test_ctl_besitzer_bekommt_projekt_im_benutzerordner(mac) -> None:
    """Live am Mac (26.10.): „Mit Server verbinden“ zum eigenen Mac scheitert (NetFS 65 bei jeder eigenen Adresse).
    Der Mac-Besitzer kommt deshalb direkt dran: Recht auf das Projekt + Eintrag ~/HydraHive/<Name>."""
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "test123", str(path))
    _ctl(mac)
    c = _calls(mac)
    assert any(x.startswith("chmod +a user:alex allow ") and "file_inherit,directory_inherit" in x
               and x.endswith(str(path)) for x in c), c
    link = _link(mac, "test123")
    assert link.is_symlink() and os.readlink(link) == str(path)
    assert any(x.startswith("sudo -n -u alex ln ") for x in c), "Eintrag als Besitzer anlegen, nicht als root"
    assert any(x.startswith("sudo -n -u alex mkdir ") for x in c)


def test_ctl_einschalten_hebt_sperre_auf_ausschalten_setzt_sie(mac) -> None:
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    c = _calls(mac)
    assert f"chmod -a user:alex deny list,search {path}" in c, c
    _want(mac, PID, "off", "", str(path))
    mac["calls"].write_text("")
    _ctl(mac)
    assert f"chmod +a user:alex deny list,search {path}" in _calls(mac), _calls(mac)


def test_ctl_besitzer_rechte_auch_auf_vorhandene_dateien(mac) -> None:
    path = mac["data"] / "workspaces" / "projects" / PID
    (path / "a.txt").write_text("x")
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    assert any(str(path / "a.txt") in x.split() and "user:alex" in x and "+a" in x for x in _calls(mac)), _calls(mac)


def test_ctl_abschalten_nimmt_besitzer_zugang_weg(mac) -> None:
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    _want(mac, PID, "off", "", str(path))
    mac["calls"].write_text("")
    _ctl(mac)
    c = _calls(mac)
    assert not _link(mac, "P").exists() and not _link(mac, "P").is_symlink()
    assert any(x.startswith("chmod -a user:alex allow ") and x.endswith(str(path)) for x in c), c


def test_ctl_umbenennen_entfernt_alten_eintrag(mac) -> None:
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "Alt", str(path))
    _ctl(mac)
    _want(mac, PID, "on", "Neu", str(path))
    _ctl(mac)
    assert not _link(mac, "Alt").is_symlink() and _link(mac, "Neu").is_symlink()


def test_ctl_fremder_eintrag_im_benutzerordner_bleibt(mac) -> None:
    """Was der Besitzer selbst unter ~/HydraHive angelegt hat (echter Ordner, Link woandershin), fassen wir nicht an."""
    path = mac["data"] / "workspaces" / "projects" / PID
    (mac["home"] / "HydraHive" / "P").mkdir(parents=True)
    (mac["home"] / "HydraHive" / "P" / "eigenes.txt").write_text("x")
    (mac["home"] / "HydraHive" / "Q").symlink_to(mac["tmp"])
    _want(mac, PID, "on", "P", str(path))
    _ctl(mac)
    assert (mac["home"] / "HydraHive" / "P" / "eigenes.txt").exists()
    assert not (mac["home"] / "HydraHive" / "P" / PID).exists(), "kein Link im fremden Ordner"
    assert _state(mac, PID) == "on", "SMB-Freigabe klappt trotzdem"
    _want(mac, PID, "off", "", str(path))
    _ctl(mac)
    assert (mac["home"] / "HydraHive" / "P" / "eigenes.txt").exists()
    assert (mac["home"] / "HydraHive" / "Q").is_symlink()


@pytest.mark.parametrize("owner", ["", "root", "a b", "_hydrahive"])
def test_ctl_ohne_gueltigen_besitzer_nur_smb(mac, owner) -> None:
    """Kein/ungültiger Besitzer (oder Besitzer = Dienst-Konto, alte Installationen): SMB geht, kein Besitzer-Zugang."""
    path = mac["data"] / "workspaces" / "projects" / PID
    _want(mac, PID, "on", "P", str(path))
    subprocess.run(["bash", str(CTL)], env=_env(mac, HH_MAC_OWNER=owner), capture_output=True, text=True,
                   timeout=60)
    c = _calls(mac)
    assert any(x.startswith("sharing -a") for x in c)
    assert not any(" ln " in f" {x} " for x in c), c
    if owner not in ("", "_hydrahive"):
        assert not any(f"user:{owner} " in x for x in c), c
    assert _state(mac, PID) == "on"


def test_setup_besitzer_darf_bis_zu_den_projekten_durchgehen(mac) -> None:
    _setup(mac)
    acl = [x for x in _calls(mac) if x.startswith("chmod +a user:alex")]
    for d in (mac["data"], mac["data"] / "workspaces", mac["data"] / "workspaces" / "projects"):
        assert any(x == f"chmod +a user:alex allow search {d}" for x in acl), acl
    assert not any(" allow " in x and "list" in x for x in acl), "nur durchgehen, nicht auflisten"


DENY_LATER = "user:alex deny list,search,read,file_inherit,directory_inherit,only_inherit,limit_inherit"


def test_setup_besitzer_sieht_nichts_ausser_dem_weg(mac) -> None:
    """Live am Mac (26.10.): Unter dem Daten-Ordner (750) ist fast alles 755/644 – mit „durchgehen“ hätte der Besitzer
    alle Projekte auflisten, master/ lesen und sessions.db öffnen können. Deshalb: auf dem Weg nicht auflisten, alles
    daneben sperren (auch was später entsteht), nicht freigegebene Projekte zu. (Am Mac in /tmp nachgeprüft.)"""
    d, ws = mac["data"], mac["data"] / "workspaces"
    (ws / "master").mkdir()
    (d / "sessions.db").write_text("x")
    (d / ".versteckt").mkdir()
    (ws / "projects" / "anderes").mkdir()
    _setup(mac)
    c = _calls(mac)
    for x in (d, ws, ws / "projects"):
        assert f"chmod +a user:alex deny list {x}" in c, c
        assert f"chmod +a {DENY_LATER} {x}" in c, c
    for x in (ws / "master", d / ".versteckt", ws / "projects" / "anderes", ws / "projects" / PID):
        assert f"chmod -h +a user:alex deny list,search {x}" in c, c
    assert f"chmod -h +a user:alex deny read {d / 'sessions.db'}" in c, c
    for x in (ws, ws / "projects"):
        assert not any(y.startswith("chmod") and "user:alex deny" in y and "search" in y and y.endswith(f"+a user:alex"
                       f" deny list,search {x}") for y in c), "Weg selbst bleibt begehbar"


def test_setup_ohne_besitzer_keine_sperren(mac) -> None:
    _setup(mac, HH_MAC_OWNER="")
    assert not any(" deny " in x for x in _calls(mac)), _calls(mac)


def test_setup_sperren_erst_entfernen_dann_setzen(mac) -> None:
    """macOS-`chmod -a` zieht die Rechte aus JEDEM passenden Eintrag ab (live am Mac: das zweite -a leerte die gerade
    gesetzte Sperre „deny list“, workspaces/ und projects/ blieben auflistbar). Pro Ordner: alle -a vor allen +a."""
    _setup(mac)
    c = _calls(mac)
    for d in (mac["data"], mac["data"] / "workspaces", mac["data"] / "workspaces" / "projects"):
        idx = [(i, x.split()[1]) for i, x in enumerate(c)
               if x.startswith("chmod ") and "user:alex deny" in x and x.endswith(f" {d}")]
        minus = [i for i, op in idx if op == "-a"]
        plus = [i for i, op in idx if op == "+a"]
        assert minus and plus and max(minus) < min(plus), (d, idx)


def test_setup_gibt_dem_dienst_den_besitzer_mit(mac) -> None:
    _setup(mac)
    plist = (mac["tmp"] / "io.hydrahive.shares.plist").read_text()
    assert "<key>HH_MAC_OWNER</key>" in plist and "<string>alex</string>" in plist


def test_setup_erkennt_besitzer_ueber_homebrew(mac) -> None:
    """Ohne Angabe: Besitzer von Homebrew = der Mensch am Mac (wie überall im Mac-Installer, lib/mac-roles.sh)."""
    brew = mac["tmp"] / "brew"
    brew.write_text("")
    brew.chmod(0o755)
    env = {k: v for k, v in _env(mac, HH_BREW_CANDIDATES=str(brew)).items() if k != "HH_MAC_OWNER"}
    r = subprocess.run(["bash", str(SETUP)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    me = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
    assert f"<string>{me}</string>" in (mac["tmp"] / "io.hydrahive.shares.plist").read_text()


def test_setup_zieht_vorhandene_freigaben_nach(mac) -> None:
    """Nach Update/Neuinstallation: eingeschaltete Projekte neu beauftragen (Besitzer-Zugang, Rechte, Datensätze)."""
    d = mac["conf"] / "mac-shares.d"
    d.mkdir()
    (d / f"{PID}.name").write_text("test123\n")
    (d / f"{PID}.state").write_text("on\n")
    (d / "anderes.name").write_text("aus\n")
    (d / "anderes.state").write_text("off\n")
    _setup(mac)
    want = d / f"{PID}.want"
    assert want.read_text().splitlines() == ["on", "test123", str(mac["data"] / "workspaces" / "projects" / PID)]
    assert not (d / "anderes.want").exists()


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


# --- Update: Freigabe mitpflegen ----------------------------------------------------------------------------------

UPDATE = INSTALLER / "update-mac.sh"


def _run_update_sharing(tmp_path: Path, plist_exists: bool) -> list[str]:
    """Nur den Freigabe-Block von update-mac.sh ausführen."""
    text = UPDATE.read_text()
    start = text.index("# Dateifreigabe")
    end = text.index("if grep -q '^HH_INSTALL_TAILSCALE=yes'")
    repo, ran = tmp_path / "repo", tmp_path / "ran.log"
    _exe(repo / "installer" / "modules-mac" / "47-filesharing.sh", f'echo "47 user=$HH_USER" >> "{ran}"\n')
    plist = tmp_path / "io.hydrahive.shares.plist"
    if plist_exists:
        plist.write_text("x")
    script = ('log() { echo "$*"; }\nto_log() { cat; }\n'
              f'HH_REPO_DIR="{repo}"\nHH_CONFIG_DIR="{tmp_path}"\nHH_DATA_DIR="{tmp_path}"\nHH_USER=tester\n'
              f'HH_SHARES_PLIST="{plist}"\n' + text[start:end])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    return ran.read_text().splitlines() if ran.exists() else []


def test_update_pflegt_freigabe_nur_wenn_installiert(tmp_path) -> None:
    """Der Fix muss beim Kunden per Update ankommen – aber nichts einrichten, was er nicht wollte."""
    assert _run_update_sharing(tmp_path / "a", plist_exists=True) == ["47 user=tester"]
    assert _run_update_sharing(tmp_path / "b", plist_exists=False) == []
