"""Regressionstests für Session-Ownership-Logik in HydraHive2.

Testet die Funktion `check_owner` in:
core/src/hydrahive/api/routes/_sessions_helpers.py

Sie wirft HTTP 403 "session_no_access" wenn:
- role != "admin" UND session.user_id != username

Diese Tests können mit pytest ODER direkt mit Python ausgeführt werden:
  python test_session_ownership.py
  pytest test_session_ownership.py -v
"""

from types import SimpleNamespace

from fastapi import status

from hydrahive.api.routes._sessions_helpers import check_owner


def test_owner_darf_auf_eigene_session_zugreifen():
    """Owner darf auf eigene Session zugreifen (kein Fehler)."""
    session = SimpleNamespace(user_id="alice", id="session-1")
    # Sollte keine Exception werfen
    check_owner(session, username="alice", role="user")
    print("✓ test_owner_darf_auf_eigene_session_zugreifen")


def test_admin_darf_auf_fremde_session_zugreifen():
    """Admin darf auf fremde Session zugreifen (kein Fehler)."""
    session = SimpleNamespace(user_id="alice", id="session-1")
    # Admin darf auf alice's Session zugreifen
    check_owner(session, username="bob", role="admin")
    print("✓ test_admin_darf_auf_fremde_session_zugreifen")


def test_fremder_user_ohne_admin_403():
    """Fremder User ohne Admin → 403."""
    session = SimpleNamespace(user_id="alice", id="session-1")
    
    try:
        check_owner(session, username="bob", role="user")
        raise AssertionError("Expected HTTP 403, but no exception was raised")
    except Exception as exc:
        # Prüfe dass es die richtige Exception ist
        assert exc.status_code == status.HTTP_403_FORBIDDEN, \
            f"Expected status 403, got {exc.status_code}"
        assert exc.detail["code"] == "session_no_access", \
            f"Expected code 'session_no_access', got {exc.detail.get('code')}"
    
    print("✓ test_fremder_user_ohne_admin_403")


def test_admin_mit_eigener_session_kein_fehler():
    """Admin mit eigener Session → kein Fehler."""
    session = SimpleNamespace(user_id="alice", id="session-1")
    # Admin greift auf eigene Session zu
    check_owner(session, username="alice", role="admin")
    print("✓ test_admin_mit_eigener_session_kein_fehler")


def test_leerer_username_403():
    """Leerer Username → 403."""
    session = SimpleNamespace(user_id="alice", id="session-1")
    
    try:
        check_owner(session, username="", role="user")
        raise AssertionError("Expected HTTP 403, but no exception was raised")
    except Exception as exc:
        assert exc.status_code == status.HTTP_403_FORBIDDEN, \
            f"Expected status 403, got {exc.status_code}"
        assert exc.detail["code"] == "session_no_access", \
            f"Expected code 'session_no_access', got {exc.detail.get('code')}"
    
    print("✓ test_leerer_username_403")


def test_none_username_403():
    """None als Username → 403 (Edge-Case)."""
    session = SimpleNamespace(user_id="alice", id="session-1")
    
    try:
        check_owner(session, username=None, role="user")
        raise AssertionError("Expected HTTP 403, but no exception was raised")
    except Exception as exc:
        assert exc.status_code == status.HTTP_403_FORBIDDEN, \
            f"Expected status 403, got {exc.status_code}"
        assert exc.detail["code"] == "session_no_access", \
            f"Expected code 'session_no_access', got {exc.detail.get('code')}"
    
    print("✓ test_none_username_403")


def run_all_tests():
    """Führe alle Tests aus."""
    print("\n=== Session Ownership Tests ===\n")
    
    tests = [
        test_owner_darf_auf_eigene_session_zugreifen,
        test_admin_darf_auf_fremde_session_zugreifen,
        test_fremder_user_ohne_admin_403,
        test_admin_mit_eigener_session_kein_fehler,
        test_leerer_username_403,
        test_none_username_403,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*40}")
    print(f"Tests: {len(tests)} | Passed: {len(tests) - failed} | Failed: {failed}")
    print(f"{'='*40}\n")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
