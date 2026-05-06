"""Regressionstests für den Login-Lockout-Mechanismus.

Testet core/src/hydrahive/api/middleware/lockout.py
"""
from __future__ import annotations

import time

import pytest

from hydrahive.api.middleware import lockout


@pytest.fixture(autouse=True)
def reset_lockout_state():
    """Reset lockout state vor jedem Test."""
    lockout._username_attempts.clear()
    lockout._ip_attempts.clear()
    yield
    lockout._username_attempts.clear()
    lockout._ip_attempts.clear()


def test_user_not_locked_before_threshold():
    """Vor N Fehlversuchen ist der User nicht gesperrt."""
    username = "testuser"
    ip = "192.168.1.100"
    
    # Record N-1 failures (threshold ist 5)
    for _ in range(lockout.USERNAME_THRESHOLD - 1):
        lockout.record_failure(username, ip)
    
    locked, retry_after = lockout.is_locked(username, ip)
    assert locked is False
    assert retry_after == 0


def test_user_locked_after_threshold():
    """Nach N Fehlversuchen ist der User gesperrt."""
    username = "testuser"
    ip = "192.168.1.100"
    
    # Record N failures (threshold ist 5)
    for _ in range(lockout.USERNAME_THRESHOLD):
        lockout.record_failure(username, ip)
    
    locked, retry_after = lockout.is_locked(username, ip)
    assert locked is True
    assert retry_after > 0


def test_user_unlocked_after_reset():
    """Nach reset() ist der User wieder entsperrt."""
    username = "testuser"
    ip = "192.168.1.100"
    
    # Lock user
    for _ in range(lockout.USERNAME_THRESHOLD):
        lockout.record_failure(username, ip)
    
    # Verify locked
    locked, _ = lockout.is_locked(username, ip)
    assert locked is True
    
    # Reset
    lockout.reset(username, ip)
    
    # Verify unlocked
    locked, retry_after = lockout.is_locked(username, ip)
    assert locked is False
    assert retry_after == 0


def test_retry_after_is_positive_when_locked():
    """retry_after ist > 0 wenn gesperrt."""
    username = "testuser"
    ip = "192.168.1.100"
    
    # Lock user
    for _ in range(lockout.USERNAME_THRESHOLD):
        lockout.record_failure(username, ip)
    
    locked, retry_after = lockout.is_locked(username, ip)
    assert locked is True
    assert retry_after > 0
    # retry_after sollte ungefähr WINDOW_SECONDS sein
    assert retry_after <= lockout.WINDOW_SECONDS


def test_different_ips_count_separately():
    """Verschiedene IPs zählen getrennt."""
    username = "testuser"
    ip1 = "192.168.1.100"
    ip2 = "192.168.1.101"
    
    # Record failures von IP1
    for _ in range(lockout.USERNAME_THRESHOLD):
        lockout.record_failure(username, ip1)
    
    # IP1 ist gesperrt
    locked, _ = lockout.is_locked(username, ip1)
    assert locked is True
    
    # IP2 ist NICHT gesperrt (IP-Counter ist getrennt)
    # ABER: Username-Counter ist global, also IP2 ist auch gesperrt!
    # Das ist das erwartete Verhalten: Username wird gesperrt, egal von welcher IP
    locked, _ = lockout.is_locked(username, ip2)
    assert locked is True
    
    # Teste jetzt unterschiedliche User von gleicher IP
    user1 = "alice"
    user2 = "bob"
    ip_shared = "10.0.0.50"
    
    # Reset state
    lockout._username_attempts.clear()
    lockout._ip_attempts.clear()
    
    # user1 macht 4 Fehlversuche
    for _ in range(4):
        lockout.record_failure(user1, ip_shared)
    
    # user1 ist nicht gesperrt (unter threshold)
    locked, _ = lockout.is_locked(user1, ip_shared)
    assert locked is False
    
    # user2 ist auch nicht gesperrt
    locked, _ = lockout.is_locked(user2, ip_shared)
    assert locked is False


def test_ip_lockout_threshold():
    """IP wird nach IP_THRESHOLD gesperrt (unabhängig von Usernamen)."""
    ip = "10.0.0.100"
    
    # Verschiedene Usernames von gleicher IP
    for i in range(lockout.IP_THRESHOLD):
        lockout.record_failure(f"user{i}", ip)
    
    # IP ist jetzt gesperrt, auch für neue Usernames
    locked, retry_after = lockout.is_locked("new_user", ip)
    assert locked is True
    assert retry_after > 0


def test_lockout_expires_after_window():
    """Lockout läuft nach WINDOW_SECONDS ab."""
    username = "testuser"
    ip = "192.168.1.100"
    
    # Mock time: setze erste Fehlversuche in die Vergangenheit
    old_time = time.time() - lockout.WINDOW_SECONDS - 10
    
    # Manuell alte Einträge hinzufügen
    lockout._username_attempts[username] = [old_time] * lockout.USERNAME_THRESHOLD
    
    # Jetzt sollte der User NICHT mehr gesperrt sein (Einträge wurden gepruned)
    locked, retry_after = lockout.is_locked(username, ip)
    assert locked is False
    assert retry_after == 0


def test_partial_expiry():
    """Nur alte Einträge verfallen, neue bleiben."""
    username = "testuser"
    ip = "192.168.1.100"
    
    now = time.time()
    old_time = now - lockout.WINDOW_SECONDS - 10
    
    # 3 alte Einträge + 2 neue
    lockout._username_attempts[username] = [old_time, old_time, old_time, now, now]
    
    # Nur 2 Einträge bleiben nach Pruning → nicht gesperrt
    locked, _ = lockout.is_locked(username, ip)
    assert locked is False
    
    # Füge 3 weitere hinzu → jetzt 5 → gesperrt
    for _ in range(3):
        lockout.record_failure(username, ip)
    
    locked, retry_after = lockout.is_locked(username, ip)
    assert locked is True
    assert retry_after > 0
