"""Schritt 6: finaler Langform-Markdown-Bericht."""
from __future__ import annotations

from . import prompts
from .llm import ask
from .models import RunState


async def write_report(state: RunState) -> str:
    """Erzeugt den finalen Markdown-Bericht. Fällt auf den Arbeitsbericht zurück."""
    if not state.findings:
        return f"# {state.question}\n\n*Keine verwertbaren Quellen gefunden.*"
    system = prompts.SYSTEM.format(date=prompts.today_str())
    md = await ask(
        prompts.final_report(state.question, state.report_md, state.category),
        model=state.model,
        system=system,
        max_tokens=4096,
        temperature=0.5,
    )
    md = md.strip()
    # Schwaches Modell lieferte zu wenig → Arbeitsbericht ist besser als nichts
    if len(md) < 200:
        return state.report_md.strip() or md or f"# {state.question}\n\n*Bericht konnte nicht erzeugt werden.*"
    return md
