from __future__ import annotations

import asyncio


async def _run(*args: str, timeout: float = 30) -> str:
    proc = await asyncio.create_subprocess_exec(
        "sudo", "-n", "tailscale", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip() or f"tailscale {args[0]} fehlgeschlagen")
    return stdout.decode().strip()


async def up(authkey: str) -> None:
    await _run("up", f"--authkey={authkey}", "--accept-routes")


async def logout() -> None:
    await _run("logout", timeout=10)
