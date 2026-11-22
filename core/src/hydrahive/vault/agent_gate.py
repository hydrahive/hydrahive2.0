"""Vault-Werkzeuge nur bei entsperrtem Vault (Ziel vault-agenten §1.1–1.3, Etappe 1a).

Geprüft an EINER Stelle: ``runner/dispatcher.py`` vor dem Aufruf des Werkzeugs. Vault-Werkzeug = Kernliste
(``CORE_SENSITIVE`` ohne Mail, Ziel §1.7) plus ``sensitive_tools`` aus den Manifesten geladener Module mit
``"vault": true``. Der Lauf gehört dem Besitzer der Sitzung (``ToolContext.user_id`` = Nutzername); der Vault
arbeitet mit der festen user_id. Unbekannter Nutzer oder Fehler → gesperrt (fail closed).
"""
from __future__ import annotations

import logging

from hydrahive.db._mirror_levels import CORE_SENSITIVE
from hydrahive.tools.base import ToolResult

logger = logging.getLogger(__name__)

LOCKED_HINT = "Vault gesperrt – bitte in HydraHive entsperren."
#: Sensibel für das Datamining, aber laut Ziel §1.7 frei (keine Vault-Daten).
_NOT_VAULT = frozenset({"read_mail", "send_mail"})


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


def blocked(tool_name: str, username: str) -> ToolResult | None:
    """Sperr-Hinweis, wenn ``tool_name`` ein Vault-Werkzeug ist und der Vault des Besitzers nicht offen ist."""
    if tool_name not in vault_tools():
        return None
    try:
        from hydrahive.access.check import user_id_for
        from hydrahive.vault import unlocks
        user_id = user_id_for(username)
        if user_id and unlocks.use(user_id):
            return None
    except Exception:  # noqa: BLE001 — nicht entscheidbar → gesperrt
        logger.exception("Vault-Prüfung für %s fehlgeschlagen – gesperrt", tool_name)
    return ToolResult.fail(LOCKED_HINT)
