"""Tests für teamchat/identity.py — ensure_identity (TDD).

Lazy imports in jeder Testfunktion (settings.data_dir-Freeze-Gotcha).
Netzwerk vollständig gemockt. Echte DB + echte Krypto via tmp_path.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    """DB initialisieren + teamchat_identities nach jedem Test leeren."""
    from hydrahive.db import init_db
    from hydrahive.db.connection import db

    init_db()
    yield
    with db() as conn:
        conn.execute("DELETE FROM teamchat_identities")


def _make_account_tokens(user_id: str, access_token: str, device_id: str):
    from hydrahive.teamchat.client import AccountTokens
    return AccountTokens(user_id=user_id, access_token=access_token, device_id=device_id)


# ---------------------------------------------------------------------------
# Erster Aufruf → Provisioning via register_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_identity_first_call_provisions(monkeypatch, setup_test_env):
    """Erster Aufruf: register_account wird gerufen, Token verschlüsselt in DB gespeichert,
    Rückgabe ist der Klartext-Token."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "test-secret-key-for-jwt-signing")

    tokens = _make_account_tokens(
        user_id="@alice:test.local",
        access_token="syt_plaintext_token_abc123",
        device_id="DEVXYZ",
    )

    with patch(
        "hydrahive.teamchat.identity.client.register_account",
        new=AsyncMock(return_value=tokens),
    ):
        from hydrahive.teamchat.identity import ensure_identity
        result = await ensure_identity("alice")

    # Rückgabe ist der Klartext-Token
    assert result.access_token == "syt_plaintext_token_abc123"
    assert result.user_id == "@alice:test.local"
    assert result.device_id == "DEVXYZ"

    # DB-Eintrag vorhanden — Token muss verschlüsselt sein (enc:v1:-Präfix)
    from hydrahive.db import teamchat
    row = teamchat.get_identity("alice")
    assert row is not None
    assert row["access_token"].startswith("enc:v1:")
    assert row["access_token"] != "syt_plaintext_token_abc123"
    assert row["mxid"] == "@alice:test.local"
    assert row["device_id"] == "DEVXYZ"


# ---------------------------------------------------------------------------
# Zweiter Aufruf → idempotent, kein register_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_identity_second_call_idempotent(monkeypatch, setup_test_env):
    """Zweiter Aufruf: kein Netzwerk-Call, Token korrekt entschlüsselt."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "test-secret-key-for-jwt-signing")

    tokens = _make_account_tokens(
        user_id="@bob:test.local",
        access_token="syt_bob_token_xyz",
        device_id="DEVBOB",
    )

    mock_register = AsyncMock(return_value=tokens)
    with patch("hydrahive.teamchat.identity.client.register_account", new=mock_register):
        from hydrahive.teamchat.identity import ensure_identity
        first = await ensure_identity("bob")

    # Zweiter Aufruf — register_account darf NICHT nochmal gerufen werden
    mock_register2 = AsyncMock()
    with patch("hydrahive.teamchat.identity.client.register_account", new=mock_register2):
        second = await ensure_identity("bob")

    mock_register2.assert_not_awaited()
    assert second.access_token == "syt_bob_token_xyz"
    assert second.user_id == "@bob:test.local"


# ---------------------------------------------------------------------------
# AccountExistsError → login_password-Fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_identity_account_exists_falls_back_to_login(monkeypatch, setup_test_env):
    """register_account wirft AccountExistsError → login_password wird gerufen."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "test-secret-key-for-jwt-signing")

    from hydrahive.teamchat.client import AccountExistsError
    login_tokens = _make_account_tokens(
        user_id="@carol:test.local",
        access_token="syt_carol_from_login",
        device_id="DEVCAROL",
    )

    with (
        patch(
            "hydrahive.teamchat.identity.client.register_account",
            new=AsyncMock(side_effect=AccountExistsError("already exists")),
        ),
        patch(
            "hydrahive.teamchat.identity.client.login_password",
            new=AsyncMock(return_value=login_tokens),
        ),
    ):
        from hydrahive.teamchat.identity import ensure_identity
        result = await ensure_identity("carol")

    assert result.access_token == "syt_carol_from_login"
    assert result.user_id == "@carol:test.local"

    # login-Token muss auch verschlüsselt in DB landen
    from hydrahive.db import teamchat
    row = teamchat.get_identity("carol")
    assert row is not None
    assert row["access_token"].startswith("enc:v1:")


# ---------------------------------------------------------------------------
# Fehlerfälle: fehlende Konfiguration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_identity_raises_wenn_server_name_leer(monkeypatch, setup_test_env):
    """Leerer matrix_server_name → IdentityError."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "")
    monkeypatch.delenv("HH_MATRIX_SERVER_NAME", raising=False)
    # Sicherstellen, dass keine server_name-Datei existiert
    from hydrahive.settings import settings
    sn_file = settings.config_dir / "matrix" / "server_name"
    if sn_file.exists():
        sn_file.unlink()

    from hydrahive.teamchat.identity import ensure_identity, IdentityError
    with pytest.raises(IdentityError, match="server_name"):
        await ensure_identity("dave")


@pytest.mark.asyncio
async def test_ensure_identity_raises_wenn_reg_token_leer(monkeypatch, setup_test_env):
    """Leerer matrix_registration_token → IdentityError."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "")
    monkeypatch.delenv("HH_MATRIX_REGISTRATION_TOKEN", raising=False)

    from hydrahive.teamchat.identity import ensure_identity, IdentityError
    with pytest.raises(IdentityError, match="registration_token"):
        await ensure_identity("eve")


