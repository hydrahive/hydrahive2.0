"""teamchat/identity.py — HydraHive-User/Agent ↔ Matrix-Account-Provisioning.

ensure_identity(user_id)      → Matrix-Account für einen menschlichen User.
ensure_bot_identity(agent_id) → eigener Bot-Account für einen Agenten.

Beide idempotent: vorhandene Identität zurückgeben oder neu anlegen
(register → falls AccountExistsError: login). Passwörter sind deterministisch
(sha256(localpart:server_secret)[:32]) damit Re-Login nach DB-Verlust ohne
erneute Registrierung funktioniert.

DB-Key vs. Matrix-localpart: für Menschen identisch (user_id). Für Bots getrennt
— DB-Key `agent:{id}` (kollisionsfrei zum Menschen-Namensraum), localpart
`agent-{id}` (Matrix erlaubt nur [a-z0-9._=/-]).
"""
from __future__ import annotations

import hashlib
import logging
import re

from hydrahive.credentials._crypto import decrypt, encrypt
from hydrahive.db import teamchat as db_teamchat
from hydrahive.teamchat import client
from hydrahive.teamchat.client import AccountExistsError, AccountTokens

logger = logging.getLogger(__name__)

# Matrix-localpart-Grammatik (Client-Server-Spec): erlaubte Zeichen.
_LOCALPART_ALLOWED = re.compile(r"[^a-z0-9._=/-]")


class IdentityError(Exception):
    """Wird geworfen wenn Matrix-Provisioning wegen fehlender Konfiguration scheitert."""


def _derive_password(localpart: str, server_secret: str) -> str:
    """Deterministisches Passwort: sha256(localpart:server_secret)[:32] (Hex)."""
    return hashlib.sha256(f"{localpart}:{server_secret}".encode()).hexdigest()[:32]


def _bot_localpart(agent_id: str) -> str:
    """Gültiger Matrix-localpart für einen Agenten-Bot: 'agent-<sanitisiert>'."""
    slug = _LOCALPART_ALLOWED.sub("-", agent_id.lower())
    return f"agent-{slug}"


async def ensure_identity(user_id: str) -> AccountTokens:
    """Gibt die Matrix-Identität für einen menschlichen HydraHive-User zurück."""
    return await _ensure_account(db_key=user_id, localpart=user_id)


async def ensure_bot_identity(agent_id: str) -> AccountTokens:
    """Gibt die Matrix-Identität für einen Agenten-Bot zurück (eigener Namensraum)."""
    return await _ensure_account(db_key=f"agent:{agent_id}", localpart=_bot_localpart(agent_id))


async def _ensure_account(*, db_key: str, localpart: str) -> AccountTokens:
    """Provisioniert oder lädt einen Matrix-Account.

    1. DB unter *db_key* vorhanden → Token entschlüsseln und zurückgeben (kein Netzwerk).
    2. Sonst → Account mit *localpart* provisionieren (register oder login-Fallback),
       verschlüsselt unter *db_key* ablegen, Klartext zurückgeben.
    """
    # Lazy import: verhindert settings.data_dir-Freeze bei Collection-Zeit
    from hydrahive.settings import settings

    # --- Schritt 1: vorhandene Identität zurückgeben ---
    row = db_teamchat.get_identity(db_key)
    if row is not None:
        logger.debug("ensure_account: vorhandene Identität für key=%s gefunden", db_key)
        return AccountTokens(
            user_id=row["mxid"],
            access_token=decrypt(row["access_token"], settings.data_dir),
            device_id=row["device_id"],
        )

    # --- Schritt 2: neue Identität provisionieren ---
    if not settings.matrix_server_name:
        raise IdentityError(
            "Matrix server_name nicht konfiguriert — "
            "HH_MATRIX_SERVER_NAME setzen oder <config_dir>/matrix/server_name anlegen"
        )

    homeserver = settings.matrix_homeserver_url
    reg_token = settings.matrix_registration_token
    if not reg_token:
        raise IdentityError(
            "matrix_registration_token nicht konfiguriert — "
            "HH_MATRIX_REGISTRATION_TOKEN setzen"
        )

    password = _derive_password(localpart, settings.secret_key)

    logger.info("ensure_account: provisioniere Matrix-Account für localpart=%s", localpart)
    try:
        tokens = await client.register_account(
            homeserver, localpart, password, reg_token,
            device_name="hydrahive-teamchat",
        )
    except AccountExistsError:
        logger.info("ensure_account: Account existiert bereits — login_password für %s", localpart)
        tokens = await client.login_password(
            homeserver, localpart, password,
            device_name="hydrahive-teamchat",
        )

    db_teamchat.upsert_identity(
        user_id=db_key,
        mxid=tokens.user_id,
        access_token=encrypt(tokens.access_token, settings.data_dir),
        device_id=tokens.device_id,
    )
    logger.debug("ensure_account: Identität gespeichert für key=%s mxid=%s", db_key, tokens.user_id)
    return tokens
