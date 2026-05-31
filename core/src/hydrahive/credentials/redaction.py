"""Wert-basierte Secret-Redaction für Tool-Output.

Ein Agent kann ein Secret auf beliebigem Weg in den stdout bekommen — `env`,
`echo $OPENROUTER_API_KEY`, `cat /etc/hydrahive2/llm.json`. Die env-Denylist
in tools.shell hält Keys nur aus dem Subprozess-*Env* fern; sie schützt nicht
den Output. Dieser Layer schwärzt die bekannten Secret-*Werte* aus dem
ToolResult, BEVOR er in tool_calls-DB / Transcript / SSE-Stream / Datamining
landet — egal wie er da reingekommen ist.

Quelle der Secret-Werte ist dieselbe SSOT, die tools.shell für die Denylist
nutzt (tools.shell._env_denylist) plus die Provider-Keys aus der LLM-Config.
Keine dritte hartcodierte Liste — neue Provider sind automatisch abgedeckt.
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterable

from hydrahive.tools.base import ToolResult

# Werte kürzer als das werden NICHT geschwärzt: ein kurzer Secret-Wert (oder ein
# leerer) würde sonst als Substring überall im Output matchen und ihn zerstören.
# Echte Keys/Tokens/DSNs sind deutlich länger.
MIN_SECRET_LEN = 12

PLACEHOLDER = "[REDACTED]"


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


def _scrub_str(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        if secret and len(secret) >= MIN_SECRET_LEN and secret in text:
            text = text.replace(secret, PLACEHOLDER)
    return text


def scrub(value: Any, secrets: Iterable[str] | None = None) -> Any:
    """Ersetzt jeden bekannten Secret-Wert in value durch PLACEHOLDER.

    Rekursiv über dict/list/tuple; gibt neue Strukturen zurück (immutable),
    Nicht-Strings bleiben unangetastet.
    """
    if secrets is None:
        secrets = secret_values()
    secrets = [s for s in secrets if s and len(s) >= MIN_SECRET_LEN]
    if not secrets:
        return value
    return _scrub_value(value, secrets)


def _scrub_value(value: Any, secrets: list[str]) -> Any:
    if isinstance(value, str):
        return _scrub_str(value, secrets)
    if isinstance(value, dict):
        return {k: _scrub_value(v, secrets) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_scrub_value(v, secrets) for v in value)
    return value


# --- Pattern-Detektion für die historische Audit ----------------------------
# Wert-Abgleich (secret_values) findet einen bereits ROTIERTEN Key nicht mehr,
# weil sein alter Wert nicht mehr in Env/Config steht. Für das Aufspüren von
# Altlasten in sessions.db suchen wir nach Key-FORMEN, prefix-verankert, damit
# normaler Text (Commit-Messages, Pfade) nicht fälschlich matcht.
SECRET_PATTERNS = (
    re.compile(r"sk-or-v1-[A-Za-z0-9_\-]{20,}"),  # OpenRouter (nicht hex-only)
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{24,}"),    # Anthropic
    re.compile(r"sk-proj-[A-Za-z0-9_\-]{24,}"),   # OpenAI (Projekt-Key)
    re.compile(r"gsk_[A-Za-z0-9]{32,}"),          # Groq
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),        # Google / Gemini
    re.compile(r"nvapi-[A-Za-z0-9_\-]{32,}"),     # NVIDIA NIM
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),          # GitHub (classic PAT — HH injiziert GH_TOKEN)
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),  # GitHub (fine-grained PAT)
    re.compile(r"hf_[A-Za-z0-9]{20,}"),           # HuggingFace
    re.compile(r"(?i)Authorization:\s*Bearer\s+[A-Za-z0-9_\-\.]{12,}"),  # Bearer-Header
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----.*?-----END [A-Z ]+PRIVATE KEY-----", re.DOTALL),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),           # OpenAI / generisch (zuletzt)
)


# Zur Laufzeit registrierte Zusatz-Patterns (z.B. von Plugins). Liegen hier,
# damit es EINE Pattern-Quelle gibt — nicht erneut eine zweite Liste pro Modul.
_EXTRA_PATTERNS: list[re.Pattern[str]] = []


def register_pattern(pattern: str) -> None:
    """Registriert ein zusätzliches Secret-Pattern (compile-bar) zur SSOT."""
    _EXTRA_PATTERNS.append(re.compile(pattern))


def detect_secrets(text: str) -> list[str]:
    """Findet Secret-FÖRMIGE Substrings (für die Audit). Reihenfolge: spezifische
    Provider-Prefixe zuerst, generisches sk- zuletzt. Dedupliziert (Reihenfolge
    bleibt erhalten)."""
    if not text:
        return []
    found: list[str] = []
    for pattern in (*SECRET_PATTERNS, *_EXTRA_PATTERNS):
        found.extend(pattern.findall(text))
    return list(dict.fromkeys(found))


def mask(secret: str) -> str:
    """Maskiert einen Secret-Wert für Reports: Prefix als Hinweis, Rest verdeckt.
    Der volle Wert taucht nie in der Ausgabe auf."""
    head = secret[:9]
    return f"{head}…({len(secret)} chars)"


def redact_detected(text: str) -> str:
    """Ersetzt jeden secret-förmigen Substring durch PLACEHOLDER (Audit --redact)."""
    for secret in detect_secrets(text):
        text = text.replace(secret, PLACEHOLDER)
    return text


def scrub_result(result: ToolResult, secrets: Iterable[str] | None = None) -> ToolResult:
    """Neues ToolResult mit geschwärztem output/error/metadata. Original bleibt
    unverändert."""
    if secrets is None:
        secrets = secret_values()
    secrets = [s for s in secrets if s and len(s) >= MIN_SECRET_LEN]
    if not secrets:
        return result
    return ToolResult(
        success=result.success,
        output=_scrub_value(result.output, secrets),
        error=_scrub_value(result.error, secrets),
        metadata=_scrub_value(result.metadata, secrets),
    )