# ---------------------------------------------------------------------------
# Deterministisches Passwort
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Bot-Identität (Agent-Bots) — eigener Namensraum, gültiger localpart
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_bot_identity_provisions_with_bot_localpart(monkeypatch, setup_test_env):
    """Bot-Account: register mit localpart 'agent-buddy', DB-Key 'agent:buddy'."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "test-secret-key-for-jwt-signing")

    captured: list[str] = []

    async def capturing_register(homeserver, username, password, reg_token, *, device_name):
        captured.append(username)
        from hydrahive.teamchat.client import AccountTokens
        return AccountTokens(
            user_id=f"@{username}:test.local",
            access_token="syt_bot_token",
            device_id="DEVBOT",
        )

    with patch("hydrahive.teamchat.identity.client.register_account", new=capturing_register):
        from hydrahive.teamchat.identity import ensure_bot_identity
        result = await ensure_bot_identity("buddy")

    # Matrix-localpart ist bot-präfixiert
    assert captured == ["agent-buddy"]
    assert result.user_id == "@agent-buddy:test.local"
    assert result.access_token == "syt_bot_token"

    # DB-Eintrag unter eigenem Namensraum-Key, Token verschlüsselt
    from hydrahive.db import teamchat
    row = teamchat.get_identity("agent:buddy")
    assert row is not None
    assert row["access_token"].startswith("enc:v1:")
    assert row["mxid"] == "@agent-buddy:test.local"


@pytest.mark.asyncio
async def test_ensure_bot_identity_idempotent(monkeypatch, setup_test_env):
    """Zweiter Aufruf: kein erneutes register."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "test-secret-key-for-jwt-signing")

    tokens = _make_account_tokens("@agent-buddy:test.local", "syt_x", "DEV")
    with patch("hydrahive.teamchat.identity.client.register_account", new=AsyncMock(return_value=tokens)):
        from hydrahive.teamchat.identity import ensure_bot_identity
        await ensure_bot_identity("buddy")

    mock_register2 = AsyncMock()
    with patch("hydrahive.teamchat.identity.client.register_account", new=mock_register2):
        second = await ensure_bot_identity("buddy")

    mock_register2.assert_not_awaited()
    assert second.access_token == "syt_x"


@pytest.mark.asyncio
async def test_ensure_bot_identity_localpart_sanitized(monkeypatch, setup_test_env):
    """Großschreibung/ungültige Zeichen im agent_id → gültiger localpart."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "test-secret-key-for-jwt-signing")

    captured: list[str] = []

    async def capturing_register(homeserver, username, password, reg_token, *, device_name):
        captured.append(username)
        from hydrahive.teamchat.client import AccountTokens
        return AccountTokens(user_id=f"@{username}:test.local", access_token="t", device_id="D")

    with patch("hydrahive.teamchat.identity.client.register_account", new=capturing_register):
        from hydrahive.teamchat.identity import ensure_bot_identity
        await ensure_bot_identity("Sales Bot#1")

    localpart = captured[0]
    assert localpart.startswith("agent-")
    # nur erlaubte Matrix-localpart-Zeichen
    assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789._=/-" for c in localpart)


@pytest.mark.asyncio
async def test_bot_identity_namespace_separate_from_human(monkeypatch, setup_test_env):
    """Mensch 'buddy' und Bot 'buddy' sind getrennte Accounts."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "test-secret-key-for-jwt-signing")

    async def reg(homeserver, username, password, reg_token, *, device_name):
        from hydrahive.teamchat.client import AccountTokens
        return AccountTokens(user_id=f"@{username}:test.local", access_token=f"tok_{username}", device_id="D")

    with patch("hydrahive.teamchat.identity.client.register_account", new=reg):
        from hydrahive.teamchat.identity import ensure_identity, ensure_bot_identity
        human = await ensure_identity("buddy")
        bot = await ensure_bot_identity("buddy")

    assert human.user_id == "@buddy:test.local"
    assert bot.user_id == "@agent-buddy:test.local"

    from hydrahive.db import teamchat
    assert teamchat.get_identity("buddy") is not None
    assert teamchat.get_identity("agent:buddy") is not None


@pytest.mark.asyncio
async def test_ensure_identity_deterministic_password(monkeypatch, setup_test_env):
    """Passwort muss deterministisch und 32 Hex-Zeichen sein."""
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    monkeypatch.setenv("HH_MATRIX_HOMESERVER_URL", "http://127.0.0.1:6167")
    monkeypatch.setenv("HH_MATRIX_REGISTRATION_TOKEN", "reg-token-test")
    monkeypatch.setenv("HH_SECRET_KEY", "stable-server-secret-key")

    captured_passwords: list[str] = []

    async def capturing_register(homeserver, username, password, reg_token, *, device_name):
        captured_passwords.append(password)
        from hydrahive.teamchat.client import AccountTokens
        return AccountTokens(
            user_id=f"@{username}:test.local",
            access_token=f"tok_{username}",
            device_id="DEV",
        )

    with patch("hydrahive.teamchat.identity.client.register_account", new=capturing_register):
        from hydrahive.teamchat.identity import ensure_identity
        await ensure_identity("frank")

    assert len(captured_passwords) == 1
    pw = captured_passwords[0]
    # Muss 32 Hex-Zeichen sein
    assert len(pw) == 32
    assert all(c in "0123456789abcdef" for c in pw)

    # Gleiche Ableitung bei zweitem Durchlauf (DB reset → provision erneut)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("DELETE FROM teamchat_identities")

    captured_passwords.clear()
    with patch("hydrahive.teamchat.identity.client.register_account", new=capturing_register):
        await ensure_identity("frank")

    assert len(captured_passwords) == 1
    assert captured_passwords[0] == pw  # identisches Passwort
