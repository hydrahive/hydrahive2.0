"""Tailscale Admin API: API-Key speichern + Pre-Auth-Keys (Invites) erzeugen.

Storage: <config_dir>/tailscale-admin.json mit chmod 0600. Enthält
{api_key, tailnet} — niemals an Frontend zurückgeben (nur configured-Flag).

Invite-Mechanik: Tailscale Admin-API POST /tailnet/<tn>/keys mit
preauthorized=True, reusable=False, ephemeral=False, expirySeconds=86400.
Reicht den 'key' aus der Response 1:1 ans Frontend durch. Der Empfänger-
Server nutzt ihn dann als `tailscale up --authkey=...`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

TS_API_BASE = "https://api.tailscale.com/api/v2"
INVITE_EXPIRY_S = 24 * 3600  # 24h


def _config_path():
    return settings.config_dir / "tailscale-admin.json"


def load_admin_config() -> dict:
    """Returnt {api_key, tailnet} oder {} wenn keine Config existiert."""
    try:
        return json.loads(_config_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_admin_config(api_key: str, tailnet: str) -> None:
    """Schreibt Config atomar mit chmod 0600. Anrufer prüft Validität vorher."""
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"api_key": api_key, "tailnet": tailnet}), encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(p)


def is_configured() -> bool:
    cfg = load_admin_config()
    return bool(cfg.get("api_key"))


def public_config() -> dict:
    """Frontend-safe Snapshot — kein api_key drin."""
    cfg = load_admin_config()
    return {
        "configured": bool(cfg.get("api_key")),
        "tailnet": cfg.get("tailnet", "-"),
    }


def _ts_api_sync(path: str, api_key: str, *, method: str = "GET", body: bytes | None = None,
                 timeout: int = 15) -> dict:
    """Sync Tailscale-API-Call. Wirft urllib.error.HTTPError bei 4xx/5xx."""
    req = urllib.request.Request(
        f"{TS_API_BASE}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


async def validate_api_key(api_key: str, tailnet: str) -> tuple[bool, str]:
    """Probiert GET /tailnet/<tn>/devices?fields=id. True wenn 200, sonst (False, Fehler)."""
    try:
        await asyncio.to_thread(
            _ts_api_sync, f"/tailnet/{tailnet}/devices?fields=id", api_key, timeout=10
        )
        return True, ""
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


async def create_invite() -> dict:
    """Erzeugt einen 24h-Single-Use-Pre-Auth-Key. Wirft RuntimeError bei API-Fehler."""
    cfg = load_admin_config()
    api_key = cfg.get("api_key")
    if not api_key:
        raise RuntimeError("tailscale_admin_not_configured")
    tailnet = cfg.get("tailnet", "-")

    payload = json.dumps({
        "capabilities": {
            "devices": {
                "create": {
                    "reusable": False,
                    "ephemeral": False,
                    "preauthorized": True,
                }
            }
        },
        "expirySeconds": INVITE_EXPIRY_S,
    }).encode()

    try:
        data = await asyncio.to_thread(
            _ts_api_sync, f"/tailnet/{tailnet}/keys", api_key,
            method="POST", body=payload,
        )
    except urllib.error.HTTPError as e:
        logger.warning("Tailscale-API: %s %s", e.code, e.reason)
        raise RuntimeError(f"tailscale_api_http_{e.code}")
    except Exception as e:
        logger.warning("Tailscale-API: %s", e)
        raise RuntimeError("tailscale_api_unreachable")

    return {
        "auth_key": data.get("key", ""),
        "expires": data.get("expires", ""),
        "id": data.get("id", ""),
    }
