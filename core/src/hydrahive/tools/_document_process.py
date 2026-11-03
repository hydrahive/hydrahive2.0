"""Fail-closed Sandbox und begrenztes stdout für lokale Dokumentparser."""
from __future__ import annotations

import os
import platform
import selectors
import shutil
import signal
import subprocess
import time
from contextlib import suppress
from pathlib import Path

_MAX_MEMORY = 1_073_741_824
_MAX_FILE = 268_435_456


class DocumentIsolationError(RuntimeError):
    pass


class ProcessFailed(RuntimeError):
    pass


def _required(name: str) -> str:
    found = shutil.which(name, path="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
    if not found:
        raise DocumentIsolationError(f"Dokument-Isolation fehlt ({name}); bitte HydraHive aktualisieren.")
    return found


def _sb(value: Path) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _mac_profile(root: Path, work: Path) -> Path:
    profile = root / "document-parser.sb"
    if profile.exists():
        return profile
    profile.write_text(
        "\n".join([
            "(version 1)", "(deny default)", "(deny network*)", "(allow process-exec)",
            "(deny file-read* (subpath \"/System/Volumes/Data\"))", "(allow sysctl-read)",
            '(allow file-read* (subpath "/System/Library") '
            '(subpath "/System/Volumes/Preboot/Cryptexes/OS/System/Library") '
            '(subpath "/System/Volumes/Preboot/Cryptexes/OS/usr/lib") (subpath "/Library/Fonts") '
            '(subpath "/usr/bin") (subpath "/usr/lib") (subpath "/usr/share") '
            '(subpath "/opt/homebrew/bin") (subpath "/opt/homebrew/lib") '
            '(subpath "/opt/homebrew/share") (subpath "/opt/homebrew/Cellar") (subpath "/opt/homebrew/opt") '
            '(subpath "/usr/local/bin") (subpath "/usr/local/lib") (subpath "/usr/local/share") '
            '(subpath "/usr/local/Cellar") (subpath "/usr/local/opt"))',
            f'(allow file-read* (subpath "{_sb(root)}"))',
            f'(allow file-write* (subpath "{_sb(work)}"))',
        ]) + "\n", encoding="utf-8",
    )
    profile.chmod(0o400)
    return profile


def _sandbox_argv(argv: list[str], root: Path, work: Path) -> list[str]:
    command = _required(argv[0])
    system = platform.system()
    if system == "Linux":
        bwrap, prlimit = _required("bwrap"), _required("prlimit")
        return [
            prlimit, f"--as={_MAX_MEMORY}", "--cpu=120", f"--fsize={_MAX_FILE}",
            "--nproc=64", "--nofile=64", "--", bwrap,
            "--die-with-parent", "--new-session", "--unshare-all", "--cap-drop", "ALL", "--clearenv",
            "--ro-bind", "/usr", "/usr", "--ro-bind-try", "/bin", "/bin",
            "--ro-bind-try", "/lib", "/lib", "--ro-bind-try", "/lib64", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--ro-bind", str(root), str(root), "--bind", str(work), str(work),
            "--chdir", str(work), "--setenv", "HOME", str(work), "--setenv", "TMPDIR", str(work),
            "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8",
            "--", command, *argv[1:],
        ]
    if system == "Darwin":
        sandbox = [_required("sandbox-exec"), "-f", str(_mac_profile(root, work)), command, *argv[1:]]
        limits = "ulimit -t 120 -f 524288 -n 64 -u 64 -d 1048576 -v 1048576; exec \"$@\""
        return [_required("bash"), "-c", limits, "hh-document-limit", *sandbox]
    raise DocumentIsolationError("Lokale Dokument-Isolation ist auf diesem Betriebssystem nicht verfügbar.")


def _terminate(process: subprocess.Popen) -> None:
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=5)


def _collect(process: subprocess.Popen, timeout: float, max_bytes: int) -> bytes:
    if process.stdout is None:
        raise DocumentIsolationError("Dokumentparser hat keinen sicheren Ausgabekanal.")
    deadline = time.monotonic() + timeout
    output = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate(process)
                raise DocumentIsolationError("Zeitlimit der lokalen Dokument-Isolation überschritten.")
            events = selector.select(min(0.2, remaining))
            if not events:
                continue
            chunk = os.read(process.stdout.fileno(), 65_536)
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > max_bytes:
                _terminate(process)
                raise DocumentIsolationError("Ausgabelimit der lokalen Dokument-Isolation überschritten.")
    try:
        process.wait(timeout=max(0.1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired as exc:
        _terminate(process)
        raise DocumentIsolationError("Zeitlimit der lokalen Dokument-Isolation überschritten.") from exc
    return bytes(output)


def run(argv: list[str], timeout: float, root: Path, work: Path, max_bytes: int) -> str:
    wrapped = _sandbox_argv(argv, root, work)
    env = {
        "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "HOME": str(work), "TMPDIR": str(work),
    }
    try:
        process = subprocess.Popen(
            wrapped, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, start_new_session=True,
        )
    except OSError as exc:
        raise DocumentIsolationError("Lokale Dokument-Isolation konnte nicht gestartet werden.") from exc
    output = _collect(process, timeout, max_bytes)
    if process.returncode != 0:
        raise ProcessFailed(argv[0])
    return output.decode("utf-8", errors="replace")
