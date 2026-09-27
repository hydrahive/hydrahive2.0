"""Quellen der Secret-Werte, die aus Tool-Output geschwärzt werden.

Ausgelagert aus redaction.py (Größe). redaction re-exportiert alles hier, damit
`redaction.secret_values()` & Co. für alle Aufrufer gleich bleiben.

- secret_values(): shell-Denylist-SSOT (tools.shell._env_denylist) + Provider-
  Keys der LLM-Config — keine dritte hartcodierte Liste.
- agent_secret_values(): Postfach-Passwörter aus der Agent-Config.
- user_secret_values(): Credential-Werte des Nutzers (Security-Task ef27f79b).
"""
from __future__ import annotations

import base64
import logging
import os
import re

logger = logging.getLogger(__name__)

_PEM_FRAME = re.compile(r"-----(BEGIN|END) [A-Z0-9 ]+-----")

# Werte kürzer als das werden NICHT geschwärzt: ein kurzer Secret-Wert (oder ein
# leerer) würde sonst als Substring überall im Output matchen und ihn zerstören.
# Echte Keys/Tokens/DSNs sind deutlich länger.
MIN_SECRET_LEN = 12

def secret_values() -> set[str]:
    """Aktuelle Secret-Werte, die aus Output geschwärzt werden müssen.

    Zieht aus (1) der shell-Denylist-SSOT (Provider-Keys + JWT/DSN/Tokens, die
    apply_keys/Settings ins Prozess-Env legen) und (2) den Provider-Keys der
    LLM-Config — falls einer in der Config steht, aber (noch) nicht im Env.
    """
    out: set[str] = set()

    # (1) Werte der denylisteten Env-Vars — gleiche SSOT wie der Env-Filter.
    from hydrahive.tools.shell import _env_denylist

    for name in _env_denylist():
        val = os.environ.get(name, "")
        if len(val) >= MIN_SECRET_LEN:
            out.add(val)

    # (2) Provider-Keys direkt aus der LLM-Config.
    from hydrahive.llm._config import load_config

    for provider in load_config().get("providers", []):
        key = provider.get("api_key", "")
        if len(key) >= MIN_SECRET_LEN:
            out.add(key)

    return out


def agent_secret_values(agent_id: str) -> set[str]:
    """Per-Agent Secret-Werte: die Postfach-Passwörter aus `tool_config`.

    `secret_values()` (env + LLM-Config) kennt diese nicht — sie liegen in der
    Agent-Config. Damit ein Buddy, der seine eigene config.json liest, das
    Passwort nicht im Tool-Output leakt, mischt der dispatcher diese an der
    Schwärz-Engstelle dazu. Werte < MIN_SECRET_LEN bleiben (wie überall)
    ungeschützt, um kurze Substrings nicht überall im Output zu zerstören.
    """
    if not agent_id:
        return set()
    out: set[str] = set()
    try:
        from hydrahive.agents import config as agent_config
        tc = (agent_config.get(agent_id) or {}).get("tool_config") or {}
        for block in ("smtp", "imap"):
            pw = (tc.get(block) or {}).get("password", "")
            if len(pw) >= MIN_SECRET_LEN:
                out.add(pw)
    except Exception as exc:
        # Sicherheitsrelevant: schlägt das Laden fehl, werden diese Secrets NICHT
        # geschwärzt. Nicht still verschlucken — sonst leakt es unbemerkt.
        logger.warning("Mail-Secrets für Redaction (agent=%s) nicht ladbar: %s", agent_id, exc)
    return out


def user_secret_values(username: str) -> set[str]:
    """Die Credential-Werte eines Nutzers (Vault unter /credentials).

    Spiegelt ein Dienst einen eingesetzten Token zurück (Echo-Endpunkt,
    Fehlerseite) oder liest ein Agent eine Datei mit dem Wert, landet er sonst
    ungeschwärzt in tool_calls-DB, Transcript, Stream und Datamining.
    SSH-Keys sind mehrzeilig — jede lange Zeile wird einzeln geschwärzt.
    """
    if not username:
        return set()
    out: set[str] = set()
    try:
        from hydrahive.credentials.store import list_credentials
        for cred in list_credentials(username):
            parts = [cred.value, *cred.value.splitlines()]
            if cred.type == "basic":
                # Echo-Dienste spiegeln den Header ("Basic <base64>"), Dateien
                # enthalten oft nur das Passwort ohne "user:".
                parts.append(base64.b64encode(cred.value.encode("utf-8")).decode("ascii"))
                parts.append(cred.value.partition(":")[2])
            for part in parts:
                part = part.strip()
                # PEM-Rahmen ("-----BEGIN … KEY-----") ist nicht geheim.
                if len(part) >= MIN_SECRET_LEN and not _PEM_FRAME.fullmatch(part):
                    out.add(part)
    except Exception as exc:
        logger.warning("Credential-Secrets für Redaction (user=%s) nicht ladbar: %s", username, exc)
    return out
