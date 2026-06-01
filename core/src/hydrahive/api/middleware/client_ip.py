"""Client-IP-Ermittlung hinter optionalem Reverse-Proxy.

X-Forwarded-For wird NUR berücksichtigt, wenn der direkte Peer ein vertrauens-
würdiger Proxy (Loopback) ist — sonst könnte ein Client den Header spoofen und
IP-basierte Limits/Lockouts umgehen.
"""
from __future__ import annotations

from fastapi import Request

TRUSTED_PROXIES = frozenset({"127.0.0.1", "::1"})


def client_ip(request: Request) -> str:
    direct = request.client.host if request.client else "?"
    if direct in TRUSTED_PROXIES:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return direct
