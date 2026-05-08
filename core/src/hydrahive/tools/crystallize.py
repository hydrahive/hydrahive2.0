"""crystallize — Tool: aktuelle Session kristallisieren.

Agent kann eine abgeschlossene Session manuell zu einem Crystal verdichten.
Fallback auf aktuelle Session wenn keine session_id übergeben wird.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Kristallisiert eine Session: alle beobachteten Tool-Calls werden via LLM zu einem "
    "kompakten Crystal (Narrative, Key Outcomes, Files, Lessons) destilliert. "
    "Lessons werden automatisch als durchsuchbare Memory-Einträge gespeichert. "
    "Ohne session_id wird die aktuelle Session verwendet."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session-ID die kristallisiert werden soll. Ohne Angabe = aktuelle Session.",
        },
    },
    "required": [],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.tools._crystallize import crystallize_session

    session_id = args.get("session_id") or ctx.session_id
    if not session_id:
        return ToolResult(success=False, output="", error="Keine session_id bekannt.")

    # Modell aus Agent-Config holen
    from hydrahive.settings import settings
    agents = settings.load_agents()
    agent = next((a for a in agents if a["id"] == ctx.agent_id), None)
    model = agent.get("llm_model", "claude-opus-4-5") if agent else "claude-opus-4-5"

    project = ctx.project_id

    crystal = await crystallize_session(
        ctx.agent_id,
        session_id,
        model=model,
        project=project,
        force=True,  # manueller Aufruf → immer kristallisieren
    )

    if crystal is None:
        return ToolResult(
            success=False,
            output="",
            error=f"Keine CompressedObservations für Session {session_id} gefunden.",
        )

    lessons = crystal.get("lessons") or []
    outcomes = crystal.get("key_outcomes") or []
    files = crystal.get("files_affected") or []

    lines = [
        f"**Crystal** `{crystal['id']}`",
        f"Session: `{session_id}`",
        f"Observations: {crystal.get('observation_count', 0)}",
        "",
        f"**Narrative:** {crystal.get('narrative', '')}",
        "",
    ]
    if outcomes:
        lines.append("**Key Outcomes:**")
        for o in outcomes:
            lines.append(f"  - {o}")
        lines.append("")
    if files:
        lines.append("**Files Affected:**")
        for f in files[:10]:
            lines.append(f"  - {f}")
        if len(files) > 10:
            lines.append(f"  … und {len(files) - 10} weitere")
        lines.append("")
    if lessons:
        lines.append(f"**Lessons** ({len(lessons)} als Memory gespeichert):")
        for l in lessons:
            lines.append(f"  - {l}")
    else:
        lines.append("**Lessons:** keine extrahiert")

    return ToolResult(success=True, output="\n".join(lines))


TOOL = Tool(
    name="crystallize",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="memory",
)
