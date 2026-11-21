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
    "Im Chat (und wenn du selbst per Auftrag läufst) läuft ein Auftrag an einen internen Spezialisten im HINTERGRUND: "
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


# Herkünfte, aus denen ask_agent im Hintergrund beauftragt. EINE Quelle für
# runner/_run_origin.RunOrigin.background_allowed und diese Weiche —
# test_delegation_chain_handoff prüft Gleichheit. (Befund 19.11.2026: #725
# setzte nur RunOrigin.background_allowed, das niemand las → wirkungslos.)
BACKGROUND_ORIGINS = ("chat", "delegation", "handoff")


def wants_background(args: dict, ctx: ToolContext) -> bool:
    """Hintergrund für interne Spezialisten (Ziele ohne „@“ sind immer intern)
    aus Chat-, Zustell- und Handoff-Läufen, und nur wenn der Agent nicht
    ausdrücklich warten will. Handoff: Ein beauftragter Projekt-Agent verteilt
    an Spezialisten, seine Antwort hält runner/handoff_chain zurück, bis alle
    Kinder fertig sind."""
    if bool(args.get("wait")):
        return False
    return ctx.origin in BACKGROUND_ORIGINS


# Unter dieser Restzeit der Kette wird nichts mehr vergeben: ein Spezialist
# braucht Minuten, sonst läuft er sicher in die Gesamtfrist (Befund 19.11.2026).
MIN_CHILD_SECONDS = 300


def chain_remaining(ctx: ToolContext) -> float | None:
    """Restzeit der Gesamtfrist, wenn dieser Lauf zu einem Handoff-Auftrag gehört."""
    if ctx.origin != "handoff" or not ctx.session_id:
        return None
    from hydrahive.runner import handoff_session
    return handoff_session.remaining_seconds(ctx.session_id)


def child_timeout(ctx: ToolContext, timeout_seconds: int) -> int:
    """Frist des Kindes höchstens bis zum Ende der Kette (nie länger als die Kette lebt)."""
    left = chain_remaining(ctx)
    if left is None:
        return timeout_seconds
    return max(1, min(timeout_seconds, int(left)))


def refuse_reason(ctx: ToolContext) -> str | None:
    """Grenzen VOR dem Absenden prüfen (sonst liefe der Spezialist umsonst)."""
    left = chain_remaining(ctx)
    if left is not None and left < MIN_CHILD_SECONDS:
        return (
            f"Gesamtfrist dieses Auftrags fast abgelaufen (noch {max(0, int(left // 60))} min). "
            "Nicht mehr beauftragen — der Spezialist würde mittendrin abgebrochen. "
            "Sichere den Stand (committen/pushen) und berichte, was erledigt ist und was fehlt."
        )
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
    if ctx.origin == "handoff":
        # Beauftragter Agent (Kette): kein Nutzer im Chat. Antwort an den
        # Auftraggeber geht erst raus, wenn nichts mehr offen ist (handoff_chain).
        follow = ("Vergib unabhängige Teilaufträge jetzt gleich mit, dann beende deinen "
                  "Lauf mit einer Zeile, was vergeben ist. Dein Abschlussbericht kommt erst, "
                  "wenn alle Ergebnisse da sind.")
    else:
        follow = ("Sag dem Nutzer kurz, was beauftragt wurde, und mach mit anderem weiter "
                  "oder beende deine Antwort.")
    return ToolResult.ok(
        f"Auftrag {row['id'][-8:]} an {row['target_name']} läuft im Hintergrund "
        f"(Frist ca. {minutes} min). Das Ergebnis kommt automatisch als neue "
        "Nachricht in diese Session, dann wirst du erneut aufgerufen. Warte NICHT "
        f"darauf und sende den Auftrag nicht erneut. {follow}",
        delegation_id=row["id"], background=True,
    )


def start_or_fail(*, ctx: ToolContext, state_id: str, target: dict, task: str,
                  timeout_seconds: int, fut, cancel) -> ToolResult:
    """Wie start(); scheitert das Anlegen, sofort Fehler statt synchron zu warten.

    Früher wartete ask_agent dann bis zur Frist (600 s) – im Chat genau das Hängen,
    das der Hintergrund verhindern soll (CI 06.10.2026, UNIQUE-Verletzung state_id).
    """
    try:
        return start(ctx=ctx, state_id=state_id, target=target, task=task,
                     timeout_seconds=timeout_seconds, fut=fut)
    except Exception:
        logger.exception("Hintergrund-Auftrag nicht angelegt")
        cancel(state_id)
        name = target.get("name") or target.get("id", "?")
        return ToolResult.fail(
            f"Hintergrund-Auftrag an '{name}' konnte nicht angelegt werden (interner Fehler). "
            "Der Auftrag ist bereits gesendet, sein Ergebnis kommt aber nicht zurück. "
            f"Nicht sofort wiederholen; ggf. mit wait=true erneut beauftragen. State-ID: {state_id}"
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
