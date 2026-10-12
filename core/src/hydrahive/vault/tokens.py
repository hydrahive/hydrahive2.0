"""Vault-Token (docs/specs/vault.md §4.3).

Kurzlebig und gleitend: nach ``IDLE_SECONDS`` ohne Vault-Anfrage ungültig, spätestens ``MAX_SECONDS`` nach dem
Entsperren. Gebunden an user_id und PIN-generation (Reset/Änderung macht alle Tokens ungültig). Signiert mit dem
Server-Schlüssel (HMAC-SHA256), Format ``<payload_b64>.<sig_b64>``. Getrennt vom Login-Token (eigener Header).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

from hydrahive.settings import settings

IDLE_SECONDS = 15 * 60
MAX_SECONDS = 8 * 60 * 60
_CONTEXT = b"hydrahive-vault-v1"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sig(payload: str) -> str:
    key = hmac.new(settings.secret_key.encode(), _CONTEXT, hashlib.sha256).digest()
    return _b64(hmac.new(key, payload.encode(), hashlib.sha256).digest())


def _encode(data: dict) -> str:
    payload = _b64(json.dumps(data, separators=(",", ":"), sort_keys=True).encode())
    return f"{payload}.{_sig(payload)}"


def _decode(token: object) -> dict | None:
    if not isinstance(token, str) or token.count(".") != 1:
        return None
    payload, sig = token.split(".")
    if not hmac.compare_digest(sig, _sig(payload)):
        return None
    try:
        data = json.loads(_unb64(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def issue(user_id: str, *, generation: int, now: float) -> str:
    return _encode({"uid": user_id, "gen": generation, "iat": now, "last": now})


def _valid(data: dict | None, user_id: str, generation: int, now: float) -> bool:
    if not data or data.get("uid") != user_id or data.get("gen") != generation:
        return False
    try:
        iat, last = float(data["iat"]), float(data["last"])
    except (KeyError, TypeError, ValueError):
        return False
    return now - last <= IDLE_SECONDS and now - iat <= MAX_SECONDS


def check(token: object, user_id: str, *, generation: int, now: float) -> bool:
    return _valid(_decode(token), user_id, generation, now)


def refresh(token: object, user_id: str, *, generation: int, now: float) -> str | None:
    """Gültigen Token verlängern (neues ``last``). None, wenn er nicht mehr gilt."""
    data = _decode(token)
    if not _valid(data, user_id, generation, now):
        return None
    return _encode({**data, "last": now})


def remaining(token: object, user_id: str, *, generation: int, now: float) -> int:
    """Sekunden bis zur Sperre (0 = gesperrt)."""
    data = _decode(token)
    if not _valid(data, user_id, generation, now):
        return 0
    return int(min(IDLE_SECONDS - (now - float(data["last"])), MAX_SECONDS - (now - float(data["iat"]))))
