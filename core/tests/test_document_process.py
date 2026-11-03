from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hydrahive.tools import _document_process as process


def test_linux_sandbox_has_no_network_read_only_input_and_resource_limits(tmp_path: Path, monkeypatch):
    root = tmp_path / "snapshot"
    work = root / "work"
    work.mkdir(parents=True)
    (root / "input.pdf").write_bytes(b"%PDF-")
    binaries = {"pdfinfo": "/usr/bin/pdfinfo", "bwrap": "/usr/bin/bwrap", "prlimit": "/usr/bin/prlimit"}
    monkeypatch.setattr(process.platform, "system", lambda: "Linux")
    monkeypatch.setattr(process.shutil, "which", lambda name, path=None: binaries.get(name))

    argv = process._sandbox_argv(["pdfinfo", str(root / "input.pdf")], root, work)

    assert argv[:2] == ["/usr/bin/prlimit", "--as=1073741824"]
    assert "/usr/bin/bwrap" in argv
    assert "--unshare-all" in argv and "--clearenv" in argv
    assert ["--tmpfs", "/tmp"] == argv[argv.index("--tmpfs"):argv.index("--tmpfs") + 2]
    assert any(argv[i:i + 3] == ["--ro-bind", str(root), str(root)] for i in range(len(argv) - 2))
    bind = argv.index("--bind")
    assert argv[bind:bind + 3] == ["--bind", str(work), str(work)]
    assert argv[-2:] == ["/usr/bin/pdfinfo", str(root / "input.pdf")]


def test_macos_sandbox_denies_by_default_and_allows_only_private_workdir(tmp_path: Path, monkeypatch):
    root = tmp_path / "snapshot"
    work = root / "work"
    work.mkdir(parents=True)
    monkeypatch.setattr(process.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(process.shutil, "which", lambda name, path=None: {
        "pdfinfo": "/opt/homebrew/bin/pdfinfo", "sandbox-exec": "/usr/bin/sandbox-exec", "bash": "/bin/bash",
    }.get(name))

    argv = process._sandbox_argv(["pdfinfo", str(root / "input.pdf")], root, work)
    profile = Path(argv[argv.index("-f") + 1]).read_text(encoding="utf-8")

    assert argv[:2] == ["/bin/bash", "-c"]
    assert "ulimit -t 120" in argv[2] and 'exec "$@"' in argv[2]
    assert argv[-2:] == ["/opt/homebrew/bin/pdfinfo", str(root / "input.pdf")]
    assert "(deny default)" in profile
    assert "(deny network*)" in profile
    assert "(allow process-exec)" in profile
    assert "(allow process*)" not in profile and "mach-lookup" not in profile
    assert '(deny file-read* (subpath "/System/Volumes/Data"))' in profile
    assert '(subpath "/System")' not in profile
    assert f'(allow file-write* (subpath "{work}"))' in profile
    assert f'(allow file-read* (subpath "{root}"))' in profile

    # pdfinfo → pdftotext → OCR verwenden dasselbe private Profil; 0400 darf
    # beim zweiten Schritt nicht erneut mit write_text überschrieben werden.
    before = Path(argv[argv.index("-f") + 1]).read_bytes()
    second = process._sandbox_argv(["pdfinfo", str(root / "input.pdf")], root, work)
    second_profile = Path(second[second.index("-f") + 1])
    assert second_profile.read_bytes() == before
    assert second_profile.stat().st_mode & 0o777 == 0o400


def test_unknown_platform_fails_closed(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(process.platform, "system", lambda: "Windows")
    with pytest.raises(process.DocumentIsolationError, match="nicht verfügbar"):
        process._sandbox_argv(["pdfinfo", "input.pdf"], tmp_path, tmp_path)


def test_run_uses_minimal_environment_and_never_shell(tmp_path: Path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    captured = {}

    class FakeProcess:
        stdout = object()
        returncode = 0
        pid = 123

    monkeypatch.setattr(process, "_sandbox_argv", lambda argv, root, writable: ["sandbox", *argv])
    monkeypatch.setattr(process, "_collect", lambda child, timeout, max_bytes: b"Pages: 1\n")

    def fake_popen(argv, **kwargs):
        captured.update(argv=argv, kwargs=kwargs)
        return FakeProcess()

    monkeypatch.setattr(process.subprocess, "Popen", fake_popen)
    result = process.run(["pdfinfo", str(tmp_path / "input.pdf")], 4, tmp_path, work, 1000)

    assert result == "Pages: 1\n"
    assert captured["argv"][0] == "sandbox"
    assert captured["kwargs"]["start_new_session"] is True
    assert captured["kwargs"].get("shell", False) is False
    assert set(captured["kwargs"]["env"]) == {"PATH", "LANG", "LC_ALL", "HOME", "TMPDIR"}


def test_collect_kills_process_when_output_limit_is_exceeded():
    child = subprocess.Popen(
        ["/usr/bin/python3", "-c", "print('x' * 200000)"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    with pytest.raises(process.DocumentIsolationError, match="Ausgabelimit"):
        process._collect(child, timeout=5, max_bytes=1024)
    assert child.poll() is not None


def test_collect_kills_process_on_timeout():
    child = subprocess.Popen(
        ["/bin/sh", "-c", "sleep 5"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    with pytest.raises(process.DocumentIsolationError, match="Zeitlimit"):
        process._collect(child, timeout=0.05, max_bytes=1024)
    assert child.poll() is not None
