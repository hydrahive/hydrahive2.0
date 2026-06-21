"""Schritt 4-5: laufende Synthese + Stop-Entscheidung."""
from __future__ import annotations

from . import prompts
from .llm import ask
from .models import Finding, RunState

_SYNTH_WINDOW = 10  # nur die jüngsten Funde in die Synthese geben (Kontext-Budget)


def _format_findings(findings: list[Finding]) -> str:
    return "\n\n".join(
        f"- [{f.title}]({f.url}): {f.summary}" + (f"\n  Belege: {f.evidence}" if f.evidence else "")
        for f in findings
    )


async def synthesize(state: RunState) -> None:
    """Arbeitet die jüngsten Funde in state.report_md ein (mutiert in-place)."""
    recent = state.findings[-_SYNTH_WINDOW:]
    if not recent:
        return
    system = prompts.SYSTEM.format(date=prompts.today_str())
    state.report_md = await ask(
        prompts.synthesize(state.question, state.report_md, _format_findings(recent)),
        model=state.model,
        system=system,
        max_tokens=2500,
        temperature=0.4,
    )


async def should_stop(state: RunState) -> bool:
    if not state.report_md.strip():
        return False
    system = prompts.SYSTEM.format(date=prompts.today_str())
    raw = await ask(
        prompts.should_stop(state.question, state.report_md),
        model=state.model, system=system, max_tokens=10,
    )
    return raw.strip().upper().startswith("YES")
