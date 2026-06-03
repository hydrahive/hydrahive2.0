"""teamchat/client.py — low-level Matrix homeserver transport.

Speaks Matrix via matrix-nio (login/client) and httpx (register UIAA).
Knows nothing about HydraHive users, the DB, or encryption.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from nio import AsyncClient, LoginResponse, LoginError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MatrixClientError(Exception):
    """Base class for all Matrix-client errors."""


class AccountExistsError(MatrixClientError):
    """Raised when registration fails because the account already exists."""


class RegistrationError(MatrixClientError):
    """Raised when registration fails for any reason other than account-exists."""


class LoginFailedError(MatrixClientError):
    """Raised when password-login is rejected by the homeserver."""


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountTokens:
    """Immutable authentication credential bundle returned after register/login."""

    user_id: str        # full MXID, e.g. "@till:masternode.hydrahive.org"
    access_token: str
    device_id: str | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def register_account(
    homeserver_url: str,
    username: str,
    password: str,
    registration_token: str,
    *,
    device_name: str = "hydrahive",
) -> AccountTokens:
    """Register a new Matrix account using the UIAA registration_token flow.

    Two-step flow (mirrors HH1 matrix_agent.py:248-313, httpx instead of aiohttp):
    1. POST without auth — if `access_token` already present, done.
       If ``M_USER_IN_USE`` → raise AccountExistsError.
       Otherwise grab the UIAA ``session`` id.
    2. POST again with ``m.login.registration_token`` auth block.
       Expect ``access_token`` in the response; raise RegistrationError if absent.
    """
    register_url = f"{homeserver_url.rstrip('/')}/_matrix/client/v3/register"
    base_body = {
        "username": username,
        "password": password,
        "initial_device_display_name": device_name,
        "inhibit_login": False,
    }

    async with httpx.AsyncClient() as http:
        # Step 1: probe / get UIAA session
        resp1 = await http.post(register_url, json=base_body)
        d1: dict = resp1.json()
        # Body NICHT loggen — er kann im No-UIAA-Fall einen access_token enthalten.
        logger.debug(
            "register step-1: status=%s has_token=%s has_session=%s",
            resp1.status_code, "access_token" in d1, "session" in d1,
        )

        if "access_token" in d1:
            # No UIAA required — homeserver accepted the request directly.
            logger.info("register: no UIAA needed for user=%s", username)
            return _tokens_from_dict(d1)

        if d1.get("errcode") == "M_USER_IN_USE":
            raise AccountExistsError(
                f"Matrix account already exists for username={username!r}"
            )

        uiaa_session = d1.get("session")
        if not uiaa_session:
            raise RegistrationError(
                f"Registration step-1 returned no UIAA session "
                f"and no access_token: {d1!r}"
            )

        # Step 2: authenticate with registration token
        auth_block = {
            "type": "m.login.registration_token",
            "token": registration_token,
            "session": uiaa_session,
        }
        step2_body = {**base_body, "auth": auth_block}
        resp2 = await http.post(register_url, json=step2_body)
        d2: dict = resp2.json()
        # Body NICHT loggen — er enthält bei Erfolg den access_token.
        logger.debug(
            "register step-2: status=%s has_token=%s",
            resp2.status_code, "access_token" in d2,
        )

        if "access_token" not in d2:
            raise RegistrationError(
                f"Registration step-2 did not return an access_token: {d2!r}"
            )

        logger.info("register: account created for user=%s", username)
        return _tokens_from_dict(d2)


async def login_password(
    homeserver_url: str,
    username: str,
    password: str,
    *,
    device_name: str = "hydrahive",
) -> AccountTokens:
    """Log in an existing Matrix account with a password.

    Always calls ``close()`` on the transient nio client (in a finally block).
    Raises LoginFailedError on LoginError response.
    """
    client = AsyncClient(homeserver_url, username)
    try:
        resp = await client.login(password=password, device_name=device_name)
        if isinstance(resp, LoginResponse):
            logger.info("login: success for user=%s", username)
            return AccountTokens(
                user_id=resp.user_id,
                access_token=resp.access_token,
                device_id=resp.device_id,
            )
        # Any non-LoginResponse (LoginError or similar) is a failure.
        raise LoginFailedError(
            f"Login failed for {username!r}: {resp!r}"
        )
    finally:
        await client.close()


def build_client(
    homeserver_url: str,
    user_id: str,
    access_token: str,
    device_id: str | None = None,
) -> AsyncClient:
    """Construct an authenticated AsyncClient.

    The caller owns the lifecycle — must call ``await client.close()`` when done.
    Does NOT perform any network I/O.
    """
    client = AsyncClient(homeserver_url, user_id, device_id or "")
    client.access_token = access_token
    client.user_id = user_id
    if device_id:
        client.device_id = device_id
    logger.debug("build_client: created client for user_id=%s", user_id)
    return client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tokens_from_dict(d: dict) -> AccountTokens:
    try:
        return AccountTokens(
            user_id=d["user_id"],
            access_token=d["access_token"],
            device_id=d.get("device_id"),
        )
    except KeyError as e:
        raise RegistrationError(f"Matrix-Response fehlt Pflichtfeld {e}") from e
