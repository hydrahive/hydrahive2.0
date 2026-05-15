"""AES-GCM Verschlüsselung für Credential-Values.

Master-Key-Quellen (in Priorität):
  1. HH_MASTER_KEY env var (64-hex chars = 32 Bytes)
  2. Auto-generierte Datei data_dir/credentials/.master_key (0600)

Verschlüsselte Werte haben das Präfix "enc:v1:".
Ältere Plaintext-Werte werden beim nächsten Write automatisch verschlüsselt.
"""
from __future__ import annotations

import base64
import logging
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

_PREFIX = "enc:v1:"
_NONCE_BYTES = 12


def _key_path(data_dir: Path) -> Path:
    return data_dir / "credentials" / ".master_key"


def _load_key(data_dir: Path) -> bytes:
    env = os.environ.get("HH_MASTER_KEY", "").strip()
    if env:
        try:
            key = bytes.fromhex(env)
            if len(key) == 32:
                return key
        except ValueError:
            pass
        logger.warning("HH_MASTER_KEY ist kein valides 64-Hex-String, ignoriert")

    path = _key_path(data_dir)
    if path.exists():
        try:
            return bytes.fromhex(path.read_text().strip())
        except ValueError:
            logger.warning("Defekte Master-Key-Datei: %s — generiere neu", path)

    key = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.hex())
    os.chmod(path, 0o600)
    logger.info("Neuer Master-Key generiert: %s", path)
    return key


def encrypt(plaintext: str, data_dir: Path) -> str:
    key = _load_key(data_dir)
    nonce = secrets.token_bytes(_NONCE_BYTES)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return _PREFIX + base64.urlsafe_b64encode(nonce + ct).decode()


def decrypt(value: str, data_dir: Path) -> str:
    if not value.startswith(_PREFIX):
        return value  # Plaintext-Legacy — wird beim nächsten Write verschlüsselt
    raw = base64.urlsafe_b64decode(value[len(_PREFIX):] + "==")
    nonce, ct = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
    key = _load_key(data_dir)
    return AESGCM(key).decrypt(nonce, ct, None).decode()


def is_encrypted(value: str) -> bool:
    return value.startswith(_PREFIX)
