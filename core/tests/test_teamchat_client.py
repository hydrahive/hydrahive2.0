"""Tests for teamchat/client.py — matrix-nio client wrapper.

Network is fully mocked: httpx for register, nio.AsyncClient for login.
Import lazily inside test functions to avoid settings.data_dir freeze (project gotcha).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_httpx_response(json_data: dict, status_code: int = 200):
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


def _make_login_response(user_id: str, access_token: str, device_id: str):
    """Build a mock nio LoginResponse."""
    from nio import LoginResponse
    resp = MagicMock(spec=LoginResponse)
    resp.user_id = user_id
    resp.access_token = access_token
    resp.device_id = device_id
    return resp


def _make_login_error(message: str = "Wrong password"):
    """Build a mock nio LoginError."""
    from nio import LoginError
    err = MagicMock(spec=LoginError)
    err.message = message
    return err


# ---------------------------------------------------------------------------
# register_account — happy path: two-step UIAA
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_account_uiaa_two_step():
    """First POST returns {session}, second POST returns tokens → AccountTokens."""
    from hydrahive.teamchat.client import register_account, AccountTokens

    step1_data = {"session": "sess-abc", "flows": [{"stages": ["m.login.registration_token"]}]}
    step2_data = {
        "access_token": "tok_xyz",
        "user_id": "@alice:example.org",
        "device_id": "DEV1",
    }

    mock_post = AsyncMock(side_effect=[
        _make_httpx_response(step1_data, 401),
        _make_httpx_response(step2_data, 200),
    ])

    mock_http_client = AsyncMock()
    mock_http_client.post = mock_post
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        result = await register_account(
            "https://example.org",
            "alice",
            "s3cr3t",
            "reg-token-123",
        )

    assert isinstance(result, AccountTokens)
    assert result.user_id == "@alice:example.org"
    assert result.access_token == "tok_xyz"
    assert result.device_id == "DEV1"

    # Second call must carry the UIAA auth block with the session
    assert mock_post.call_count == 2
    body = mock_post.call_args_list[1].kwargs["json"]
    auth = body["auth"]
    assert auth["type"] == "m.login.registration_token"
    assert auth["token"] == "reg-token-123"
    assert auth["session"] == "sess-abc"

    # device_name wird als initial_device_display_name gesendet (Default "hydrahive")
    first_body = mock_post.call_args_list[0].kwargs["json"]
    assert first_body["initial_device_display_name"] == "hydrahive"


# ---------------------------------------------------------------------------
# register_account — first POST already returns access_token (no UIAA)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_account_no_uiaa_direct():
    """First POST already has access_token → returns tokens, no second call."""
    from hydrahive.teamchat.client import register_account, AccountTokens

    direct_data = {
        "access_token": "tok_direct",
        "user_id": "@bob:example.org",
        "device_id": "DEVDIRECT",
    }

    mock_post = AsyncMock(return_value=_make_httpx_response(direct_data, 200))
    mock_http_client = AsyncMock()
    mock_http_client.post = mock_post
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        result = await register_account(
            "https://example.org",
            "bob",
            "pass",
            "reg-token",
        )

    assert result.user_id == "@bob:example.org"
    assert result.access_token == "tok_direct"
    assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# register_account — M_USER_IN_USE → AccountExistsError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_account_user_in_use():
    """M_USER_IN_USE → AccountExistsError raised."""
    from hydrahive.teamchat.client import register_account, AccountExistsError

    in_use_data = {"errcode": "M_USER_IN_USE", "error": "User already registered"}

    mock_post = AsyncMock(return_value=_make_httpx_response(in_use_data, 400))
    mock_http_client = AsyncMock()
    mock_http_client.post = mock_post
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        with pytest.raises(AccountExistsError):
            await register_account("https://example.org", "alice", "pass", "tok")


# ---------------------------------------------------------------------------
# register_account — final response lacks access_token → RegistrationError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_account_missing_access_token():
    """Second POST response lacks access_token → RegistrationError."""
    from hydrahive.teamchat.client import register_account, RegistrationError

    step1_data = {"session": "sess-abc"}
    step2_data = {"errcode": "M_FORBIDDEN", "error": "Bad token"}

    mock_post = AsyncMock(side_effect=[
        _make_httpx_response(step1_data, 401),
        _make_httpx_response(step2_data, 403),
    ])
    mock_http_client = AsyncMock()
    mock_http_client.post = mock_post
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        with pytest.raises(RegistrationError):
            await register_account("https://example.org", "alice", "pass", "bad-tok")


# ---------------------------------------------------------------------------
# login_password — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_password_happy_path():
    """login_password returns correct AccountTokens and close() is awaited."""
    from hydrahive.teamchat.client import login_password, AccountTokens
    from nio import LoginResponse

    login_resp = _make_login_response(
        user_id="@carol:example.org",
        access_token="tok_carol",
        device_id="DEVCAROL",
    )

    mock_nio_client = AsyncMock()
    mock_nio_client.login = AsyncMock(return_value=login_resp)
    mock_nio_client.close = AsyncMock()

    with patch("hydrahive.teamchat.client.AsyncClient", return_value=mock_nio_client):
        result = await login_password("https://example.org", "carol", "pass123")

    assert isinstance(result, AccountTokens)
    assert result.user_id == "@carol:example.org"
    assert result.access_token == "tok_carol"
    assert result.device_id == "DEVCAROL"

    # close() must have been called (finally block)
    mock_nio_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# login_password — LoginError → LoginFailedError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_password_login_error():
    """login_password raises LoginFailedError on LoginError response."""
    from hydrahive.teamchat.client import login_password, LoginFailedError
    from nio import LoginError

    login_err = _make_login_error("Invalid credentials")

    mock_nio_client = AsyncMock()
    mock_nio_client.login = AsyncMock(return_value=login_err)
    mock_nio_client.close = AsyncMock()

    with patch("hydrahive.teamchat.client.AsyncClient", return_value=mock_nio_client):
        with pytest.raises(LoginFailedError):
            await login_password("https://example.org", "carol", "wrongpass")

    # close() must still be called even on error
    mock_nio_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# build_client — returns AsyncClient with tokens set, no network
# ---------------------------------------------------------------------------

def test_build_client_sets_tokens():
    """build_client returns AsyncClient with access_token and user_id set."""
    from hydrahive.teamchat.client import build_client
    from nio import AsyncClient

    client = build_client(
        homeserver_url="https://example.org",
        user_id="@dave:example.org",
        access_token="tok_dave",
        device_id="DEVDAVE",
    )

    assert isinstance(client, AsyncClient)
    assert client.access_token == "tok_dave"
    assert client.user_id == "@dave:example.org"
    # device_id may be stored on the client object
    assert client.device_id == "DEVDAVE"
