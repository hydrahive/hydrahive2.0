"""CIFS-Mount-Mechanik — mountet eine SMB-Freigabe sicher in den Workspace.

Sicherheitsprinzipien:
- Das Passwort wird NIE als Prozess-Argument übergeben (wäre in `ps`/`/proc`
  sichtbar), sondern über eine temporäre Credentials-Datei (chmod 600), die
  direkt nach dem Mount gelöscht wird.
- Der Mountpoint wird serverseitig aus workspace_path konstruiert; der Name
  ist regex-validiert (kein Pfad-Metazeichen) → kein Path-Traversal.
- mount.cifs-Optionen werden gegen eine Whitelist gefiltert.
- mount/umount laufen über `sudo bash -c` (vorhandenes NOPASSWD-Recht).
"""
from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
import tempfile

from hydrahive.credentials.store import get_credential
from hydrahive.projects._paths import workspace_path
from hydrahive.smbmounts.models import (
    ALLOWED_OPTIONS, HOST_RE, NAME_RE, SHARE_RE, SUBPATH_RE, SmbMount,
)

logger = logging.getLogger(__name__)

_NAME = re.compile(NAME_RE)
_HOST = re.compile(HOST_RE)
_SHARE = re.compile(SHARE_RE)
_SUBPATH = re.compile(SUBPATH_RE)


def mountpoint_for(project_id: str, name: str) -> str:
    """Pfad, unter dem das Share im Projekt-Workspace erscheint."""
    return str(workspace_path(project_id) / "mounts" / name)


def _validate(m: SmbMount) -> str | None:
    """Gibt einen Fehlercode zurück, wenn ein Feld unsicher/ungültig ist."""
    if not _NAME.match(m.name):
        return "mount_name_invalid"
    if not _HOST.match(m.host):
        return "mount_host_invalid"
    if not _SHARE.match(m.share):
        return "mount_share_invalid"
    if m.subpath is not None:
        if not _SUBPATH.match(m.subpath) or ".." in m.subpath:
            return "mount_subpath_invalid"
    return None


def _unc_path(m: SmbMount) -> str:
    """//host/share[/subpath] — mit Forward-Slashes (mount.cifs akzeptiert das)."""
    unc = f"//{m.host}/{m.share}"
    if m.subpath:
        unc += "/" + m.subpath.strip("/")
    return unc


def _filter_options(raw: str | None) -> list[str]:
    """Nur Whitelist-Optionen durchlassen (key oder key=value)."""
    if not raw:
        return []
    out: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        key = part.split("=", 1)[0]
        if key in ALLOWED_OPTIONS and re.fullmatch(r"[A-Za-z0-9_=./-]+", part):
            out.append(part)
    return out


def _resolve_credential(owner: str, cred_name: str | None) -> tuple[str, str]:
    """Liefert (username, password) aus einem 'basic'-Credential des Owners.

    Ohne Credential → guest (leere Strings).
    """
    if not cred_name:
        return "", ""
    cred = get_credential(owner, cred_name)
    if cred is None or cred.type != "basic":
        raise ValueError("mount_credential_invalid")
    user, _, password = cred.value.partition(":")
    return user, password


def _build_mount_options(m: SmbMount, user: str, has_pw: bool,
                         creds_file: str) -> str:
    """Baut den -o Options-String. Passwort kommt aus creds_file, nie inline."""
    opts = [f"credentials={creds_file}"]
    # uid/gid: der Backend-User soll lesen/schreiben können.
    opts.append(f"uid={os.getuid()}")
    opts.append(f"gid={os.getgid()}")
    opts.append("rw" if not m.read_only else "ro")
    if not user and not has_pw:
        opts.append("guest")
    opts.extend(_filter_options(m.options))
    return ",".join(opts)


def mount(m: SmbMount) -> tuple[bool, str]:
    """Mountet das Share. Gibt (ok, error_code|mountpoint) zurück."""
    err = _validate(m)
    if err:
        return False, err
    if not m.project_id:
        return False, "mount_no_project"

    try:
        user, password = _resolve_credential(m.owner, m.credential)
    except ValueError as e:
        return False, str(e)

    mp = mountpoint_for(m.project_id, m.name)
    os.makedirs(mp, exist_ok=True)

    # Credentials-Datei: chmod 600, im Backend-Tempdir, nach Mount gelöscht.
    creds_path = ""
    if user or password:
        fd, creds_path = tempfile.mkstemp(prefix="cifs-", suffix=".cred")
        with os.fdopen(fd, "w") as fh:
            fh.write(f"username={user}\npassword={password}\n")
        os.chmod(creds_path, 0o600)

    unc = _unc_path(m)
    options = _build_mount_options(m, user, bool(password), creds_path or "/dev/null")
    cmd = f"mount.cifs {shlex.quote(unc)} {shlex.quote(mp)} -o {shlex.quote(options)}"

    try:
        proc = subprocess.run(
            ["sudo", "-n", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "mount_timeout"
    finally:
        if creds_path:
            try:
                os.unlink(creds_path)
            except OSError:
                pass

    if proc.returncode != 0:
        logger.warning("mount.cifs failed (%s): %s", proc.returncode, proc.stderr.strip())
        return False, "mount_failed"
    return True, mp


def umount(m: SmbMount) -> tuple[bool, str]:
    """Hängt das Share aus. Idempotent: nicht-gemountet → ok."""
    if not m.project_id:
        return True, "ok"
    if not _NAME.match(m.name):
        return False, "mount_name_invalid"
    mp = mountpoint_for(m.project_id, m.name)
    if not is_mounted(mp):
        return True, "ok"
    cmd = f"umount {shlex.quote(mp)}"
    try:
        proc = subprocess.run(
            ["sudo", "-n", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "umount_timeout"
    if proc.returncode != 0:
        logger.warning("umount failed (%s): %s", proc.returncode, proc.stderr.strip())
        return False, "umount_failed"
    return True, "ok"


def is_mounted(mountpoint: str) -> bool:
    """Prüft, ob der Pfad ein aktiver Mountpoint ist."""
    try:
        return os.path.ismount(mountpoint)
    except OSError:
        return False
