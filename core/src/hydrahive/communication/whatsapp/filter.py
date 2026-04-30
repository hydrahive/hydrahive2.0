"""Filter-Logik für eingehende WhatsApp-Nachrichten.

Reihenfolge:
1. Sender ist Owner → durch (überschreibt alle anderen Filter)
2. In Blacklist → reject
3. Group-Chat und group_chats_enabled=False → reject
4. Whitelist nicht leer und Sender nicht drin → reject
5. Keyword gesetzt und Nachricht enthält Keyword nicht (case-insensitive) → reject
6. private_chats_enabled=False und 1:1 → reject
7. Sonst → durch
"""
from __future__ import annotations

from dataclasses import dataclass

from hydrahive.communication.whatsapp.config import WhatsAppConfig


@dataclass
class FilterResult:
    accepted: bool
    reason: str | None = None
    is_owner: bool = False


def _digits_only(jid_or_num: str) -> str:
    """Aus '491234@s.whatsapp.net' oder '+491234' wird '491234'."""
    raw = jid_or_num.split("@")[0] if "@" in jid_or_num else jid_or_num
    return "".join(ch for ch in raw if ch.isdigit())


def _matches_any(sender_digits: str, numbers: list[str]) -> bool:
    """True wenn sender_digits mit einer der Nummern endet (oder gleich ist)."""
    for n in numbers:
        nd = _digits_only(n)
        if not nd:
            continue
        if sender_digits == nd or sender_digits.endswith(nd):
            return True
    return False


def evaluate(
    *,
    cfg: WhatsAppConfig,
    sender_jid: str,
    is_group: bool,
    text: str,
    skip_keyword: bool = False,
) -> FilterResult:
    """Pre-Filter: alle Checks ohne text. Post-Filter: zusätzlich keyword.

    skip_keyword=True wird bei eingehenden Voice-Nachrichten genutzt um
    den Sender zu prüfen BEVOR STT läuft (spart Ressourcen für
    geblockte Sender, kein Info-Leak). Nach STT wird der Filter ein
    zweites Mal mit dem Transkript gerufen — owner/block sind dann
    schon ok, einzig der keyword-Check darf jetzt feuern.
    """
    sender_digits = _digits_only(sender_jid)

    if cfg.owner_numbers and _matches_any(sender_digits, cfg.owner_numbers):
        return FilterResult(accepted=True, is_owner=True)

    if cfg.blocked_numbers and _matches_any(sender_digits, cfg.blocked_numbers):
        return FilterResult(accepted=False, reason="blocked")

    if is_group:
        if not cfg.group_chats_enabled:
            return FilterResult(accepted=False, reason="group_chats_disabled")
    else:
        if not cfg.private_chats_enabled:
            return FilterResult(accepted=False, reason="private_chats_disabled")

    if cfg.allowed_numbers and not _matches_any(sender_digits, cfg.allowed_numbers):
        return FilterResult(accepted=False, reason="not_in_allowlist")

    if not skip_keyword and cfg.require_keyword:
        if cfg.require_keyword.lower() not in text.lower():
            return FilterResult(accepted=False, reason="no_keyword")

    return FilterResult(accepted=True)
