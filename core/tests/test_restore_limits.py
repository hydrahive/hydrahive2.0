"""Restore-Größen-Caps gegen Dekompressionsbomben/Disk-Fill (Issue #189)."""
from __future__ import annotations

import io
import tarfile

import pytest

from hydrahive.backup import _limits


def _tar_with_file(size: int) -> tarfile.TarFile:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        data = b"x" * size
        ti = tarfile.TarInfo("data.bin")
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))
    buf.seek(0)
    return tarfile.open(fileobj=buf, mode="r")


def test_enforce_archive_limits_rejects_oversize():
    tar = _tar_with_file(1024)
    with pytest.raises(_limits.RestoreTooLarge) as e:
        _limits.enforce_archive_limits(tar, max_bytes=10)
    assert e.value.code == "backup_extracted_too_large"


def test_enforce_archive_limits_rejects_too_many_members():
    tar = _tar_with_file(8)
    with pytest.raises(_limits.RestoreTooLarge) as e:
        _limits.enforce_archive_limits(tar, max_members=0)
    assert e.value.code == "backup_too_many_members"


def test_enforce_archive_limits_passes_within_caps():
    tar = _tar_with_file(64)
    _limits.enforce_archive_limits(tar, max_bytes=1_000_000, max_members=100)  # kein raise


def test_stream_upload_capped_aborts_over_limit(tmp_path):
    import asyncio

    class _FakeUpload:
        def __init__(self, total): self._left = total
        async def read(self, n):
            if self._left <= 0:
                return b""
            take = min(n, self._left)
            self._left -= take
            return b"x" * take

    dest = tmp_path / "up.bin"

    async def body():
        await _limits.stream_upload_capped(_FakeUpload(5000), dest, max_bytes=1000)

    with pytest.raises(_limits.RestoreTooLarge) as e:
        asyncio.run(body())
    assert e.value.code == "backup_upload_too_large"


def test_stream_upload_capped_writes_within_limit(tmp_path):
    import asyncio

    class _FakeUpload:
        def __init__(self, total): self._left = total
        async def read(self, n):
            if self._left <= 0:
                return b""
            take = min(n, self._left)
            self._left -= take
            return b"y" * take

    dest = tmp_path / "ok.bin"
    asyncio.run(_limits.stream_upload_capped(_FakeUpload(500), dest, max_bytes=1_000_000))
    assert dest.stat().st_size == 500
