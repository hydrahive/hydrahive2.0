"""Provider-fremde Content-Blocks aus Anthropic-Messages entfernen.

Hintergrund: Sessions können das Modell wechseln. Läuft eine Session zuerst
über den Codex-Provider und danach über Anthropic, liegen in der History
Blocks vom Typ ``codex_reasoning`` (opaker Provider-State, siehe
_codex_provider.py). Anthropic kennt diesen Typ nicht und lehnt die komplette
Anfrage ab::

    400 invalid_request_error — messages.2.content.0: Input tag
    'codex_reasoning' found using 'type' does not match any of the expected
    tags: 'text', 'thinking', 'tool_use', 'tool_result', …

Der Codex-Pfad übersetzt seine eigenen Blocks korrekt zurück
(_codex_convert.py) und der LiteLLM-Pfad verwirft sie beim Mapping auf das
OpenAI-Format. Nur der Anthropic-Pfad reichte sie ungefiltert durch.

Gefiltert wird beim SENDEN, nicht beim Speichern: die Blocks bleiben in der
DB erhalten (Codex braucht sie für Reasoning-Kontinuität), sie werden nur
nicht an Anthropic geschickt. Dadurch heilen auch bestehende Sessions sofort.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Block-Typen, die die Anthropic Messages-API in `messages[].content`
# akzeptiert. Alles andere ist Provider-State fremder Backends und muss raus.
# Quelle: Fehlermeldung der API (Liste der "expected tags").
ANTHROPIC_BLOCK_TYPES = frozenset({
    "bash_code_execution_tool_result",
    "code_execution_tool_result",
    "connector_text",
    "container_upload",
    "document",
    "image",
    "mid_conv_system",
    "redacted_thinking",
    "search_result",
    "server_tool_use",
    "text",
    "text_editor_code_execution_tool_result",
    "thinking",
    "tool_result",
    "tool_search_tool_result",
    "tool_use",
    "web_fetch_tool_result",
    "web_search_tool_result",
})


def strip_foreign_blocks(messages: list[dict]) -> list[dict]:
    """Entfernt Blocks, die Anthropic nicht kennt.

    Fällt eine Message dadurch komplett leer, wird sie ganz weggelassen —
    Anthropic lehnt leere ``content``-Listen ebenso mit 400 ab. In der DB
    existiert dieser Fall real (Assistant-Turn, der nur aus einem
    ``codex_reasoning``-Block besteht), deshalb ist das kein Theoriefall.

    String-Content (alte API-Form) bleibt unangetastet.
    """
    out: list[dict] = []
    dropped_types: set[str] = set()
    dropped_messages = 0

    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            out.append(msg)
            continue

        kept: list = []
        for block in content:
            if not isinstance(block, dict):
                kept.append(block)
                continue
            btype = block.get("type")
            if btype in ANTHROPIC_BLOCK_TYPES:
                kept.append(block)
            else:
                dropped_types.add(str(btype))

        if kept:
            out.append({**msg, "content": kept})
        elif content:
            # Message ist durch das Filtern leer geworden → weglassen statt
            # mit content=[] zu senden (sonst erneut 400).
            dropped_messages += 1
        else:
            # War schon vorher leer — unverändert durchreichen, damit wir
            # bestehendes Verhalten nicht still ändern.
            out.append(msg)

    if dropped_types:
        logger.info(
            "Anthropic-Payload: %d provider-fremde Block-Typen entfernt (%s)%s",
            len(dropped_types),
            ", ".join(sorted(dropped_types)),
            f"; {dropped_messages} leer gewordene Message(s) weggelassen" if dropped_messages else "",
        )
    return out
