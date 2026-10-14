"""Fixtures für die Tests „Kopie auf externen Server“ (Spec archiv-system.md, Etappe 3).

`fake_remote`: ein Server-Ersatz mit derselben Schnittstelle wie archive/remote_smb.SmbRemote, der in
einen Ordner schreibt. `down=True` simuliert „Server weg“, `corrupt` verfälscht den nächsten Upload.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


class FakeRemote:
    def __init__(self, root: Path) -> None:
        self.root, self.down, self.corrupt, self.puts, self.subdir = root, False, False, 0, ""

    def _p(self, rel: str) -> Path:
        """Wie SmbRemote: Pfade sind relativ zum eingetragenen Unterordner."""
        assert ".." not in rel.split("/") and not rel.startswith("/"), rel
        return self.root / self.subdir / rel

    def _check(self) -> None:
        if self.down:
            from hydrahive.archive.remote_smb import RemoteError
            raise RemoteError("unreachable")

    def put(self, rel: str, local: Path) -> None:
        self._check()
        self.puts += 1
        dst = self._p(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = local.read_bytes()
        if self.corrupt:
            data, self.corrupt = data[:-1] + bytes([data[-1] ^ 1]), False
        part = dst.with_name(dst.name + ".part")
        part.write_bytes(data)
        os.replace(part, dst)

    def read_chunks(self, rel: str):
        self._check()
        if not self._p(rel).is_file():                     # wie SmbRemote: fehlende Datei → not_found
            from hydrahive.archive.remote_smb import RemoteError
            raise RemoteError("not_found")
        with open(self._p(rel), "rb") as fh:
            while chunk := fh.read(1 << 16):
                yield chunk

    def size(self, rel: str) -> int | None:
        self._check()
        p = self._p(rel)
        return p.stat().st_size if p.exists() else None

    def free_bytes(self) -> int:
        self._check()
        return 10 * 1024 ** 4

    def close(self) -> None:
        pass

    def probe(self) -> None:
        self._check()
        p = self._p(".hydrahive-probe")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"ok")
        assert p.read_bytes() == b"ok"
        p.unlink()


@pytest.fixture
def fake_remote(tmp_path, monkeypatch):
    from hydrahive.archive import remote_smb
    fake = FakeRemote(tmp_path / "nas")
    fake.root.mkdir()
    def connect(cfg):
        fake.subdir = cfg.get("subdir") or ""
        return fake

    monkeypatch.setattr(remote_smb, "connect", connect)
    return fake


@pytest.fixture
def remote_queue(monkeypatch):
    """Kopier-Reihe nur einreihen, im Test selbst abarbeiten; Zustand je Test leer."""
    from hydrahive.archive import remote_sync
    monkeypatch.setattr(remote_sync, "_start_worker", lambda: None)
    remote_sync.reset_for_tests()
    yield remote_sync
    remote_sync.reset_for_tests()


@pytest.fixture
def remote_on(fake_remote, remote_queue):
    """Server eingetragen, getestet und aktiv."""
    from hydrahive.archive import remote_config
    remote_config.save({"host": "nas.local", "share": "Backups", "subdir": "hydrahive", "user": "hh",
                        "password": "geheim-NAS-123"})
    remote_config.mark_tested(remote_config.fingerprint())
    remote_config.set_active(True)
    yield fake_remote
    remote_config.reset_for_tests()
