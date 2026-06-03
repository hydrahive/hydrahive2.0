"""teamchat/identity.py — HydraHive-User ↔ Matrix-Account-Provisioning.

ensure_identity(user_id) ist idempotent: gibt eine vorhandene Matrix-Identität
zurück oder legt sie neu an (register → falls AccountExistsError: login).
Passwörter sind deterministisch (sha256(user_id:server_secret)[:32]) damit
Re-Login nach DB-Verlust ohne erneute Registrierung funktioniert.
"""
from __future__ import annotations

import hashlib
import logging

from hydrahive.credentials._crypto import decrypt, encrypt
from hydrahive.db import teamchat as db_teamchat
from hydrahive.teamchat import client
from hydrahive.teamchat.client import AccountExistsError, AccountTokens

logger = logging.getLogger(__name__)


class IdentityError(Exception):
    """Wird geworfen wenn Matrix-Provisioning wegen fehlender Konfiguration scheitert."""


def _derive_password(user_id: str, server_secret: str) -> str:
    """Deterministisches Passwort: sha256(user_id:server_secret)[:32] (Hex)."""
    return hashlib.sha256(f"{user_id}:{server_secret}".encode()).hexdigest()[:32]


async def ensure_identity(user_id: str) -> AccountTokens:
    """Gibt die Matrix-Identität für einen HydraHive-User zurück.

    1. DB vorhanden → Token entschlüsseln und zurückgeben (kein Netzwerk).
    2. Sonst → Matrix-Account provisionieren (register oder login-Fallback),
       verschlüsselt in DB ablegen, Klartext zurückgeben.
    """
    # Lazy import: verhindert settings.data_dir-Freeze bei Collection-Zeit
    from hydrahive.settings import settings

    # --- Schritt 1: vorhandene Identität zurückgeben ---
    row = db_teamchat.get_identity(user_id)
    if row is not None:
        logger.debug("ensure_identity: vorhandene Identität für user=%s gefunden", user_id)
        return AccountTokens(
            user_id=row["mxid"],
            access_token=decrypt(row["access_token"], settings.data_dir),
            device_id=row["device_id"],
        )

    # --- Schritt 2: neue Identität provisionieren ---
    server_name = settings.matrix_server_name
    if not server_name:
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

    password = _derive_password(user_id, settings.secret_key)

    logger.info("ensure_identity: provisioniere Matrix-Account für user=%s", user_id)
    try:
        tokens = await client.register_account(
            homeserver, user_id, password, reg_token,
            device_name="hydrahive-teamchat",
        )
    except AccountExistsError:
        logger.info(
            "ensure_identity: Account existiert bereits — login_password für user=%s",
            user_id,
        )
        tokens = await client.login_password(
            homeserver, user_id, password,
            device_name="hydrahive-teamchat",
        )

    db_teamchat.upsert_identity(
        user_id=user_id,
        mxid=tokens.user_id,
        access_token=encrypt(tokens.access_token, settings.data_dir),
        device_id=tokens.device_id,
    )
    logger.debug(
        "ensure_identity: Identität gespeichert für user=%s mxid=%s",
        user_id, tokens.user_id,
    )
    return tokens
