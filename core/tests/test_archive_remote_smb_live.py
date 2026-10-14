"""Echter SMB-Server (Spec archiv-system.md, Etappe 3). Nur mit HH_TEST_SMB_URL, sonst übersprungen.

HH_TEST_SMB_URL=smb://user:pass@host/share/unterordner – der Unterordner wird angelegt und am Ende
wieder geleert (nur Dateien, die der Test selbst schreibt).
"""
from __future__ import annotations

import hashlib
import os
import uuid
from urllib.parse import unquote, urlparse

import pytest

URL = os.environ.get("HH_TEST_SMB_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="HH_TEST_SMB_URL nicht gesetzt (nur auf hydratest)")


def _cfg(**over) -> dict:
    u = urlparse(URL)
    share, _, sub = u.path.lstrip("/").partition("/")
    base = {"host": u.hostname, "share": share, "subdir": f"{sub.strip('/')}/hh-test-{uuid.uuid4().hex[:8]}",
            "user": unquote(u.username or ""), "password": unquote(u.password or "")}
    return {**base, **over}


def _cleanup(cfg: dict) -> None:
    import smbclient
    from hydrahive.archive.remote_smb import SmbRemote
    remote = SmbRemote(cfg)
    remote.login()
    root = remote._unc()
    for dirpath, dirs, files in reversed(list(smbclient.walk(root, **remote._kw))):
        for f in files:
            smbclient.remove(f"{dirpath}\\{f}", **remote._kw)
        smbclient.rmdir(dirpath, **remote._kw)


def test_roundtrip_and_overwrite(tmp_path) -> None:
    from hydrahive.archive import remote_smb
    cfg = _cfg()
    remote = remote_smb.connect(cfg)
    try:
        remote.probe()
        assert remote.free_bytes() > 0
        local = tmp_path / "p.tar.gz"
        local.write_bytes(os.urandom(5 * 1024 * 1024 + 7))
        remote.put("agents/p.tar.gz", local)
        local.write_bytes(os.urandom(1024))                     # zweites Mal: über bestehende Datei
        remote.put("agents/p.tar.gz", local)
        got = hashlib.sha256(b"".join(remote.read_chunks("agents/p.tar.gz"))).hexdigest()
        assert got == hashlib.sha256(local.read_bytes()).hexdigest()
        assert remote.size("agents/p.tar.gz") == 1024 and remote.size("agents/fehlt.tar.gz") is None
    finally:
        _cleanup(cfg)


@pytest.mark.parametrize("over,code", [
    ({"password": "ganz-falsch"}, "auth_failed"),
    ({"share": "GibtEsNicht"}, "share_not_found"),
    ({"host": "192.0.2.1"}, "unreachable"),
])
def test_errors_have_clear_codes(over, code) -> None:
    from hydrahive.archive import remote_smb
    import smbclient
    smbclient.reset_connection_cache()
    with pytest.raises(remote_smb.RemoteError) as e:
        remote_smb.connect(_cfg(**over)).probe()
    assert e.value.code == code


def test_wrong_password_after_a_good_login_is_still_rejected() -> None:
    """Gefunden auf hydratest: Nach einer gültigen Anmeldung lief ein Test mit falschem Passwort still über die
    gemerkte Verbindung und meldete „ok“ – damit hätte man falsche Daten aktiv schalten können."""
    from hydrahive.archive import remote_smb
    cfg = _cfg()
    remote_smb.connect(cfg).probe()
    with pytest.raises(remote_smb.RemoteError) as e:
        remote_smb.connect({**cfg, "password": "ganz-falsch"}).probe()
    assert e.value.code == "auth_failed"
    _cleanup(cfg)
