"""ask_agent ↔ Ketten-Anker (agentlink/chain_anchor.py, docs/specs/chain-anchor.md).

Hängt an jeden ausgehenden Auftrag Zieldokument + Originalauftrag an:
- geerbt aus dem eingehenden Auftrag der eigenen Session (Handoff-Lauf), sonst
- neu: Originalauftrag = dieser Auftrag, Zieldokument = Datei aus `ziel_doc`.
Kein Prompt, keine Bitte – der Agent kann die Blöcke nicht weglassen.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.agentlink import acceptance, chain_anchor
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


ABNAHME_SCHEMA = {
    "type": "array", "items": {"type": "string", "maxLength": 8}, "maxItems": 40,
    "description": (
        "IDs der Abnahme-Punkte aus dem Zieldokument, die DIESER Auftrag erfüllen muss (z. B. ['A1','A2']). "
        "Der Kern hängt sie wörtlich an und prüft den Bericht: erst wenn jeder Punkt mit ✅ und Beleg "
        "zurückkommt, gilt der Auftrag als fertig, sonst „unvollständig“. Pflicht, sobald ein Zieldokument "
        "Abnahme-Punkte hat und keine geerbt sind; in einer Kette nur Teilmenge der geerbten Punkte."
    ),
}
# Arbeit an einem Projekt (nicht Fragen/Reviews) braucht ein Ziel (Etappe 2, docs/specs/chain-anchor.md).
_ZIEL_PFLICHT_TYPES = {"feature", "bug_fix", "refactor"}


def goal_required() -> bool:
    """Ziel-Pflicht für Projektarbeit – Einstellung „agent_goal_required“ (System → Agenten), Standard aus.
    Arbeitsweise einer Installation, keine Grundregel: ohne Zieldokumente wären Projekt-Agenten sonst nicht
    beauftragbar (Befund 23.11.2026 vor einer fremden Neuinstallation)."""
    from hydrahive.settings.overrides import resolve
    return resolve("agent_goal_required").strip().lower() in ("1", "true", "yes", "on")


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
    if row.get("abnahme"):
        out["abnahme"] = chain_anchor.Block("abnahme", row["abnahme"])
    return out


def _abnahme(args: dict, ziel: chain_anchor.Block | None, inh: dict) -> chain_anchor.Block | None:
    """Abnahme-Block wählen und prüfen. Unbekannte IDs oder eine Ausweitung des geerbten Umfangs → AnchorError."""
    wanted = [str(x).strip().upper() for x in (args.get("abnahme") or []) if str(x).strip()]
    if not wanted:
        if inh.get("abnahme") is None and ziel is not None and acceptance.points_from_ziel(ziel.body):
            ids = ", ".join(acceptance.points_from_ziel(ziel.body))
            raise AnchorError(f"abnahme fehlt: Wähle die Punkte, die dieser Auftrag erfüllen muss (verfügbar: {ids})")
        return None
    if ziel is None:
        raise AnchorError("abnahme ohne Zieldokument: erst ziel_doc angeben")
    allowed = acceptance.points_from_ziel(inh["abnahme"].body if inh.get("abnahme") else ziel.body)
    unknown = [w for w in wanted if w not in allowed]
    if unknown:
        scope = "im geerbten Abnahme-Umfang" if inh.get("abnahme") else "im Zieldokument"
        raise AnchorError(f"Abnahme-Punkte {', '.join(unknown)} gibt es nicht {scope} (verfügbar: {', '.join(allowed)})")
    return chain_anchor.Block("abnahme", acceptance.body_for(allowed, wanted))


def anchor_task(task_text: str, args: dict, ctx: ToolContext, target_agent: dict | None = None) -> str:
    """Auftragstext mit Anker-Blöcken. Wirft AnchorError, wenn Ziel oder Abnahme fehlen/ungültig sind –
    dann wird NICHTS abgeschickt."""
    inh = inherited(ctx)
    ziel = None
    if "ziel" not in inh and args.get("ziel_doc"):
        ziel = _read_ziel(str(args["ziel_doc"]), ctx.workspace)
    effective = inh.get("ziel") or ziel
    task_type = args.get("task_type") or "feature"
    if (effective is None and (target_agent or {}).get("type") == "project" and task_type in _ZIEL_PFLICHT_TYPES
            and goal_required()):
        raise AnchorError(
            f"Projektarbeit ({task_type}) braucht ein Zieldokument: ziel_doc angeben (Zielbild + Abnahme-Punkte, "
            "vom Nutzer freigegeben). Reine Fragen/Prüfungen als task_type research oder review schicken."
        )
    return chain_anchor.compose(task_text, inh, ziel=ziel, abnahme=_abnahme(args, effective, inh))
