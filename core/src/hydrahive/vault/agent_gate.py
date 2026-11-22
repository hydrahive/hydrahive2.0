"""Vault-Werkzeuge nur bei entsperrtem Vault (Ziel vault-agenten §1.1–1.4, Etappen 1a/1b).

Geprüft an EINER Stelle: ``runner/dispatcher.py`` vor dem Aufruf des Werkzeugs. Vault-Werkzeug = Kernliste
(``CORE_SENSITIVE`` ohne Mail, Ziel §1.7) plus ``sensitive_tools`` aus den Manifesten geladener Module mit
``"vault": true``. Der Lauf gehört dem Besitzer der Sitzung (``ToolContext.user_id`` = Nutzername); der Vault
arbeitet mit der festen user_id. Unbekannter Nutzer oder Fehler → gesperrt (fail closed).

Etappe 1b (§1.4): Läuft der Agent für einen Kommunikationskanal (``ToolContext.channel`` gesetzt, auch geerbt über
ask_agent), liefert ein Vault-Werkzeug nie Daten – egal ob der Vault offen ist.
"""
from __future__ import annotations

import logging

from hydrahive.db._mirror_levels import CORE_SENSITIVE
from hydrahive.tools.base import ToolResult

logger = logging.getLogger(__name__)

LOCKED_HINT = "Vault gesperrt – bitte in HydraHive entsperren."
#: Sensibel für das Datamining, aber laut Ziel §1.7 frei (keine Vault-Daten).
_NOT_VAULT = frozenset({"read_mail", "send_mail"})
#: Lesbare Kanalnamen für den Hinweis; unbekannte Kanäle mit großem Anfangsbuchstaben.
_CHANNEL_LABELS = {
    "whatsapp": "WhatsApp", "discord": "Discord", "email": "E-Mail", "mail": "E-Mail",
    "matrix": "Matrix", "telegram": "Telegram", "signal": "Signal", "sms": "SMS",
    "federation": "einen fremden Server",
}


def channel_hint(channel: str) -> str:
    label = _CHANNEL_LABELS.get(channel.strip().lower()) or channel.strip().capitalize()
    return f"Diese Daten gibt es nur in HydraHive, nicht über {label}."


def vault_tools() -> frozenset[str]:
    out = {name for name in CORE_SENSITIVE if name not in _NOT_VAULT}
    try:
        from hydrahive.modules.registry import REGISTRY
        mods = list(REGISTRY.values())
    except Exception as e:  # noqa: BLE001 — Modul-Registry fehlt (z. B. Tests) → nur Kernliste
        logger.debug("vault_tools: Modul-Registry nicht lesbar: %s", e)
        mods = []
    for m in mods:
        if m.loaded and m.manifest and m.manifest.vault:
            out.update(tool for tool, _level in m.manifest.sensitive_tools)
    return frozenset(out)


def blocked(tool_name: str, username: str, *, channel: str | None = None) -> ToolResult | None:
    """Sperr-Hinweis, wenn ``tool_name`` ein Vault-Werkzeug ist und der Lauf aus einem Kanal kommt
    oder der Vault des Besitzers nicht offen ist."""
    if tool_name not in vault_tools():
        return None
    if channel and channel.strip():
        return ToolResult.fail(channel_hint(channel))
    try:
        from hydrahive.access.check import user_id_for
        from hydrahive.vault import unlocks
        user_id = user_id_for(username)
        if user_id and unlocks.use(user_id):
            return None
    except Exception:  # noqa: BLE001 — nicht entscheidbar → gesperrt
        logger.exception("Vault-Prüfung für %s fehlgeschlagen – gesperrt", tool_name)
    return ToolResult.fail(LOCKED_HINT)
