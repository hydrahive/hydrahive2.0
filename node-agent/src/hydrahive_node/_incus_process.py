"""Bounded, cancellable execution of the fixed local Incus binary."""

from __future__ import annotations

import asyncio
from pathlib import Path

INCUS_BINARY = Path("/usr/bin/incus")
MAX_OUTPUT_BYTES = 64 * 1024
_CONCURRENCY = asyncio.Semaphore(2)


class IncusProcessError(RuntimeError):
    pass


async def _read_bounded(stream: asyncio.StreamReader) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await stream.read(8192)
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > MAX_OUTPUT_BYTES:
            raise IncusProcessError("incus output limit exceeded")
        chunks.append(chunk)


async def _terminate(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        process.kill()
    except ProcessLookupError:
        pass
    await process.wait()


async def run(*args: str, timeout: float = 60.0) -> tuple[int, str, str]:
    if not INCUS_BINARY.is_file():
        raise IncusProcessError("incus binary is unavailable")
    async with _CONCURRENCY:
        process = await asyncio.create_subprocess_exec(
            str(INCUS_BINARY),
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if process.stdout is None or process.stderr is None:  # pragma: no cover - asyncio contract
            await _terminate(process)
            raise IncusProcessError("incus output pipes are unavailable")
        try:
            stdout, stderr, _ = await asyncio.wait_for(
                asyncio.gather(_read_bounded(process.stdout), _read_bounded(process.stderr), process.wait()),
                timeout=timeout,
            )
        except BaseException:
            await _terminate(process)
            raise
        return process.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
