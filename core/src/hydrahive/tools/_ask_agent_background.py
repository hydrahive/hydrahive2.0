"""Hintergrund-Zweig von ask_agent (docs/specs/agent-background-delegation.md).

Im Chat kehrt ask_agent sofort zurück. Der Auftrag wird in agent_delegations
festgehalten, ein Watcher wartet auf das Ergebnis und stellt es später als
eigene Nachricht in die Session zu. Der Auftraggeber-Agent wird dann erneut
aufgerufen.
"""
from __future__ import annotations

import logging

from hydrahive.db import delegations as delegations_db
from hydrahive.tools.base import ToolContext, ToolResult

logger = logging.getLogger(__name__)

MAX_RUNNING_PER_SESSION = 5
# Spiegelt runner/_run_origin.MAX_CHAIN_DEPTH. Kein Import: tools → runner →
# agents → tools wäre ein Zyklus. test_background_delegation prüft Gleichheit.
MAX_CHAIN_DEPTH = 3

DESCRIPTION_HINT = (
    "Im Chat läuft ein Auftrag an einen internen Spezialisten im HINTERGRUND: "
    "das Werkzeug kehrt sofort zurück, das Ergebnis kommt später automatisch als "
    "neue Nachricht und du wirst dann erneut aufgerufen. Warte nicht darauf und "
    "sende denselben Auftrag nicht erneut. Mehrere unabhängige Aufträge kannst du "
    "nacheinander vergeben, sie laufen gleichzeitig. wait=true nur für kurze "
    "Aufträge, deren Ergebnis du im selben Zug zwingend brauchst."
)

CANCEL_SCHEMA = {
    "type": "string",
    "description": (
        "Statt zu beauftragen: einen eigenen laufenden Hintergrund-Auftrag "
        "dieser Session abbrechen (Auftrags-ID aus der Rückmeldung, 8 Zeichen "
        "reichen). agent_id/task dann weglassen."
    ),
}

WAIT_SCHEMA = {
    "type": "boolean",
    "description": (
        "true = auf das Ergebnis warten (blockiert den Chat bis zur Antwort). "
        "Default false: Hintergrund, Ergebnis kommt als neue Nachricht."
    ),
}


def wants_background(args: dict, ctx: ToolContext, is_internal: bool) -> bool:
    """Hintergrund nur für interne Spezialisten aus Chat-/Zustell-Läufen,
    und nur wenn der Agent nicht ausdrücklich warten will."""
    if not is_internal or bool(args.get("wait")):
        return False
    return ctx.origin in ("chat", "delegation")


def refuse_reason(ctx: ToolContext) -> str | None:
    """Grenzen VOR dem Absenden prüfen (sonst liefe der Spezialist umsonst)."""
    if ctx.origin_depth + 1 > MAX_CHAIN_DEPTH:
        return (
            f"Automatische Kette zu tief ({MAX_CHAIN_DEPTH} Hintergrund-Runden ohne "
            "Nutzer-Nachricht). Nicht erneut beauftragen — fasse den Stand für den "
            "Nutzer zusammen und frag ihn, ob weitergemacht werden soll."
        )
    if delegations_db.count_running(ctx.session_id) >= MAX_RUNNING_PER_SESSION:
        return (
            f"Schon {MAX_RUNNING_PER_SESSION} Hintergrund-Aufträge laufen in dieser "
            "Session. Warte auf deren Ergebnisse, bevor du weitere vergibst."
        )
    return None


def start(
    *, ctx: ToolContext, state_id: str, target: dict, task: str,
    timeout_seconds: int, fut,
) -> ToolResult:
    from hydrahive.runner import delegation_watch

    row = delegations_db.create(
        session_id=ctx.session_id, agent_id=ctx.agent_id, user_id=ctx.user_id,
        target_agent_id=target["id"], target_name=target.get("name") or target["id"],
        task=task, state_id=state_id, depth=ctx.origin_depth + 1,
        timeout_seconds=timeout_seconds,
    )
    delegation_watch.start(row["id"], fut)
    minutes = max(1, round(timeout_seconds / 60))
    logger.info("ask_agent: Hintergrund-Auftrag %s an %s", row["id"], row["target_name"])
    return ToolResult.ok(
        f"Auftrag {row['id'][-8:]} an {row['target_name']} läuft im Hintergrund "
        f"(Frist ca. {minutes} min). Das Ergebnis kommt automatisch als neue "
        "Nachricht in diese Session, dann wirst du erneut aufgerufen. Warte NICHT "
        "darauf und sende den Auftrag nicht erneut. Sag dem Nutzer kurz, was "
        "beauftragt wurde, und mach mit anderem weiter oder beende deine Antwort.",
        delegation_id=row["id"], background=True,
    )


def cancel_own(ctx: ToolContext, ref: str) -> ToolResult:
    """Bricht einen laufenden Hintergrund-Auftrag DIESER Session ab.

    Vorher nur per Knopf im Chat möglich (Hindernis 4, 01.10.2026). Fremde
    Sessions sind tabu; Kurz-ID (Ende der ID) wie in der Rückmeldung.
    """
    from hydrahive.runner import delegation_control

    ref = (ref or "").strip()
    if len(ref) < 6:
        return ToolResult.fail("Auftrags-ID zu kurz (mindestens 6 Zeichen).")
    mine = [d for d in delegations_db.list_for_session(ctx.session_id, limit=100)
            if d["id"] == ref or d["id"].endswith(ref)]
    if not mine:
        return ToolResult.fail(f"Kein Auftrag {ref} in dieser Session.")
    if len(mine) > 1:
        return ToolResult.fail(f"Auftrags-ID {ref} ist mehrdeutig, bitte länger angeben.")
    d = mine[0]
    # cancel() wechselt nur running → cancelled (atomar); sonst False.
    if not delegation_control.cancel(d):
        return ToolResult.fail(f"Auftrag {ref} läuft nicht mehr (Status: {d['status']}).")
    logger.info("ask_agent: Hintergrund-Auftrag %s vom Agenten abgebrochen", d["id"])
    return ToolResult.ok(f"Auftrag {d['id'][-8:]} an {d['target_name']} abgebrochen. "
                         "Es kommt kein Ergebnis mehr.")
