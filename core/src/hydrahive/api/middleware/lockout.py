"""Brute-Force-Schutz für /api/auth/login.

In-Memory Counter pro Username und pro IP. Beide werden separat gepflegt:
- Username, weil so der Hauptangriff geht (wenn Angreifer einen User kennt)
- IP, weil Angreifer sonst einfach über alle User durchprobieren kann

Limits sind konservativ (echte User tippen sich selten 5x in 15 Min vertippen).
Reset bei Backend-Restart ist akzeptabel — Angreifer-IPs würden eh wechseln,
und einen kurzen Restart-Loop kann der Sysadmin sehen.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

WINDOW_SECONDS = 15 * 60
USERNAME_THRESHOLD = 5
IP_THRESHOLD = 20

_lock = Lock()
_username_attempts: dict[str, list[float]] = defaultdict(list)
_ip_attempts: dict[str, list[float]] = defaultdict(list)


def _prune(entries: list[float], now: float) -> list[float]:
    cutoff = now - WINDOW_SECONDS
    return [t for t in entries if t > cutoff]


def is_locked(username: str, ip: str) -> tuple[bool, int]:
    """Returns (locked, retry_after_seconds). 0 if not locked."""
    now = time.time()
    with _lock:
        u_entries = _prune(_username_attempts[username], now)
        _username_attempts[username] = u_entries
        i_entries = _prune(_ip_attempts[ip], now)
        _ip_attempts[ip] = i_entries
        if len(u_entries) >= USERNAME_THRESHOLD:
            return True, int(u_entries[0] + WINDOW_SECONDS - now)
        if len(i_entries) >= IP_THRESHOLD:
            return True, int(i_entries[0] + WINDOW_SECONDS - now)
    return False, 0


def record_failure(username: str, ip: str) -> None:
    now = time.time()
    with _lock:
        _username_attempts[username].append(now)
        _ip_attempts[ip].append(now)


def reset(username: str, ip: str) -> None:
    """Clears counters after a successful login."""
    with _lock:
        _username_attempts.pop(username, None)
        _ip_attempts.pop(ip, None)
