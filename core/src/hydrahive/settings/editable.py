"""Registry der GUI-editierbaren Settings.

SSOT dafür, WELCHE Settings über die Web-Konsole änderbar sind (nicht die
Bootstrap-Infra wie Pfade/Secret-Key/Port — die bleiben Env-only). Jeder Eintrag
nennt Env-Var + Default exakt wie das jeweilige Settings-Mixin → der Override
darf nie das Verhalten ändern, wenn nichts gesetzt ist.

Neues GUI-Setting = ein Eintrag hier + Consumer liest über `overrides.resolve`/
`env_or_override`. Taucht automatisch in der Settings-Seite auf.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EditableSetting:
    key: str
    env_var: str
    type: str          # "string" | "bool" | "int" | "secret"
    group: str
    label: str
    default: str = ""
    help: str = ""


EDITABLE_SETTINGS: list[EditableSetting] = [
    EditableSetting("searxng_url", "HH_SEARXNG_URL", "string", "Websuche", "SearXNG-URL",
                    help="Basis-URL deiner SearXNG-Instanz für das web_search-Tool, z.B. https://searx.example"),
    EditableSetting("mail_enabled", "HH_MAIL_ENABLED", "bool", "Mail", "Mail aktiv", "0"),
    EditableSetting("mail_smtp_host", "HH_MAIL_SMTP_HOST", "string", "Mail", "SMTP-Host"),
    EditableSetting("mail_smtp_port", "HH_MAIL_SMTP_PORT", "int", "Mail", "SMTP-Port", "587"),
    EditableSetting("mail_smtp_user", "HH_MAIL_SMTP_USER", "string", "Mail", "SMTP-User"),
    EditableSetting("mail_smtp_password", "HH_MAIL_SMTP_PASSWORD", "secret", "Mail", "SMTP-Passwort"),
    EditableSetting("mail_from", "HH_MAIL_FROM", "string", "Mail", "Absender (From)"),
    EditableSetting("mail_imap_host", "HH_MAIL_IMAP_HOST", "string", "Mail", "IMAP-Host",
                    help="Server zum Empfangen. Leer = derselbe Host wie SMTP (üblich). Login = SMTP-User/-Passwort."),
    EditableSetting("mail_imap_port", "HH_MAIL_IMAP_PORT", "int", "Mail", "IMAP-Port", "993"),
    EditableSetting("discord_enabled", "HH_DISCORD_ENABLED", "bool", "Discord", "Discord aktiv", "1"),
    EditableSetting("agentlink_url", "HH_AGENTLINK_URL", "string", "AgentLink", "AgentLink-URL"),
    EditableSetting("agentlink_token", "HH_AGENTLINK_TOKEN", "secret", "AgentLink", "AgentLink-Token"),
    EditableSetting("health_api_key", "HH_HEALTH_API_KEY", "secret", "Health", "Health-Ingest-API-Key"),
    EditableSetting("coingecko_api_key", "HH_COINGECKO_API_KEY", "secret", "Krypto", "CoinGecko API-Key",
                    help="Optionaler Demo-API-Key von CoinGecko (kostenlos, 10k Anfragen/Monat). Ohne Key läuft das Cryptoboard ebenfalls, aber mit niedrigerem Rate-Limit."),
    EditableSetting("cryptocompare_api_key", "HH_CRYPTOCOMPARE_API_KEY", "secret", "Krypto", "CryptoCompare API-Key",
                    help="Optionaler Key für Krypto-News via CryptoCompare. Ohne Key werden News übersprungen."),
    EditableSetting("update_check_enabled", "HH_UPDATE_CHECK_ENABLED", "bool", "System", "Update-Check aktiv", "true"),
    EditableSetting("module_hub_extra_git_urls", "HH_MODULE_HUB_GIT_URLS", "string", "Module", "Zusätzliche Modul-Hubs",
                    help="Komma-separierte Git-URLs interner Hubs (z.B. Gitea), zusätzlich zum öffentlichen GitHub-Hub. Deren Module erscheinen mit unter den verfügbaren. Greift nach Backend-Neustart."),
]

BY_KEY: dict[str, EditableSetting] = {s.key: s for s in EDITABLE_SETTINGS}
