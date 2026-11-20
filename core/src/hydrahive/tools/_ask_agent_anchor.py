"""ask_agent ↔ Ketten-Anker (agentlink/chain_anchor.py, docs/specs/chain-anchor.md).

Hängt an jeden ausgehenden Auftrag Zieldokument + Originalauftrag an:
- geerbt aus dem eingehenden Auftrag der eigenen Session (Handoff-Lauf), sonst
- neu: Originalauftrag = dieser Auftrag, Zieldokument = Datei aus `ziel_doc`.
Kein Prompt, keine Bitte – der Agent kann die Blöcke nicht weglassen.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.agentlink import chain_anchor
from hydrahive.db import agent_handoffs as db_agent_handoffs
from hydrahive.tools.base import ToolContext

ZIEL_DOC_SCHEMA = {
    "type": "string", "maxLength": 500,
    "description": (
        "Pfad zum Zieldokument (z. B. 'hydrahive2-modules/ziele/haushalt-krypto.md', relativ zum Workspace). "
        "Es wird unverändert an diesen und alle folgenden Aufträge der Kette angehängt. Wird ignoriert, "
        "wenn die Kette schon ein Zieldokument trägt."
    ),
}


class AnchorError(ValueError):
    """Zieldokument nicht lesbar – Auftrag wird NICHT ohne Ziel abgeschickt."""


def _read_ziel(path_arg: str, workspace: Path) -> chain_anchor.Block:
    raw = (path_arg or "").strip()
    if not raw:
        raise AnchorError("ziel_doc ist leer")
    base = workspace.resolve()
    p = (base / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    if base not in p.parents and p != base:
        raise AnchorError(f"ziel_doc liegt außerhalb des Workspace: {raw}")
    if not p.is_file():
        raise AnchorError(f"ziel_doc nicht gefunden: {raw}")
    text = p.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        raise AnchorError(f"ziel_doc ist leer: {raw}")
    if len(text) > chain_anchor.MAX_BLOCK_CHARS:
        raise AnchorError(f"ziel_doc zu groß ({len(text)} Zeichen, max {chain_anchor.MAX_BLOCK_CHARS}): {raw}")
    return chain_anchor.Block("ziel", text, raw)


def inherited(ctx: ToolContext) -> dict[str, chain_anchor.Block]:
    """Anker des eigenen eingehenden Auftrags (nur in Handoff-Läufen)."""
    if ctx.origin != "handoff":
        return {}
    row = db_agent_handoffs.anchor_for_session(ctx.session_id)
    if not row:
        return {}
    out: dict[str, chain_anchor.Block] = {}
    if row.get("ziel"):
        out["ziel"] = chain_anchor.Block("ziel", row["ziel"], row.get("ziel_quelle") or "")
    if row.get("original"):
        out["original"] = chain_anchor.Block("original", row["original"])
    return out


def anchor_task(task_text: str, args: dict, ctx: ToolContext) -> str:
    """Auftragstext mit Anker-Blöcken. Wirft AnchorError, wenn ein angegebenes Zieldokument fehlt."""
    inh = inherited(ctx)
    ziel = None
    if "ziel" not in inh and args.get("ziel_doc"):
        ziel = _read_ziel(str(args["ziel_doc"]), ctx.workspace)
    return chain_anchor.compose(task_text, inh, ziel=ziel)
