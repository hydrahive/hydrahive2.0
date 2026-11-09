from __future__ import annotations

import logging

from hydrahive.compaction._chunking import split_at_message_boundaries
from hydrahive.compaction._llm import SummaryTooLarge, call_summary, model_chain, should_switch_model
from hydrahive.compaction._prompts import MERGE_INSTRUCTIONS as _MERGE_INSTRUCTIONS
from hydrahive.compaction._prompts import SUMMARY_INSTRUCTIONS as _SUMMARY_INSTRUCTIONS
from hydrahive.compaction.tokens import context_window_for, estimate_dense_text, estimate_text

logger = logging.getLogger(__name__)

_USABLE_FRACTION = 0.80

__all__ = ["SummaryTooLarge", "summarize"]


async def summarize(
    *,
    model: str,
    serialized_history: str,
    previous_summary: str | None = None,
    facts: dict | None = None,
    max_tokens: int = 4096,
    fallback_models: list[str] | None = None,
) -> str:
    """Strukturierte Zusammenfassung mit sequenziellem Modell-Failover.

    Pro Modell wird die komplette Zusammenfassung passend zu DESSEN Kontextfenster zerlegt. Ein Fallback mit
    kleinerem Fenster bekommt also kleinere Stücke, statt an zu großen Stücken für das Primärmodell zu scheitern
    (Review 09.11.2026). Gewechselt wird nur bei Rate-Limit/Quota/Auth/Verbindungsfehlern.
    """
    models = model_chain(model, fallback_models)
    for index, current in enumerate(models):
        is_last = index == len(models) - 1
        try:
            return await _summarize_with(current, serialized_history, previous_summary, facts, max_tokens)
        except Exception as exc:
            if is_last or not should_switch_model(exc):
                raise
            logger.warning("Compaction-Failover %s → %s wegen: %s", current, models[index + 1], exc)
    raise RuntimeError("Compaction ohne Modell")


async def _summarize_with(
    model: str, serialized_history: str, previous_summary: str | None, facts: dict | None, max_tokens: int,
) -> str:
    window = context_window_for(model)
    facts_str = _facts_string(facts) if facts else ""
    # Frühere Zusammenfassung dicht geschätzt: sie geht mit dem ersten Stück in denselben Aufruf.
    prev_tokens = estimate_dense_text(previous_summary) if previous_summary else 0
    fixed_overhead = (estimate_text(_SUMMARY_INSTRUCTIONS) + estimate_text(facts_str) + prev_tokens
                      + max_tokens + 1000)
    usable_for_history = max(10_000, int(window * _USABLE_FRACTION) - fixed_overhead)

    history_tokens = estimate_dense_text(serialized_history)
    if history_tokens <= usable_for_history:
        return await _single_summarize(
            model, _SUMMARY_INSTRUCTIONS, serialized_history, previous_summary, facts_str, max_tokens,
        )

    logger.info("Compaction-Chunking (%s): %d Tokens > %d nutzbar — splitte in Chunks",
                model, history_tokens, usable_for_history)
    chunks = split_at_message_boundaries(serialized_history, usable_for_history)
    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        logger.info("Chunk %d/%d (%d chars) → summarize", i, len(chunks), len(chunk))
        chunk_summaries.append(await _single_summarize(
            model, _SUMMARY_INSTRUCTIONS, chunk,
            previous_summary if i == 1 else None, facts_str if i == 1 else "", max_tokens,
        ))
    return await _merge_summaries(model, chunk_summaries, max_tokens, usable_for_history)


def _facts_string(facts: dict) -> str:
    parts = ["STRUKTURIERTE FAKTEN (gesicherte Wahrheit, übernimm wörtlich wo passend):"]
    for k, v in facts.items():
        parts.append(f"- {k}: {v}")
    parts.append("")
    return "\n".join(parts)


async def _single_summarize(
    model: str,
    system_prompt: str,
    history_text: str,
    previous_summary: str | None,
    facts_str: str,
    max_tokens: int,
) -> str:
    user_parts: list[str] = []
    if facts_str:
        user_parts.append(facts_str)
    if previous_summary:
        user_parts.append("BISHERIGE ZUSAMMENFASSUNG (aktualisieren statt überschreiben):")
        user_parts.append(previous_summary.strip())
        user_parts.append("")
        user_parts.append("NEUE NACHRICHTEN seit dieser Zusammenfassung:")
    else:
        user_parts.append("KONVERSATION zum Zusammenfassen:")
    user_parts.append(history_text)
    return await call_summary(
        model, system_prompt=system_prompt, content="\n".join(user_parts), max_tokens=max_tokens,
    )


async def _merge_summaries(
    model: str, summaries: list[str], max_tokens: int, usable_per_call: int,
) -> str:
    """Hierarchisches Merging: wenn alle Summaries zusammen ins Window passen,
    ein einzelner Merge. Sonst rekursiv in Gruppen mergen."""
    combined = "\n\n---\n\n".join(
        f"## Teil-Zusammenfassung {i+1}/{len(summaries)}\n\n{s}"
        for i, s in enumerate(summaries)
    )
    if estimate_dense_text(combined) <= usable_per_call or len(summaries) <= 1:
        return await call_summary(
            model, system_prompt=_MERGE_INSTRUCTIONS, content=combined, max_tokens=max_tokens,
        )

    # Rekursion: Gruppen von je 4 Summaries mergen, dann nochmal
    group_size = 4
    groups = [summaries[i:i + group_size] for i in range(0, len(summaries), group_size)]
    merged_groups: list[str] = []
    for g in groups:
        merged_groups.append(await _merge_summaries(model, g, max_tokens, usable_per_call))
    return await _merge_summaries(model, merged_groups, max_tokens, usable_per_call)
