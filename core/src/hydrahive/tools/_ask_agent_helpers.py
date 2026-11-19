"""Small response, identity and timeout helpers for the ask_agent tool."""
from __future__ import annotations

from hydrahive.agentlink.checkpoints import split_checkpoint_findings
from hydrahive.agentlink.protocol import State
from hydrahive.agentlink.runtime_profiles import CHAIN_TOTAL_SECONDS, can_delegate, effective_budget
from hydrahive.settings import settings
from hydrahive.tools.base import ToolResult


def caller_agentlink_id(local_agent_id: str) -> str:
    """Stable resume/security identity; never derived from a mutable display name."""
    return (
        f"{settings.agentlink_agent_id}/{local_agent_id}"
        if local_agent_id else settings.agentlink_agent_id
    )


def response_timeout(target_agent: dict | None, profile: object) -> int:
    """Keep caller alive 60s longer than an internal target's effective budget.

    Kann das Ziel selbst beauftragen (Projekt-Agent), antwortet es erst nach
    seinen Kind-Aufträgen (runner/handoff_chain.py) — dann gilt die
    Ketten-Gesamtfrist. Vorher lief der Auftraggeber nach Budget + 60 s ab,
    während das Ziel noch auf seine Spezialisten wartete (Befund 19.11.2026)."""
    if not target_agent:
        return settings.agentlink_handoff_timeout
    own = effective_budget(target_agent, profile).timeout_seconds
    if can_delegate(target_agent):
        own = max(own, CHAIN_TOTAL_SECONDS)
    return own + 60


def result_from_response(response: State) -> ToolResult:
    """Preserve target failures and expose valid checkpoint metadata."""
    findings = response.working_memory.findings if response.working_memory else []
    visible_findings, checkpoint = split_checkpoint_findings(findings)
    description = response.task.description if response.task else ""
    summary_parts = [description] if description else []
    summary_parts.extend(f"- {item}" for item in visible_findings)
    output = "\n".join(summary_parts) if summary_parts else (
        f"Antwort-State {response.id} ohne lesbaren Inhalt."
    )
    status = response.task.status if response.task else "blocked"
    if status != "done":
        if checkpoint:
            output += (
                "\nFortsetzen: ask_agent für denselben agent_id mit "
                f"resume_token=\"{checkpoint['resume_token']}\" aufrufen."
            )
            return ToolResult.fail(
                f"Specialist-Status {status}: {output}", checkpoint=checkpoint,
            )
        return ToolResult.fail(f"Specialist-Status {status}: {output}")
    return ToolResult.ok(output)
