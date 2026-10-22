"""installer/lib/mac-service-user.sh (Plan docs/plans/mac-service-user.md): System-Konto _hydrahive anlegen.

Nachgebauter Mac: dscl/id/dseditgroup arbeiten auf einer Textdatei (Nutzer + Gruppen mit IDs).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SCRIPT = INSTALLER / "lib" / "mac-service-user.sh"


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    """Verzeichnisdienst als Dateien: users.txt „name uid gid“, groups.txt „name gid“, attrs.txt „name key value“."""
    db = tmp_path / "ds"
    db.mkdir()
    (db / "users.txt").write_text("root 0 0\nalexmo 501 20\n_www 70 70\n")
    (db / "groups.txt").write_text("wheel 0\nstaff 20\n_www 70\ncom.apple.access_remote_ae 400\n")
    (db / "attrs.txt").write_text("")
    calls = tmp_path / "calls.log"
    calls.write_text("")
    bin_ = tmp_path / "bin"
    _exe(bin_ / "dscl", f'''echo "dscl $*" >> "{calls}"
DB="{db}"
[ "$1" = "." ] && shift
cmd="$1"; shift
case "$cmd" in
  -list)
    case "$1" in
      /Users) awk '{{print $1, $2}}' "$DB/users.txt";;
      /Groups) awk '{{print $1, $2}}' "$DB/groups.txt";;
    esac;;
  -read)
    kind="${{1#/}}"; kind="${{kind%%/*}}"; name="${{1##*/}}"
    if [ "$kind" = Users ]; then grep -q "^$name " "$DB/users.txt" || {{ echo "DS Error: -14136 (eDSRecordNotFound)" >&2; exit 56; }}
    else grep -q "^$name " "$DB/groups.txt" || {{ echo "DS Error: -14136 (eDSRecordNotFound)" >&2; exit 56; }}; fi
    [ -n "$2" ] && grep "^$name $2 " "$DB/attrs.txt" | head -1 | awk '{{print $2": "$3}}';;
  -create)
    kind="${{1#/}}"; kind="${{kind%%/*}}"; name="${{1##*/}}"; key="$2"; val="$3"
    if [ "$kind" = Users ]; then
      grep -q "^$name " "$DB/users.txt" || echo "$name - -" >> "$DB/users.txt"
      [ "$key" = UniqueID ] && sed -i "s/^$name [^ ]* /$name $val /" "$DB/users.txt"
      [ "$key" = PrimaryGroupID ] && sed -i "s/^\\($name [^ ]*\\) .*/\\1 $val/" "$DB/users.txt"
    else
      grep -q "^$name " "$DB/groups.txt" || echo "$name -" >> "$DB/groups.txt"
      [ "$key" = PrimaryGroupID ] && sed -i "s/^$name .*/$name $val/" "$DB/groups.txt"
    fi
    [ -n "$key" ] && echo "$name $key $val" >> "$DB/attrs.txt";;
  -delete) :;;
esac
exit 0
''')
    _exe(bin_ / "id", f'''DB="{db}"
if [ "$1" = "-u" ] && [ -z "$2" ]; then echo 0; exit 0; fi
name="${{@: -1}}"
line=$(grep "^$name " "$DB/users.txt") || {{ echo "id: $name: no such user" >&2; exit 1; }}
case "$1" in -u) echo "$line" | awk '{{print $2}}';; -g) echo "$line" | awk '{{print $3}}';; *) echo "uid=$(echo $line | awk '{{print $2}}')($name)";; esac
''')
    _exe(bin_ / "sudo", 'exec "$@"\n')
    _exe(bin_ / "chown", f'echo "chown $*" >> "{calls}"\n')
    return {"tmp": tmp_path, "bin": bin_, "db": db, "calls": calls}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": f"{m['bin']}:/usr/bin:/bin", "HH_SVC_HOME": str(m["tmp"] / "home"), **extra}
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30)


def _users(m: dict) -> dict:
    return {l.split()[0]: l.split()[1:] for l in (m["db"] / "users.txt").read_text().splitlines()}


def _groups(m: dict) -> dict:
    return {l.split()[0]: l.split()[1] for l in (m["db"] / "groups.txt").read_text().splitlines()}


def _attrs(m: dict, name: str) -> dict:
    out = {}
    for l in (m["db"] / "attrs.txt").read_text().splitlines():
        parts = l.split(" ", 2)
        if parts[0] == name and len(parts) == 3:
            out[parts[1]] = parts[2]
    return out


def test_creates_hidden_system_account(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    uid, gid = _users(mac)["_hydrahive"]
    assert uid == gid and 450 <= int(uid) <= 499
    assert _groups(mac)["_hydrahive"] == uid
    a = _attrs(mac, "_hydrahive")
    assert a["UserShell"] == "/usr/bin/false"
    assert a["IsHidden"] == "1"
    assert a["NFSHomeDirectory"] == str(mac["tmp"] / "home")
    assert "Password" in a and a["Password"] == "*"            # kein Login möglich


def test_id_free_for_user_and_group(mac):
    """Befund macOS 27: GID 400 ist schon vergeben (com.apple.access_remote_ae) – Nutzer UND Gruppe frei prüfen."""
    (mac["db"] / "users.txt").write_text("root 0 0\n_x 450 450\n")
    (mac["db"] / "groups.txt").write_text("wheel 0\n_y 451 \ncom.apple.access_remote_ae 452\n")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    uid, gid = _users(mac)["_hydrahive"]
    assert uid == gid == "453"


def test_idempotent_keeps_existing_account(mac):
    _run(mac)
    first = _users(mac)["_hydrahive"]
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _users(mac)["_hydrahive"] == first
    assert not any(l.startswith("dscl . -create") for l in mac["calls"].read_text().splitlines())
    assert "_hydrahive" in r.stdout


def test_no_free_id_fails(mac):
    users = "".join(f"_u{i} {i} {i}\n" for i in range(450, 500))
    (mac["db"] / "users.txt").write_text("root 0 0\n" + users)
    r = _run(mac)
    assert r.returncode != 0
    assert "_hydrahive" not in _users(mac)


def test_home_belongs_to_account(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    home = mac["tmp"] / "home"
    assert home.is_dir()
    assert f"chown _hydrahive:_hydrahive {home}" in mac["calls"].read_text()
    assert oct(home.stat().st_mode)[-3:] == "750"


def test_name_override_for_tests(mac):
    r = _run(mac, HH_SVC_USER="_hhtest")
    assert r.returncode == 0
    assert "_hhtest" in _users(mac) and "_hydrahive" not in _users(mac)


def test_no_linux_tools():
    text = SCRIPT.read_text()
    for bad in ("useradd", "groupadd", "systemctl", "apt-get"):
        assert bad not in text, bad
