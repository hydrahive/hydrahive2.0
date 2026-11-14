"""Kurzfassung des letzten Tool-Ergebnisses für die Sprechblase im Agenten-Büro (Spec agent-office.md §1).

Reine Funktion, keine Nutzdaten über ~120 Zeichen hinaus (`activity.set_tool` kürzt ohnehin hart, hier
nur die erste Zeile wählen, damit nicht mitten in einem JSON-Blob abgeschnitten wird).
"""
from __future__ import annotations


def _as_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block.get("text") or "")
        return ""
    return ""


def summarize_result_blocks(blocks: list[dict]) -> str:
    """Erste Zeile des letzten `tool_result`-Blocks; Fehler bekommen das Präfix „Fehler: “."""
    for block in reversed(blocks):
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        text = _as_text(block.get("content"))
        line = text.split("\n", 1)[0].strip()[:120]
        if not line:
            return ""
        return f"Fehler: {line}" if block.get("is_error") else line
    return ""
