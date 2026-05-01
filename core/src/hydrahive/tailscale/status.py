from __future__ import annotations

import asyncio
import json
import logging
import shutil

logger = logging.getLogger(__name__)


def _tailscale_bin() -> str:
    return shutil.which("tailscale") or "/usr/bin/tailscale"


async def _run(*args: str, timeout: float = 5) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        _tailscale_bin(), *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return proc.returncode, stdout.decode(), stderr.decode()


async def get_status() -> dict:
    try:
        rc, out, err = await _run("status", "--json")
        if rc != 0:
            return {"installed": True, "connected": False, "error": err.strip()}
        data = json.loads(out)
        self_info = data.get("Self", {})
        ips = data.get("TailscaleIPs", [])
        ipv4 = next((ip for ip in ips if ":" not in ip), None)
        hostname = self_info.get("HostName", "")
        dns_name = self_info.get("DNSName", "").rstrip(".")
        tailnet = dns_name[len(hostname) + 1:] if hostname and dns_name.startswith(hostname) else ""
        backend_state = data.get("BackendState", "")
        return {
            "installed": True,
            "connected": backend_state == "Running",
            "backend_state": backend_state,
            "ip": ipv4,
            "hostname": hostname,
            "dns_name": dns_name,
            "tailnet": tailnet,
            "auth_url": data.get("AuthURL", "") or None,
        }
    except FileNotFoundError:
        return {"installed": False, "connected": False}
    except Exception as e:
        logger.warning("tailscale status fehlgeschlagen: %s", e)
        return {"installed": True, "connected": False, "error": str(e)}
