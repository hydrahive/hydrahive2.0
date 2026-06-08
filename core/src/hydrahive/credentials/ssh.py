"""SSH-Config-Manager für ssh_key-Credentials.

Verwaltet einen HydraHive-eigenen Abschnitt in der SSH-Config des Service-Accounts.
Beim Speichern/Löschen von ssh_key-Credentials wird dieser Abschnitt regeneriert.

Aufbau:
  ~/.ssh/config (= data_dir/.ssh/config)
    [eventuell manueller Teil]
    # === HydraHive SSH Credentials — DO NOT EDIT ===
    Host 192.168.178.216
        User joshua
        IdentityFile /var/lib/hydrahive2/.ssh/cred_alice_testserver_key
        StrictHostKeyChecking accept-new
        UserKnownHostsFile /var/lib/hydrahive2/.ssh/known_hosts
    # === End HydraHive SSH Credentials ===

Key-Dateien: data_dir/.ssh/cred_{username}_{credname}_key
"""
from __future__ import annotations

import logging
import os
import re
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

_SECTION_START = "# === HydraHive SSH Credentials — DO NOT EDIT ==="
_SECTION_END = "# === End HydraHive SSH Credentials ==="


def _ssh_dir() -> Path:
    from hydrahive.settings import settings
    return Path(str(settings.data_dir)) / ".ssh"


def _key_path(username: str, cred_name: str) -> Path:
    return _ssh_dir() / f"cred_{username}_{cred_name}_key"


def _config_path() -> Path:
    return _ssh_dir() / "config"


def _known_hosts_path() -> Path:
    return _ssh_dir() / "known_hosts"


def _ensure_ssh_dir() -> Path:
    d = _ssh_dir()
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def write_ssh_key(username: str, cred_name: str, private_key: str) -> Path:
    """Schreibt den privaten Key in eine dedizierte Datei. Gibt den Pfad zurück."""
    _ensure_ssh_dir()
    path = _key_path(username, cred_name)
    key = private_key.strip()
    if key and not key.endswith("\n"):
        key += "\n"
    path.write_text(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def remove_ssh_key(username: str, cred_name: str) -> None:
    """Löscht die Key-Datei falls vorhanden."""
    path = _key_path(username, cred_name)
    try:
        path.unlink(missing_ok=True)
    except OSError as e:
        logger.warning("Key-Datei konnte nicht gelöscht werden: %s: %s", path, e)


_SAFE_HOST = re.compile(r"^[A-Za-z0-9.\-]{1,253}$")
_SAFE_USER = re.compile(r"^[A-Za-z0-9._\-]{1,32}$")


def _build_host_block(host: str, ssh_user: str, key_path: Path) -> str:
    """Generiert einen SSH-Config Host-Block.

    Beide Parameter werden gegen enge Allowlists geprüft — verhindert
    SSH-Config-Injection via ProxyCommand oder andere Direktiven.
    """
    if not _SAFE_HOST.match(host):
        raise ValueError(f"Ungültiger SSH-Hostname: {host!r}")
    if not _SAFE_USER.match(ssh_user):
        raise ValueError(f"Ungültiger SSH-Username: {ssh_user!r}")
    known_hosts = _known_hosts_path()
    lines = [
        f"Host {host}",
        f"    User {ssh_user}",
        f"    IdentityFile {key_path}",
        "    StrictHostKeyChecking accept-new",
        f"    UserKnownHostsFile {known_hosts}",
        "",
    ]
    return "\n".join(lines)


def rebuild_ssh_config(all_ssh_credentials: list[tuple[str, str, str, str]]) -> None:
    """Regeneriert den HydraHive-Abschnitt der SSH-Config.

    all_ssh_credentials: Liste von (username, cred_name, host, ssh_user) für alle
    ssh_key-Credentials aller User.
    """
    _ensure_ssh_dir()
    config_file = _config_path()

    # Existierenden manuellen Inhalt außerhalb des HH-Blocks erhalten
    manual_part = ""
    if config_file.exists():
        content = config_file.read_text()
        start = content.find(_SECTION_START)
        if start == -1:
            manual_part = content.rstrip()
        else:
            manual_part = content[:start].rstrip()

    # Neuen HH-Block bauen
    if all_ssh_credentials:
        blocks = [_SECTION_START, ""]
        for username, cred_name, host, ssh_user in all_ssh_credentials:
            key_p = _key_path(username, cred_name)
            blocks.append(_build_host_block(host, ssh_user, key_p))
        blocks.append(_SECTION_END)
        hh_section = "\n".join(blocks)
    else:
        hh_section = ""

    parts = [p for p in [manual_part, hh_section] if p]
    new_content = "\n\n".join(parts)
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"

    config_file.write_text(new_content)
    try:
        os.chmod(config_file, 0o600)
    except OSError:
        pass


def _load_all_ssh_credentials() -> list[tuple[str, str, str, str]]:
    """Sammelt alle ssh_key-Credentials aller User aus dem Store."""
    from hydrahive.settings import settings
    cred_dir = Path(str(settings.data_dir)) / "credentials"
    if not cred_dir.exists():
        return []

    from hydrahive.credentials.store import _load_raw  # noqa: PLC0415
    result: list[tuple[str, str, str, str]] = []
    for json_file in cred_dir.glob("*.json"):
        username = json_file.stem
        try:
            raw = _load_raw(username)
        except Exception:
            continue
        for cred_name, row in raw.items():
            if not isinstance(row, dict) or row.get("type") != "ssh_key":
                continue
            host = (row.get("url_pattern") or "").strip()
            ssh_user = (row.get("header_name") or "").strip()
            if host and ssh_user:
                result.append((username, cred_name, host, ssh_user))
    return result


def sync_ssh_config() -> None:
    """Liest alle ssh_key-Credentials und schreibt die SSH-Config neu."""
    try:
        entries = _load_all_ssh_credentials()
        rebuild_ssh_config(entries)
        logger.info("SSH-Config synchronisiert (%d Einträge)", len(entries))
    except Exception as e:
        logger.error("SSH-Config sync fehlgeschlagen: %s", e)
