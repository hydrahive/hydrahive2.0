"""PTY-Bridge zwischen `incus exec` und einem WebSocket.

Wir öffnen ein PTY-Paar, starten `incus exec <name> -- bash` als Subprocess
mit dem Slave-Side als stdin/stdout/stderr, und routen Bytes zwischen
WebSocket und Master-FD.
"""
from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import pty
import shutil
import struct
import termios

logger = logging.getLogger(__name__)


class ConsoleSession:
    """Lebenszyklus einer PTY-Session — start, write, resize, stop."""

    def __init__(self, name: str):
        self.name = name
        self._master_fd: int | None = None
        self._proc: asyncio.subprocess.Process | None = None
        self._loop = asyncio.get_event_loop()
        self._on_output: callable | None = None
        self._on_exit: callable | None = None

    async def start(self, on_output, on_exit) -> None:
        if shutil.which("incus") is None:
            raise RuntimeError("incus_missing")

        self._on_output = on_output
        self._on_exit = on_exit

        master, slave = pty.openpty()
        # Sinnvolle Default-Größe — der Client schickt ggf. ein resize().
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))

        self._proc = await asyncio.create_subprocess_exec(
            "incus", "exec", self.name,
            "--mode=interactive", "--", "bash",
            stdin=slave, stdout=slave, stderr=slave,
            start_new_session=True,
        )
        os.close(slave)
        self._master_fd = master

        self._loop.add_reader(master, self._on_master_readable)
        # Hintergrund-Task der auf den Prozess-Exit wartet
        asyncio.create_task(self._watch_exit())

    def _on_master_readable(self) -> None:
        if self._master_fd is None:
            return
        try:
            data = os.read(self._master_fd, 4096)
        except OSError:
            self._cleanup_reader()
            return
        if not data:
            self._cleanup_reader()
            return
        if self._on_output:
            asyncio.create_task(self._on_output(data))

    def _cleanup_reader(self) -> None:
        if self._master_fd is not None:
            try:
                self._loop.remove_reader(self._master_fd)
            except (ValueError, OSError):
                pass

    async def _watch_exit(self) -> None:
        if not self._proc:
            return
        await self._proc.wait()
        if self._on_exit:
            try:
                await self._on_exit()
            except Exception as e:
                logger.debug("on_exit-Callback fehlgeschlagen: %s", e)

    def write(self, data: bytes) -> None:
        if self._master_fd is None:
            return
        try:
            os.write(self._master_fd, data)
        except OSError:
            pass

    def resize(self, rows: int, cols: int) -> None:
        if self._master_fd is None:
            return
        try:
            fcntl.ioctl(
                self._master_fd, termios.TIOCSWINSZ,
                struct.pack("HHHH", rows, cols, 0, 0),
            )
        except OSError:
            pass

    async def stop(self) -> None:
        self._cleanup_reader()
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                try:
                    self._proc.kill()
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
